import logging
import ipywidgets as widgets
from traitlets import Bool, Dict, Float, Int, List, Unicode, Union

from ._version import __version__


@widgets.register
class HiGlassDisplay(widgets.DOMWidget):
    _view_name = Unicode("HiGlassDisplayView").tag(sync=True)
    _model_name = Unicode("HiGlassDisplayModel").tag(sync=True)
    _view_module = Unicode("higlass-jupyter").tag(sync=True)
    _model_module = Unicode("higlass-jupyter").tag(sync=True)
    _view_module_version = Unicode(__version__).tag(sync=True)
    _model_module_version = Unicode(__version__).tag(sync=True)
    _model_data = List([]).tag(sync=True)

    viewconf = Dict({}).tag(sync=True)
    height = Int().tag(sync=True)

    dom_element_id = Unicode(read_only=True).tag(sync=True)

    # Read-only properties that get updated by HiGlass exclusively
    location = List(Union([Float(), List()]), read_only=True).tag(sync=True)
    cursor_location = List([], read_only=True).tag(sync=True)
    selection = List([], read_only=True).tag(sync=True)

    # Short-hand options
    auth_token = Unicode().tag(sync=True)
    bounded = Bool(None, allow_none=True).tag(sync=True)
    default_track_options = Dict({}).tag(sync=True)
    dark_mode = Bool(False).tag(sync=True)
    renderer = Unicode().tag(sync=True)
    select_mode = Bool(False).tag(sync=True)
    selection_on_alt = Bool(False).tag(sync=True)
    # For any kind of options. Note that whatever is defined in options will
    # be overwritten by the short-hand options
    options = Dict({}).tag(sync=True)

    def __init__(self, **kwargs):
        super(HiGlassDisplay, self).__init__(**kwargs)


def display(
    views,
    location_syncs=[],
    value_scale_syncs=[],
    zoom_syncs=[],
    host="localhost",
    server_port=None,
    dark_mode=False,
    log_level=logging.ERROR,
    no_fuse=False,
):
    """
    Instantiate a HiGlass display with the given views.

    Args:
        views: A list of views to display. If the items in the list are
            lists themselves, then automatically create views out of them.
        location_syncs: A list of lists, each containing a list of views which
            will scroll together.
        zoom_syncs: A list of lists, each containing a list of views that
            will zoom together.
        host: The host on which the internal higlass server will be running on.
        server_port: The port on which the internal higlass server will be running on.
        dark_mode: Whether to use dark mode or not.
        log_level: Level of logging to perform.
        no_fuse: Don't mount the fuse filesystem. Useful if not loading any data
            over http or https.

    Returns:
        (display: HiGlassDisplay, server: higlass.server.Server, higlass.client.viewconf) tuple
        Display is an object used to create
        a HiGlass viewer within a Jupyter notebook. The server object encapsulates
        a Flask instance of a higlass server and the viewconf is a Python object
        containing the viewconf describing the higlass dashboard.
    """
    from .server import Server
    from .client import CombinedTrack, View, ViewConf, ViewportProjection

    tilesets = []

    # views can also be passed in as lists of tracks
    new_views = []
    for view in views:
        if isinstance(view, (tuple, list)):
            # view is a list of tracks
            new_views.append(View(view))
        else:
            new_views.append(view)
    views = new_views

    for view in views:
        for track in view.tracks:
            if hasattr(track, "tracks"):
                for track1 in track.tracks:
                    if not isinstance(track1, ViewportProjection) and track1.tileset:
                        tilesets += [track1.tileset]

            if track.tileset:
                tilesets += [track.tileset]

    server = Server(tilesets, host=host, port=server_port, no_fuse=no_fuse)
    server.start(log_level=log_level)

    cloned_views = [View.from_dict(view.to_dict()) for view in views]

    for view in cloned_views:
        for track in view.tracks:
            if isinstance(track, CombinedTrack):
                for track1 in track.tracks:
                    if "fromViewUid" in track1.conf:
                        # this is a viewport projection and doesn't have
                        # a server
                        pass
                    elif "server" not in track1.conf or track1.conf["server"] is None:
                        track1.conf["server"] = server.api_address
            elif "fromViewUid" in track.conf:
                pass
            else:
                if "server" not in track.conf or track.conf["server"] is None:
                    track.conf["server"] = server.api_address

    viewconf = ViewConf(
        cloned_views,
        location_syncs=location_syncs,
        value_scale_syncs=value_scale_syncs,
        zoom_syncs=zoom_syncs,
    )

    return (
        HiGlassDisplay(
            viewconf=viewconf.to_dict(),
            hg_options={"theme": "dark" if dark_mode else "light"},
        ),
        server,
        viewconf,
    )
