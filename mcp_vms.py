#!/usr/bin/env python3

import os
import sys
import asyncio
import logging
import time
from io import BytesIO
from datetime import datetime
from PIL import Image as PILImage
from mcp.server.fastmcp import FastMCP, Image, Context
from typing import List, Dict, Any
from mcp_vms_config import vms_config

import vmspy # type: ignore

DATA_DIR = "./data"

def to_dict(obj):
    if isinstance(obj, (list, tuple)):
        return [to_dict(item) for item in obj]
    
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}

    if hasattr(obj, "__class__") and not isinstance(obj, (int, float, str, bool, type(None))):
        result = {}
        for attr in dir(obj):
            if not attr.startswith('__'):
                value = getattr(obj, attr)
                if not callable(value):
                    result[attr] = to_dict(value)
        return result

    return obj

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)

# Configure logging: first disable other loggers
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)

# Configure our logger
log_filename = os.path.join(DATA_DIR, datetime.now().strftime("%y-%m-%d.log"))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create handlers
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setFormatter(formatter)
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setFormatter(formatter)

# Set up our logger
logger = logging.getLogger("vms-mcp")
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
# Prevent double logging
logger.propagate = False

# Create a FastMCP server instance
mcp = FastMCP("image-service")

# Create vmspy instances
vms_live_video = vmspy.live_video()
vms_playback = vmspy.playback()
vms_utils = vmspy.utils()

@mcp.tool()
async def get_channels(ctx: Context = None) -> List[Dict[str, Any]]:
    """
    Return a list of channel information dictionaries.

    Each dictionary contains the following keys:
    - ch_no: The channel number (int).
    - title: The name or title of the channel (string).
    - is_connected: A boolean indicating whether the channel is currently connected.
    - is_recording: A boolean indicating whether the channel is currently recording.
    - is_ptz: A boolean indicating whether the channel is a PTZ (Pan-Tilt-Zoom) camera.
    - ptz_presets: A list of PTZ preset dictionaries, each with 'no' and 'title' keys (available when is_ptz is True).
    - time_start: The earliest recording time of the channel in ISO 8601 format (string).
    - time_end: The latest recording time of the channel in ISO 8601 format (string).
    - sub_channel_count: The number of sub-channels associated with this channel (int).

    Args:
        ctx: The context object for logging or error handling.

    Returns:
        A list of channel information dictionaries.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
            channels = [to_dict(ch) for ch in vms_utils.get_channel_list()]
            logger.debug(f"Retrieved channel list: {channels}")
        else:
            error_msg = vms_utils.get_error()
            if ctx: ctx.error(f"Failed to get channel list: {error_msg}")
            logger.error(f"Failed to get channel list: {error_msg}")
            channels = []
        return channels
    except Exception as e:
        logger.exception("Error in get_channels")
        if ctx: ctx.error(f"Failed to retrieve channels: {str(e)}")
        return []

@mcp.tool()
async def get_channel_groups(ctx: Context = None) -> List[Dict[str, Any]]:
    """
    Return the list of channel groups along with their member channels.

    Each group dictionary contains the following keys:
    - idx: The index of the group (int).
    - title: The name of the group (string).
    - channels: A list of channel member dictionaries, where each member contains:
        - ch_no: The channel number (int).
        - title: The name or title of the channel (string).

    Args:
        ctx: The context object for logging or error handling.

    Returns:
        A list of group information dictionaries.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
            groups = [to_dict(g) for g in vms_utils.get_group_list()]
            logger.debug(f"Retrieved channel groups: {groups}")
            return groups
        else:
            error_msg = vms_utils.get_error()
            if ctx: ctx.error(f"Failed to retrieve channel groups: {error_msg}")
            logger.error(f"Failed to retrieve channel groups: {error_msg}")
            return []
    except Exception as e:
        logger.exception("Error in get_channel_groups")
        if ctx: ctx.error(f"Failed to retrieve channel groups: {str(e)}")
        return []

