import json
import re

from mopidy_youtube import logger
from mopidy_youtube.apis.youtube_scrapi import scrAPI


# JSON based scrAPI
class jAPI(scrAPI):

    # search for videos and playlists using japi
    # **currently not working**
    # @classmethod
    # def run_search(cls, query):
    #
    #     cls.session.headers = {
    #         "user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0)"
    #         " Gecko/20100101 Firefox/66.0",
    #         "Cookie": "PREF=hl=en;",
    #         "Accept-Language": "en;q=0.5",
    #         "content_type": "application/json",
    #     }
    #     logger.info("session.get triggered: jAPI search")
    #     result = cls.session.get(cls.endpoint + "results", params=query)
    #     yt_data = cls._find_yt_data(result.text)
    #     extracted_json = yt_data["contents"]["twoColumnSearchResultsRenderer"][
    #         "primaryContents"
    #     ]["sectionListRenderer"]["contents"][0]["itemSectionRenderer"][
    #         "contents"
    #     ]
    #     return cls.json_to_items(cls, extracted_json)

    def json_to_items(cls, result_json):
        if len(result_json) > 1 and "itemSectionRenderer" in result_json[1]:
            result_json = result_json[1]["itemSectionRenderer"]["contents"]

        items = []

        for content in result_json:
            if "videoRenderer" in content:
                base = "videoRenderer"
            elif "compactVideoRenderer" in content:
                base = "compactVideoRenderer"
            elif "playlistVideoRenderer" in content:
                base = "playlistVideoRenderer"
            else:
                base = ""

            if base in [
                "videoRenderer",
                "compactVideoRenderer",
                "playlistVideoRenderer",
            ]:
                if "longBylineText" in content[base]:
                    byline = "longBylineText"
                else:
                    byline = "shortBylineText"

                try:
                    videoId = content[base]["videoId"]
                except Exception as e:
                    # videoID = "Unknown"
                    logger.error("videoId exception %s" % e)
                    continue

                try:
                    title = content[base]["title"]["simpleText"]
                except Exception:
                    try:
                        title = content[base]["title"]["runs"][0]["text"]
                    except Exception as e:
                        # title = "Unknown"
                        logger.error("title exception %s" % e)
                        continue

                try:
                    thumbnails = content[base]["thumbnail"]["thumbnails"][0]
                    thumbnails["url"] = thumbnails["url"].split("?", 1)[
                        0
                    ]  # is the rest tracking stuff? Omit
                except Exception as e:
                    logger.error(f"thumbnail exception {e}")

                try:
                    channelTitle = content[base][byline]["runs"][0]["text"]
                except Exception as e:
                    # channelTitle = "Unknown"
                    logger.error("channelTitle exception %s, %s" % (e, title))
                    continue

                item = {
                    "id": {"kind": "youtube#video", "videoId": videoId},
                    "snippet": {
                        "title": title,
                        "resourceId": {"videoId": videoId},
                        "thumbnails": {"default": thumbnails,},
                        "channelTitle": channelTitle,
                    },
                }

                try:
                    duration_text = content[base]["lengthText"]["simpleText"]
                    duration = "PT" + cls.format_duration(
                        re.match(cls.time_regex, duration_text)
                    )
                    logger.debug("duration: ", duration)
                except Exception as e:
                    logger.warn("no video-time, possibly live: ", e)
                    duration = "PT0S"

                item.update({"contentDetails": {"duration": duration}})

                # is channelId useful for anything?
                try:
                    channelId = content[base][byline]["runs"][0][
                        "navigationEndpoint"
                    ]["browseEndpoint"]["browseId"]
                    logger.debug(channelId)
                    item["snippet"].update({"channelId": channelId})
                except Exception as e:
                    logger.error("channelId exception %s, %s" % (e, title))

                items.append(item)

            elif "radioRenderer" in content:
                continue

            elif "playlistRenderer" in content:

                try:
                    thumbnails = content["playlistRenderer"]["thumbnails"][0][
                        "thumbnails"
                    ][0]
                    thumbnails["url"] = thumbnails["url"].split("?", 1)[
                        0
                    ]  # is the rest tracking stuff? Omit
                except Exception as e:
                    logger.error(
                        f"thumbnail exception {e}, {content['playlistRenderer']['playlistId']}"
                    )

                try:
                    channelTitle = content["playlistRenderer"][
                        "longBylineText"
                    ]["runs"][0]["text"]
                except Exception as e:
                    logger.error(
                        f"channelTitle exception {e}, {content['playlistRenderer']['playlistId']}"
                    )

                item = {
                    "id": {
                        "kind": "youtube#playlist",
                        "playlistId": content["playlistRenderer"]["playlistId"],
                    },
                    "contentDetails": {
                        "itemCount": content["playlistRenderer"]["videoCount"]
                    },
                    "snippet": {
                        "title": content["playlistRenderer"]["title"][
                            "simpleText"
                        ],
                        "thumbnails": {"default": thumbnails,},
                        "channelTitle": channelTitle,
                    },
                }
                items.append(item)

            elif "gridPlaylistRenderer" in content:
                logger.info(content)
                try:
                    thumbnails = content["gridPlaylistRenderer"][
                        "thumbnailRenderer"
                    ]["playlistVideoThumbnailRenderer"]["thumbnail"][
                        "thumbnails"
                    ][
                        0
                    ]
                    thumbnails["url"] = thumbnails["url"].split("?", 1)[
                        0
                    ]  # is the rest tracking stuff? Omit
                except Exception as e:
                    logger.error(
                        f"thumbnail exception {e}, {content['gridPlaylistRenderer']['playlistId']}"
                    )

                item = {
                    "id": {
                        "kind": "youtube#playlist",
                        "playlistId": content["gridPlaylistRenderer"][
                            "playlistId"
                        ],
                    },
                    "contentDetails": {
                        "itemCount": int(
                            content["gridPlaylistRenderer"][
                                "videoCountShortText"
                            ]["simpleText"].replace(",", "")
                        )
                    },
                    "snippet": {
                        "title": content["gridPlaylistRenderer"]["title"][
                            "runs"
                        ][0]["text"],
                        "thumbnails": {"default": thumbnails,},
                        "channelTitle": "unknown",  # note: do better
                    },
                }
                items.append(item)

        # remove duplicates
        items[:] = [
            json.loads(t)
            # for t in {json.dumps(d) for d in items}
            for t in {json.dumps(d, sort_keys=True) for d in items}
        ]

        return items
