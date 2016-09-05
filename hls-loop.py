import itertools
import math
import re
import time
from flask import Flask, Response


SEGMENTS_IN_PLAYLIST = 3
HLS_MIMETYPE = "application/vnd.apple.mpegurl"
(PLAYLIST_STATIC, PLAYLIST_LIVE, PLAYLIST_VOD) = range(3)

LIVE_HLS_PLAYLIST_TEMPLATE = """#EXTM3U
#EXT-X-TARGETDURATION:11
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:"""

app = Flask(__name__)
zero = time.time()


def content_path(program_id, fname):
    return "static/bipbop_4x3/gear{}/{}".format(program_id, fname)


def read_file_durations(playlist_id):
    "return a list of (duration, filename) touples for playlist file"
    with open(content_path(playlist_id, "prog_index.m3u8")) as f:
        return re.findall(r"EXTINF:([\d\.]+),\s*\n([\w\.]+)",
                          f.read(), flags=re.M)


@app.route("/variant.m3u8")
def variant():
    return Response("""#EXTM3U
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=232370,CODECS="mp4a.40.2, avc1.4d4015"
playlist1.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=649879,CODECS="mp4a.40.2, avc1.4d401e"
playlist2.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=991714,CODECS="mp4a.40.2, avc1.4d401e"
playlist3.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=1927833,CODECS="mp4a.40.2, avc1.4d401f"
playlist4.m3u8
""", mimetype=HLS_MIMETYPE)


def extract_playlist_window(segments, window_width):
    """return tuple of curent media sequence and (duration, filename) list
    of SEGMENTS_IN_PLAYLIST at the returned media_sequence"""

    total_duration = sum(float(duration) for duration, filename in segments)
    delta = time.time() - zero
    n_loops = math.floor(delta / total_duration)
    delta_in_loop = delta - total_duration * n_loops

    media_sequence = int(n_loops * len(segments))
    filtered_segments = []
    for segment in itertools.cycle(segments):
        delta_in_loop -= float(segment[0])
        if delta_in_loop > 0:
            media_sequence += 1
        elif len(filtered_segments) < window_width:
            filtered_segments.append(segment)
        else:
            break
    return media_sequence, filtered_segments


def format_segment(playlist_id, segment):
    duration, fname = segment
    return "#EXTINF:{},\n{}".format(duration, content_path(playlist_id, fname))


def generate_playlist(playlist_id, playlist_type=PLAYLIST_LIVE):
    segments = read_file_durations(playlist_id)
    media_sequence = 0
    if playlist_type in (PLAYLIST_LIVE, PLAYLIST_VOD):
        media_sequence, segments = extract_playlist_window(segments, SEGMENTS_IN_PLAYLIST)

    segments_txt = '\n'.join([format_segment(playlist_id, segment) for segment in segments])
    if playlist_type is PLAYLIST_STATIC:
        # TODO VOD type should also have the endlist when appropriate
        segments_txt += "\n#EXT-X-ENDLIST"
    # TODO VOD type should have the "#EXT-X-PLAYLIST-TYPE:VOD" tag before media
    # sequence
    return "{}{}\n{}".format(LIVE_HLS_PLAYLIST_TEMPLATE, media_sequence, segments_txt)


@app.route("/radio.m3u8")
@app.route("/program<int:playlist_id>.m3u8")
@app.route("/playlist<int:playlist_id>.m3u8")
def looped_playlist(playlist_id=0):
    return Response(generate_playlist(playlist_id, PLAYLIST_LIVE),
                    mimetype=HLS_MIMETYPE)


@app.route("/static_radio.m3u8")
@app.route("/static<int:playlist_id>.m3u8")
def static_playlist(playlist_id=0):
    return Response(generate_playlist(playlist_id, PLAYLIST_STATIC),
                    mimetype=HLS_MIMETYPE)

@app.route("/crossdomain.xml")
def crossdomain():
    return Response("""<cross-domain-policy>
<site-control permitted-cross-domain-policies="all"/>
<allow-access-from domain="*" secure="false"/>
<allow-http-request-headers-from domain="*" headers="*" secure="false"/>
</cross-domain-policy>""", mimetype="text/xml")

if __name__ == "__main__":
    #app.debug = True
    app.run(host='0.0.0.0')