@mcp.tool()
async def get_recording_dates(year: int, month: int, ctx: Context = None) -> List[Dict[str, Any]]:
    """
    Retrieve recording dates for video channels for a specific year and month.

    This function fetches the recording dates for all channels within the specified time range.

    Args:
        year: The year for which to retrieve recording dates.
        month: The month for which to retrieve recording dates.
        ctx: The context object for logging or error handling.

    Returns:
        A list of recording date information dictionaries, each containing:
        - ch_no: The channel number (int).
        - title: The name or title of the channel (string).
        - dates: A list of recording dates in ISO 8601 format (list of strings).
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
            recording_dates = [to_dict(d) for d in vms_utils.get_recording_dates(year, month)]
            logger.debug(f"Retrieved recording dates for {year}-{month}: {recording_dates}")
            return recording_dates
        else:
            error_msg = vms_utils.get_error()
            if ctx: ctx.error(f"Failed to get recording dates for {year}-{month}: {error_msg}")
            logger.error(error_msg)
            return []
    except Exception as e:
        logger.exception(f"Error in get_recording_dates for {year}-{month}")
        if ctx: ctx.error(f"Failed to retrieve recording dates for {year}-{month}: {str(e)}")
        return []

@mcp.tool()
async def get_recording_times(ch_no: int, sub_idx: int, year: int, month: int, day: int, ctx: Context = None) -> List[Dict[str, Any]]:
    """
    Retrieve recording times for a specific channel, sub-channel, and date.

    This function fetches the recording times for a given channel and sub-channel on a specific day.

    Args:
        ch_no: The channel number.
        sub_idx: The sub-channel index, zero(0) for primary.
        year: The year for which to retrieve recording times.
        month: The month for which to retrieve recording times.
        day: The day for which to retrieve recording times.
        ctx: The context object for logging or error handling.

    Returns:
        A list of recording time information dictionaries, each containing:
        - time: The start time of the recording in ISO 8601 format (string).
        - timestamp: The Unix timestamp of the recording start time (int).
        - duration: The duration of the recording in seconds (int).
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
            recording_times = [to_dict(rt) for rt in vms_utils.get_recording_times(ch_no, year, month, day, sub_idx)]
            logger.debug(f"Retrieved recording times for channel {ch_no}, sub-channel {sub_idx} on {year}-{month}-{day}: {recording_times}")
            return recording_times
        else:
            error_msg = vms_utils.get_error()
            if ctx: ctx.error(f"Failed to get recording times for channel {ch_no}: {error_msg}")
            logger.error(error_msg)
            return []
    except Exception as e:
        logger.exception(f"Error in get_recording_times for channel {ch_no}, sub-channel {sub_idx} on {year}-{month}-{day}")
        if ctx: ctx.error(f"Failed to retrieve recording times for channel {ch_no}, sub-channel {sub_idx} on {year}-{month}-{day}: {str(e)}")
        return []

@mcp.tool()
async def get_events(ch_no: int, year: int, month: int, day: int, num_days: int = 1, ctx: Context = None) -> List[Dict[str, Any]]:
    """
    Retrieve events for a specific date and channel.

    If the channel number is zero (0), events for all channels are retrieved.

    Args:
        ch_no: The channel number. Use 0 to retrieve events for all channels.
        year: The year of the events to retrieve.
        month: The month of the events to retrieve.
        day: The day of the events to retrieve.
        num_days: The number of days to retrieve events for (default: 1).
        ctx: The context object for logging or error handling.

    Returns:
        A list of event information dictionaries, each containing:
        - ch_no: The channel number (int).
        - type: The type of the event (string, e.g., "Motion", "Sensor").
        - time: The time of the event in ISO 8601 format (string).
        - timestamp: The Unix timestamp of the event (int).
        - duration: The duration of the event in seconds (float).
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
            events = [to_dict(e) for e in vms_utils.get_events(ch_no, year, month, day, num_days)]
            logger.debug(f"Retrieved events for channel {ch_no} on {year}-{month}-{day} for {num_days} day(s): {events}")
            return events
        else:
            error_msg = vms_utils.get_error()
            if ctx: ctx.error(f"Failed to retrieve events for channel {ch_no}: {error_msg}")
            logger.error(f"Failed to retrieve events for channel {ch_no}: {error_msg}")
            return []
    except Exception as e:
        logger.exception(f"Error while retrieving events for channel {ch_no} on {year}-{month}-{day}: {str(e)}")
        if ctx: ctx.error(f"An unexpected error occurred: {str(e)}")
        return []

@mcp.tool()
async def get_archived_files(ctx: Context = None) -> List[Dict[str, Any]]:
    """
    Retrieve the list of archived video files (automatically converted by pybind11).

    Args:
        ctx: The context object for logging or error handling.

    Returns:
        A list of archived file information dictionaries, each containing:
        - file_id: The unique identifier of the archived file (int).
        - ch_no: The channel number (int).
        - title: The title of the archived file (string).
        - desc: The description of the archived file (string).
        - time: The start time of the archived file in ISO 8601 format (string).
        - timestamp: The Unix timestamp of the archived file start time (int).
        - duration: The duration of the archived file in seconds (int).
        - priority: The priority level of the archived file (int).
        - filesize: The size of the archived file in bytes (int).
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
            files = [to_dict(f) for f in vms_utils.get_file_list()]
            logger.debug(f"Retrieved archived files: {files}")
            return files
        else:
            error_msg = vms_utils.get_error()
            if ctx: ctx.error(f"Failed to retrieve archived files: {error_msg}")
            logger.error(f"Failed to retrieve archived files: {error_msg}")
            return []
    except Exception as e:
        logger.exception(f"Error while retrieving archived files: {str(e)}")
        if ctx: ctx.error(f"An unexpected error occurred: {str(e)}")
        return []


