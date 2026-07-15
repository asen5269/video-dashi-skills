import json

from scripts.douyin_parser import extract_detail, extract_url, router_detail


def test_extract_url_from_share_text():
    assert extract_url("复制打开抖音 https://v.douyin.com/abc123/ 看视频") == "https://v.douyin.com/abc123/"


def test_router_detail_reads_item():
    item = {"aweme_id": "123", "desc": "demo"}
    payload = {"loaderData": {"video": {"videoInfoRes": {"item_list": [item]}}}}
    source = f"<script>window._ROUTER_DATA = {json.dumps(payload)};</script>"
    assert router_detail(source) == item


def test_extract_detail_selects_video_and_cover():
    class Session:
        def get(self, *args, **kwargs):
            return type("Response", (), {"headers": {}})()

    detail = {
        "desc": "标题\n正文",
        "video": {
            "play_addr": {"url_list": ["https://example.com/playwm/video.mp4"]},
            "origin_cover": {"url_list": ["https://example.com/cover.jpg"]},
        },
    }
    result = extract_detail(detail, Session())
    assert result["title"] == "标题"
    assert result["content"] == "正文"
    assert result["videos"] == ["https://example.com/play/video.mp4"]
    assert result["images"] == ["https://example.com/cover.jpg"]
