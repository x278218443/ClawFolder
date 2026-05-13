"""
B站发布模块 - 通过 API 或浏览器自动化发布视频到 B站
"""
import os
import json
import time
import requests


class BilibiliPublisher:
    """B站视频发布客户端"""

    BASE_URL = "https://member.bilibili.com"
    API_URL = "https://api.bilibili.com"

    def __init__(self, sessdata: str, jct: str, buvid: str = ""):
        self.sessdata = sessdata
        self.jct = jct
        self.buvid = buvid
        self.session = requests.Session()
        self.session.cookies.set("SESSDATA", sessdata)
        self.session.cookies.set("bili_jct", jct)
        if buvid:
            self.session.cookies.set("buvid3", buvid)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://member.bilibili.com/platform/upload/video",
        })

    def get_upos_upload_url(self) -> dict:
        """获取上传地址"""
        resp = self.session.get(
            f"{self.BASE_URL}/x/upload/recup",
            params={"upcdn": "bda2", "probe_version": 20221109},
        )
        return resp.json()

    def upload_video(self, video_path: str, title: str = "untitled") -> dict:
        """上传视频文件到 B站
        返回: {"bili_filename": "xxx.mp4", "title": "xxx", ...}
        """
        if not os.path.exists(video_path):
            print(f"[B站] 视频文件不存在: {video_path}")
            return None

        file_size = os.path.getsize(video_path)
        print(f"[B站] 开始上传: {video_path} ({file_size/1024/1024:.1f}MB)")

        # Step 1: 获取上传凭证
        try:
            pre_upload = self.session.get(
                f"{self.BASE_URL}/x/web/preupload",
                params={"name": os.path.basename(video_path), "size": file_size, "r": "upos"},
            ).json()
        except Exception as e:
            print(f"[B站] 获取上传凭证失败: {e}")
            return None

        if pre_upload.get("code") != 0:
            print(f"[B站] 预上传失败: {pre_upload}")
            return None

        upload_url = pre_upload["data"]["upos_uri"]
        auth = pre_upload["data"]["auth"]
        endpoint = pre_upload["data"]["endpoints"][0] if pre_upload["data"]["endpoints"] else ""

        # Step 2: 初始化上传
        try:
            init_resp = self.session.post(
                f"https:{endpoint}/{upload_url.split('/')[-1]}",
                headers={"X-Upos-Auth": auth},
                params={"uploads": "", "output": "json"},
            ).json()
            upload_id = init_resp["upload_id"]
        except Exception as e:
            print(f"[B站] 初始化上传失败: {e}")
            return None

        # Step 3: 分片上传
        chunk_size = 4 * 1024 * 1024  # 4MB per chunk
        chunks = (file_size + chunk_size - 1) // chunk_size
        parts = []

        with open(video_path, "rb") as f:
            for i in range(chunks):
                chunk = f.read(chunk_size)
                try:
                    resp = self.session.put(
                        f"https:{endpoint}/{upload_url.split('/')[-1]}",
                        headers={"X-Upos-Auth": auth},
                        params={
                            "partNumber": i + 1,
                            "uploadId": upload_id,
                            "chunk": i,
                            "chunks": chunks,
                            "size": len(chunk),
                        },
                        data=chunk,
                    )
                    parts.append({"partNumber": i + 1, "eTag": "etag"})
                    print(f"[B站] 上传分片 {i+1}/{chunks}")
                except Exception as e:
                    print(f"[B站] 分片上传失败: {e}")
                    return None

        # Step 4: 完成上传
        try:
            complete = self.session.post(
                f"https:{endpoint}/{upload_url.split('/')[-1]}",
                headers={"X-Upos-Auth": auth},
                params={"output": "json", "name": os.path.basename(video_path), "profile": "ugcupos/bup"},
                json={"parts": parts, "uploadId": upload_id},
            ).json()
            print(f"[B站] 上传完成!")
            return {
                "bili_filename": complete.get("data", {}).get("filename", ""),
                "title": title,
                "size": file_size,
            }
        except Exception as e:
            print(f"[B站] 完成上传失败: {e}")
            return None

    def submit_video(
        self,
        upload_result: dict,
        title: str,
        desc: str = "",
        tags: list[str] = None,
        cover_url: str = "",
        tid: int = 122,  # 分区ID, 122=日常
    ) -> dict:
        """提交视频投稿
        Args:
            upload_result: upload_video 的返回值
            title: 视频标题
            desc: 视频简介
            tags: 标签列表
            cover_url: 封面图URL
            tid: 分区ID
        """
        payload = {
            "copyright": 1,  # 1=自制
            "source": "",
            "title": title[:80],
            "desc": desc[:250],
            "desc_format_id": 0,
            "dynamic": "",
            "tag": ",".join(tags[:12]) if tags else "",
            "tid": tid,
            "videos": [{
                "filename": upload_result.get("bili_filename", ""),
                "title": title[:80],
                "desc": "",
            }],
            "dtime": 0,  # 0=立即发布
            "open_elec": 0,
            "no_reprint": 1,
            "subtitle": {"open": 0, "lan": ""},
            "dolby": 0,
            "lossless_music": 0,
            "up_selection_reply": False,
            "up_close_reply": False,
            "open_danmaku": True,
        }

        if cover_url:
            payload["cover"] = cover_url

        try:
            resp = self.session.post(
                f"{self.BASE_URL}/x/web/add",
                data=payload,
                params={"csrf": self.jct},
            )
            result = resp.json()

            if result.get("code") == 0:
                bvid = result.get("data", {}).get("bvid", "")
                print(f"[B站] ✅ 投稿成功! BV号: {bvid}")
                return {"success": True, "bvid": bvid, "title": title}
            else:
                print(f"[B站] 投稿失败: {result}")
                return {"success": False, "error": result.get("message", "未知错误")}

        except Exception as e:
            print(f"[B站] 投稿异常: {e}")
            return {"success": False, "error": str(e)}


def publish_video(
    video_path: str,
    title: str,
    desc: str = "",
    tags: list[str] = None,
    tid: int = 122,
) -> dict:
    """一键发布视频到 B站"""
    from config.settings import BILI_SESSDATA, BILI_JCT, BILI_BUVID

    if not BILI_SESSDATA or not BILI_JCT:
        print("[B站] 未配置 B站账号信息，请在 config/api_keys.json 中填写")
        return {"success": False, "error": "未配置B站账号"}

    publisher = BilibiliPublisher(BILI_SESSDATA, BILI_JCT, BILI_BUVID)

    # 上传视频
    upload_result = publisher.upload_video(video_path, title)
    if not upload_result:
        return {"success": False, "error": "上传失败"}

    # 提交投稿
    result = publisher.submit_video(
        upload_result=upload_result,
        title=title,
        desc=desc or title,
        tags=tags or ["热点", "新闻"],
        tid=tid,
    )

    return result


if __name__ == "__main__":
    print("B站发布模块 - 请先配置 BILI_SESSDATA 和 BILI_JCT")
    print("获取方式: 登录B站 → F12 → Application → Cookies")