@mcp.tool() 
async def fetch_live_image(ch_no: int, sub_idx: int, ctx: Context = None) -> Image | None:
    """
    Fetch a specific live frame image from a video channel.

    This function retrieves a frame image for a given channel, sub-channel, and timestamp.

    Args:
        ch_id: The channel ID.
        sub_idx: The sub-channel index, zero(0) for primary.
        ctx: The context object for logging or error handling.

    Returns:
        An Image object containing the frame image, or None if the operation fails.
    """
    if vms_live_video.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
        vms_live_video.set_image_size(vms_config['img_width'], vms_config['img_height'])
        vms_live_video.set_pixel_format(vms_config['pixel_format'])

        frame_image, frame_info = vms_live_video.get_image(ch_no, sub_idx)

        if frame_image is None:
            error_msg = f"Failed to fetch live image for channel {ch_no}, sub-channel {sub_idx}."
            logger.error(error_msg)
            if ctx: ctx.error(error_msg)
            return None

        # Convert the numpy array (frame_image) to a JPEG using PIL
        img = PILImage.fromarray(frame_image)
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format="JPEG")
        image_data = img_byte_arr.getvalue()

        logger.debug(f"Fetched live image for channel {ch_no}, sub-channel {sub_idx}.")
        return Image(data=image_data, format="jpeg")
    else:
        error_msg = f"Failed to initialize connection to retrieve recording times for channel {ch_no}, sub-channel {sub_idx}."
        if ctx: ctx.error(error_msg)
        logger.error(error_msg)
        return {"error": error_msg}

@mcp.tool() 
async def fetch_recorded_image(ch_no: int, sub_idx: int, year: int, month: int, day: int, hour: int, minute: int, second: int, ctx: Context = None) -> Image | None:
    """
    Fetch a specific recorded frame image from a video channel.

    This function retrieves a frame image for a given channel, sub-channel, and timestamp.

    Args:
        ch_id: The channel ID.
        sub_idx: The sub-channel index, zero(0) for primary.
        year: The year of the frame to fetch.
        month: The month of the frame to fetch.
        day: The day of the frame to fetch.
        hour: The hour of the frame to fetch.
        minute: The minute of the frame to fetch.
        second: The second of the frame to fetch.
        ctx: The context object for logging or error handling.

    Returns:
        An Image object containing the frame image, or None if the operation fails.
    """
    if vms_playback.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
        vms_playback.set_image_size(vms_config['img_width'], vms_config['img_height'])
        vms_playback.set_pixel_format(vms_config['pixel_format'])

        frame_image, frame_info = vms_playback.get_image(ch_no, year, month, day, hour, minute, second, sub_idx)

        if frame_image is None:
            error_msg = f"Failed to fetch recorded image for channel {ch_no}, sub-channel {sub_idx} at {year}-{month}-{day} {hour}:{minute}:{second}. ({frame_info["error"]})"
            if ctx: ctx.error(error_msg)
            logger.error(error_msg)
            return None

        # Convert the numpy array (frame_image) to a JPEG using PIL
        img = PILImage.fromarray(frame_image)
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format="JPEG")
        image_data = img_byte_arr.getvalue()

        logger.debug(f"Fetched recorded image for channel {ch_no}, sub-channel {sub_idx} at {year}-{month}-{day} {hour}:{minute}:{second}.")
        return Image(data=image_data, format="jpeg")
    else:
        error_msg = f"Failed to initialize connection to retrieve recording times for channel {ch_no}, sub-channel {sub_idx} on {year}-{month}-{day}."
        if ctx: ctx.error(error_msg)
        logger.error(error_msg)
        return {"error": error_msg}

@mcp.tool() 
async def fetch_archived_file_image(file_id: int, timestamp: int, ctx: Context = None) -> Image | None:
    """
    Fetch a specific frame image from an archived video file.

    This function retrieves a frame image from an archived file at a specific timestamp.

    Args:
        file_id: The unique identifier of the archived file.
        timestamp: The Unix timestamp of the frame to fetch.
        ctx: The context object for logging or error handling.

    Returns:
        An Image object containing the frame image, or None if the operation fails.
    """
    if vms_playback.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
        vms_playback.set_image_size(vms_config['img_width'], vms_config['img_height'])
        vms_playback.set_pixel_format(vms_config['pixel_format'])

        frame_image, frame_info = vms_playback.get_file_image(file_id, timestamp)

        if frame_image is None:
            error_msg = f"Failed to fetch archived file image for file_id {file_id} at timestamp {timestamp}. ({frame_info.get('error', 'Unknown error')})"
            if ctx: ctx.error(error_msg)
            logger.error(error_msg)
            return None

        # Convert the numpy array (frame_image) to a JPEG using PIL
        img = PILImage.fromarray(frame_image)
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format="JPEG")
        image_data = img_byte_arr.getvalue()

        logger.debug(f"Fetched archived file image for file_id {file_id} at timestamp {timestamp}.")
        return Image(data=image_data, format="jpeg")
    else:
        error_msg = f"Failed to initialize connection to retrieve archived file image for file_id {file_id}."
        if ctx: ctx.error(error_msg)
        logger.error(error_msg)
        return None

@mcp.tool()
async def move_ptz_to_preset(ch_no: int, preset_no: int, ctx: Context = None) -> bool:
    """
    Move a PTZ camera to a specified preset position.

    Args:
        ch_no: The channel number of the PTZ camera.
        preset_no: The preset number to move the camera to.
        ctx: The context object for logging or error handling.

    Returns:
        True if the operation succeeds, False otherwise.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']) \
            and vms_utils.ptz_preset_go(ch_no, preset_no):
            logger.debug(f"Moved PTZ camera on channel {ch_no} to preset {preset_no}.")
            return True
        else:
            error_msg = vms_utils.get_error()
            if ctx: ctx.error(f"Failed to move PTZ camera on channel {ch_no} to preset {preset_no}: {error_msg}")
            logger.error(error_msg)
            return False

    except Exception as e:
        logger.exception(f"Error while moving PTZ camera on channel {ch_no} to preset {preset_no}: {str(e)}")
        if ctx: ctx.error(f"An unexpected error occurred: {str(e)}")
        return False

@mcp.tool()
async def get_ptz_preset(ch_no: int, ctx: Context = None) -> Dict[str, Any]:
    """
    Retrieve the PTZ preset position information for a specific channel.

    Args:
        ch_no: The channel number.
        ctx: The context object for logging or error handling.

    Returns:
        A dictionary for the PTZ preset position:
        - no: The preset number.
        - title: The preset title.
        - status: "ok" if successful, or an error message otherwise.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
            preset = vms_utils.get_ptz_preset(ch_no)
            if preset and preset["status"] == "ok":
                logger.debug(f"Retrieved PTZ presets for channel {ch_no}: presetNo={preset["no"]}")
                return preset
            else:
                error_msg = preset["status"]
                if ctx: ctx.error(error_msg)
                logger.error(error_msg)
                return [{"no": None, "title": None, "status": error_msg}]
        else:
            error_msg = f"Failed to initialize connection to retrieve PTZ presets for channel {ch_no}."
            if ctx: ctx.error(error_msg)
            logger.error(error_msg)
            return [{"no": None, "title": None, "status": error_msg}]
    except Exception as e:
        logger.exception(f"Error while retrieving PTZ presets for channel {ch_no}: {str(e)}")
        if ctx: ctx.error(f"An unexpected error occurred: {str(e)}")
        return [{"no": None, "title": None, "status": f"Error: {str(e)}"}]

@mcp.tool()
async def show_live_video(ch_no: int, sub_idx: int, ctx: Context = None) -> bool:
    """
    Show the live video stream of a specific channel in the VMS program.

    Args:
        ch_no: The channel number.
        sub_idx: The sub-channel index, zero(0) for primary.
        ctx: The context object for logging or error handling.

    Returns:
        True if the operation succeeds, False otherwise.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']) \
            and vms_utils.show_live(ch_no, sub_idx):
            logger.debug(f"Show live video for channel {ch_no}, sub-channel {sub_idx}.")
            return True
        else:
            error_msg = vms_utils.get_error()
            if ctx: ctx.error(f"Failed to show live video for channel {ch_no}, sub-channel {sub_idx}: {error_msg}")
            logger.error(f"Failed to show live video for channel {ch_no}, sub-channel {sub_idx}: {error_msg}")
            return False
    except Exception as e:
        logger.exception(f"Error while showing live video for channel {ch_no}, sub-channel {sub_idx}: {str(e)}")
        if ctx: ctx.error(f"An unexpected error occurred: {str(e)}")
        return False

@mcp.tool()
async def show_playback_video(ch_no: int, sub_idx: int, year: int, month: int, day: int, hour: int, minute: int, second: int, ctx: Context = None) -> bool:
    """
    Show the playback video stream of a specific channel at a specific timestamp in the VMS program.

    Args:
        ch_no: The channel number.
        sub_idx: The sub-channel index, zero(0) for primary.
        year: The year of the playback timestamp.
        month: The month of the playback timestamp.
        day: The day of the playback timestamp.
        hour: The hour of the playback timestamp.
        minute: The minute of the playback timestamp.
        second: The second of the playback timestamp.
        ctx: The context object for logging or error handling.

    Returns:
        True if the operation succeeds, False otherwise.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']) \
            and vms_utils.show_playback(ch_no, year, month, day, hour, minute, second, sub_idx):
            logger.debug(f"Playback video image for channel {ch_no}, sub-channel {sub_idx} at {year}-{month}-{day} {hour}:{minute}:{second}.")
            return True
        else:
            error_msg = vms_utils.get_error()
            if ctx: ctx.error(f"Failed to show playback video image for channel {ch_no}, sub-channel {sub_idx} at {year}-{month}-{day} {hour}:{minute}:{second}: {error_msg}")
            logger.error(error_msg)
            return False
    except Exception as e:
        logger.exception(f"Error while showing playback video image for channel {ch_no}, sub-channel {sub_idx} at {year}-{month}-{day} {hour}:{minute}:{second}: {str(e)}")
        if ctx: ctx.error(f"An unexpected error occurred: {str(e)}")
        return False

@mcp.tool()
async def show_group_live_video(group_idx: int, ctx: Context = None) -> bool:
    """
    Show the live video streams of a specific group in the VMS program.

    Args:
        group_idx: The index of the group.
        ctx: The context object for logging or error handling.

    Returns:
        True if the operation succeeds, False otherwise.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']) \
            and vms_utils.show_group_live(group_idx):
            logger.debug(f"Live video started for group {group_idx}.")
            return True
        else:
            error_msg = vms_utils.get_error()
            if ctx: ctx.error(f"Failed to show live video for group {group_idx}: {error_msg}")
            logger.error(f"Failed to show live video for group {group_idx}: {error_msg}")
            return False
    except Exception as e:
        logger.exception(f"Error while showing live video for group {group_idx}: {str(e)}")
        if ctx: ctx.error(f"An unexpected error occurred: {str(e)}")
        return False

@mcp.tool()
async def show_group_playback_video(group_idx: int, year: int, month: int, day: int, hour: int, minute: int, second: int, ctx: Context = None) -> bool:
    """
    Show the playback video streams of a specific group at a specific timestamp in the VMS program.

    Args:
        group_idx: The index of the group.
        year: The year of the playback timestamp.
        month: The month of the playback timestamp.
        day: The day of the playback timestamp.
        hour: The hour of the playback timestamp.
        minute: The minute of the playback timestamp.
        second: The second of the playback timestamp.
        ctx: The context object for logging or error handling.

    Returns:
        True if the operation succeeds, False otherwise.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']) \
            and vms_utils.show_group_playback(group_idx, year, month, day, hour, minute, second):
            logger.debug(f"Show playback video for group {group_idx} at {year}-{month}-{day} {hour}:{minute}:{second}.")
            return True
        else:
            error_msg = vms_utils.get_error()
            if ctx: ctx.error(f"Failed to show playback video for group {group_idx} at {year}-{month}-{day} {hour}:{minute}:{second}: {error_msg}")
            logger.error(f"Failed to show playback video for group {group_idx} at {year}-{month}-{day} {hour}:{minute}:{second}: {error_msg}")
            return False
    except Exception as e:
        logger.exception(f"Error while showing playback video for group {group_idx} at {year}-{month}-{day} {hour}:{minute}:{second}: {str(e)}")
        if ctx: ctx.error(f"An unexpected error occurred: {str(e)}")
        return False

@mcp.tool()
async def show_archived_file_playback_video(file_id: int, timestamp: int, ctx: Context = None) -> bool:
    """
    Show the playback video stream of an archived file at a specific timestamp in the VMS program.

    Args:
        file_id: The unique identifier of the archived file.
        timestamp: The Unix timestamp to start playback from.
        ctx: The context object for logging or error handling.

    Returns:
        True if the operation succeeds, False otherwise.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']) \
            and vms_utils.show_file_playback(file_id, timestamp):
            logger.debug(f"Show Playback video started for archived file {file_id} at timestamp {timestamp}.")
            return True
        else:
            error_msg = vms_utils.get_error()
            if ctx: ctx.error(f"Failed to show playback video for archived file {file_id} at timestamp {timestamp}: {error_msg}")
            logger.error(f"Failed to show playback video for archived file {file_id} at timestamp {timestamp}: {error_msg}")
            return False
    except Exception as e:
        logger.exception(f"Error while showing playback video for archived file {file_id} at timestamp {timestamp}: {str(e)}")
        if ctx: ctx.error(f"An unexpected error occurred: {str(e)}")
        return False

def print_header(title, length=80):
    # Ensure the title has a space after it if it's not empty
    formatted_title = f"< {title} >" if title else ""
    # Use ljust to fill the remaining space with '-'
    header = formatted_title.ljust(length, '-')
    print(header)

def print_data(data):
    print("----------------------")
    print(data)

def save_image(img, filename):
    try:
        if img is not None:
            with open(filename, "wb") as f:
                f.write(img.data)
        else:
            print("Failed to fetch the image.")
    except Exception as e:
        print(f"An error occurred: {e}")    

#uv run python .\mcp_vms.py
async def main_test():
    print("\n\n\n")
    if False:
        print_header("get_channels")
        channels = await get_channels()
        print_data(channels)
    if False:
        print_header("get_recording_dates")
        recordingDates = await get_recording_dates(2026, 3)
        print_data(recordingDates)
    if False:
        print_header("get_recording_times")
        recordingTimes = await get_recording_times(5, 0, 2026, 3, 19)
        print_data(recordingTimes)
    if False:
        print_header("get_events")
        events = await get_events(7,2026,3,19)
        print_data(events)
    if False:
        print_header("get_archived_files")
        files = await get_archived_files()
        print_data(files)
        if True:
            for file in files:
                fi = file["file_id"]
                ts = file["timestamp"] + 2
                print (f"file: {fi} / timestamp={ts}")
                #vms_utils.show_file_playback(file["file_id"], ts)
                await show_archived_file_playback_video(fi, ts)
                img = await fetch_archived_file_image(fi, ts)
                save_image(img, f"archived-{fi}-{ts}.jpg")
                time.sleep(1)
    if False:
        for i in range(28):
            await show_playback_video(5, 0, 2026, 3, 19, 7, 0, i*2)
            time.sleep(1)
    if False: # Live subIdx test
        await show_live_video(2, 0)
        time.sleep(1)
        await show_live_video(2, 1)
    if True: # Playback subIdx test
        await show_playback_video(2, 0, 2026, 3, 19, 7, 0, 0)
        time.sleep(1)
        await show_playback_video(2, 1, 2026, 3, 19, 7, 0, 0)
    if False:
        img = await fetch_live_image(2, 0)
        save_image(img, "vms_image-0.jpg")
        img = await fetch_live_image(2, 1)
        save_image(img, "vms_image-1.jpg")
    if False:
        img = await fetch_recorded_image(2, 0, 2026, 3, 19, 7, 0, 0)
        save_image(img, "vms_image-0.jpg")
        img = await fetch_recorded_image(2, 1, 2026, 3, 19, 7, 0, 0)
        save_image(img, "vms_image-1.jpg")

# Run the async main function
if __name__ == "__main__":
    if False:
        mcp.run(transport='stdio')
        #mcp.run(transport='sse')
    else:
        asyncio.run(main_test())
