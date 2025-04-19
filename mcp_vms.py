#!/usr/bin/env python3

import os
import sys
import asyncio
import logging
from io import BytesIO
from datetime import datetime
from PIL import Image as PILImage
from mcp.server.fastmcp import FastMCP, Image, Context
from typing import List, Dict, Any
from mcp_vms_config import vms_config

import vmspy # type: ignore

DATA_DIR = "./data"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)

# Configure logging: first disable other loggers
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)

# Configure our logger
log_filename = os.path.join(DATA_DIR, datetime.now().strftime("%d-%m-%y.log"))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create handlers
file_handler = logging.FileHandler(log_filename)
file_handler.setFormatter(formatter)
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setFormatter(formatter)

# Set up our logger
logger = logging.getLogger("image-mcp")
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
async def get_channels(ctx: Context) -> List[Dict[str, Any]]:
    """
    Return a list of dictionaries containing video channel information.

    Each dictionary contains the following keys:
    - ch_no: The channel number.
    - title: The name or title of the channel.
    - is_connected: A boolean indicating whether the channel is currently connected.
    - is_recording: A boolean indicating whether the channel is currently recording.
    - is_ptz: A boolean indicating whether the channel is a PTZ (Pan-Tilt-Zoom) camera.
    - ptz_prestes: A list of PTZ presets, available only when is_ptz is True.
    - time_start: The earliest recording time of the channel
    - time_end: The latest recording time of the channel
    - sub_channel_count: The number of sub-channels associated with this channel.

    Args:
        ctx: The context object for logging or error handling.

    Returns:
        A list of dictionaries, where each dictionary contains information about a video channel.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
            channels = vms_utils.get_channel_list()
            logger.debug(f"Returning names: {channels}")
        else:
            error_msg = vms_utils.get_error()
            ctx.error(f"Failed to get channel list: {error_msg}")
            logger.debug(f"Failed to get channel list: {channels}")
            channels = []
        return channels
    except Exception as e:
        logger.exception("Error in get_names")
        ctx.error(f"Failed to retrieve names: {str(e)}")
        return []

@mcp.tool()
async def get_recording_dates(year: int, month: int, ctx: Context) -> List[Dict[str, Any]]:
    """
    Retrieve recording dates for video channels for a specific year and month.

    This function fetches the recording dates for all channels within the specified time range.

    Args:
        year: The year for which to retrieve recording dates.
        month: The month for which to retrieve recording dates.
        ctx: The context object for logging or error handling.

    Returns:
        A list of dictionaries, each containing:
        - ch_no: The channel ID.
        - title: The name or title of the channel.
        - dates: A list of recording dates for the channel.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
            recording_dates = vms_utils.get_recording_dates(year, month)
            logger.debug(f"Retrieved recording dates for {year}-{month}: {recording_dates}")
            return recording_dates
        else:
            error_msg = vms_utils.get_error()
            ctx.error(f"Fail to get recorind dates for {year}-{month}: {error_msg}")
            logger.error(error_msg)
            return []
    except Exception as e:
        logger.exception(f"Error in get_recording_dates for {year}-{month}")
        ctx.error(f"Failed to retrieve recording dates for {year}-{month}: {str(e)}")
        return []

@mcp.tool()
async def get_recording_times(ch_no: int, sub_idx: int, year: int, month: int, day: int, ctx: Context) -> List[Dict[str, Any]]:
    """
    Retrieve recording times for a specific channel, sub-channel, and date.

    This function fetches the recording times for a given channel and sub-channel on a specific day.

    Args:
        ch_no: The channel number.
        sub_idx: The sub-channel index.
        year: The year for which to retrieve recording times.
        month: The month for which to retrieve recording times.
        day: The day for which to retrieve recording times.
        ctx: The context object for logging or error handling.

    Returns:
        A list of dictionaries, each containing:
        - 'start': The start time of the recording in ISO 8601 format.
        - 'duration': The duration of the recording in seconds.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']):
            recording_times = vms_utils.get_recording_times(ch_no, year, month, day, sub_idx)
            logger.debug(f"Retrieved recording times for channel {ch_no}, sub-channel {sub_idx} on {year}-{month}-{day}: {recording_times}")
            return {
                "ch": ch_no,
                "sub": sub_idx,
                "title": f"Channel {ch_no}",  # Replace with actual title if available
                "recordings": recording_times
            }
        else:
            error_msg = vms_utils.get_error()
            ctx.error(f"Fail to get recording times for channel {ch_no}: {error_msg}")
            logger.error(error_msg)
            return []
    except Exception as e:
        logger.exception(f"Error in get_recording_times for channel {ch_no}, sub-channel {sub_idx} on {year}-{month}-{day}")
        ctx.error(f"Failed to retrieve recording times for channel {ch_no}, sub-channel {sub_idx} on {year}-{month}-{day}: {str(e)}")
        return []

@mcp.tool() 
def fetch_live_image(ch_no: int, sub_idx: int, ctx: Context) -> Image | None:
    """
    Fetch a specific live frame image from a video channel.

    This function retrieves a frame image for a given channel, sub-channel, and timestamp.

    Args:
        ch_id: The channel ID.
        sub_idx: The sub-channel index.
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
            ctx.error(error_msg)
            logger.error(error_msg)
            return None

        # Convert the numpy array (frame_image) to a JPEG using PIL
        img = PILImage.fromarray(frame_image)
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format="JPEG")
        image_data = img_byte_arr.getvalue()

        # with open("output_image.jpg", "wb") as f:
        #     f.write(image_data)
        logger.debug(f"Fetched live image for channel {ch_no}, sub-channel {sub_idx}.")
        return Image(data=image_data, format="jpeg")
    else:
        error_msg = f"Failed to initialize connection to retrieve recording times for channel {ch_no}, sub-channel {sub_idx}."
        ctx.error(error_msg)
        logger.error(error_msg)
        return {"error": error_msg}

@mcp.tool() 
def fetch_recorded_image(ch_no: int, sub_idx: int, year: int, month: int, day: int, hour: int, minute: int, second: int, ctx: Context) -> Image | None:
    """
    Fetch a specific recorded frame image from a video channel.

    This function retrieves a frame image for a given channel, sub-channel, and timestamp.

    Args:
        ch_id: The channel ID.
        sub_idx: The sub-channel index.
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
            ctx.error(error_msg)
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
        ctx.error(error_msg)
        logger.error(error_msg)
        return {"error": error_msg}

@mcp.tool()
async def move_ptz_to_preset(ch_no: int, preset_no: int, ctx: Context) -> bool:
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
            ctx.error(f"Failed to move PTZ camera on channel {ch_no} to preset {preset_no}: {error_msg}")
            logger.error(error_msg)
            return False

    except Exception as e:
        logger.exception(f"Error while moving PTZ camera on channel {ch_no} to preset {preset_no}: {str(e)}")
        ctx.error(f"An unexpected error occurred: {str(e)}")
        return False

@mcp.tool()
async def get_ptz_preset(ch_no: int, ctx: Context) -> Dict[str, Any]:
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
                ctx.error(error_msg)
                logger.error(error_msg)
                return [{"no": None, "title": None, "status": error_msg}]
        else:
            error_msg = f"Failed to initialize connection to retrieve PTZ presets for channel {ch_no}."
            ctx.error(error_msg)
            logger.error(error_msg)
            return [{"no": None, "title": None, "status": error_msg}]
    except Exception as e:
        logger.exception(f"Error while retrieving PTZ presets for channel {ch_no}: {str(e)}")
        ctx.error(f"An unexpected error occurred: {str(e)}")
        return [{"no": None, "title": None, "status": f"Error: {str(e)}"}]

@mcp.tool()
async def show_live_video(ch_no: int, sub_idx: int, ctx: Context) -> bool:
    """
    Show the live video stream of a specific channel in the VMS program.

    Args:
        ch_no: The channel number.
        sub_idx: The sub-channel index.
        ctx: The context object for logging or error handling.

    Returns:
        True if the operation succeeds, False otherwise.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']) \
            and vms_utils.show_live(ch_no, sub_idx):
            logger.debug(f"Live video started for channel {ch_no}, sub-channel {sub_idx}.")
            return True
        else:
            error_msg = vms_utils.get_error()
            ctx.error(f"Failed to show live video for channel {ch_no}, sub-channel {sub_idx}: {error_msg}")
            logger.error(error_msg)
            return False
    except Exception as e:
        logger.exception(f"Error while showing live video for channel {ch_no}, sub-channel {sub_idx}: {str(e)}")
        ctx.error(f"An unexpected error occurred: {str(e)}")
        return False

@mcp.tool()
async def show_playback_video(ch_no: int, year: int, month: int, day: int, hour: int, minute: int, second: int, sub_idx: int, ctx: Context) -> bool:
    """
    Show the playback video stream of a specific channel at a specific timestamp in the VMS program.

    Args:
        ch_no: The channel number.
        year: The year of the playback timestamp.
        month: The month of the playback timestamp.
        day: The day of the playback timestamp.
        hour: The hour of the playback timestamp.
        minute: The minute of the playback timestamp.
        second: The second of the playback timestamp.
        sub_idx: The sub-channel index.
        ctx: The context object for logging or error handling.

    Returns:
        True if the operation succeeds, False otherwise.
    """
    try:
        if vms_utils.init(vms_config['url'], vms_config['port'], vms_config['access_id'], vms_config['access_pw']) \
            and vms_utils.show_playback(ch_no, year, month, day, hour, minute, second, sub_idx):
            logger.debug(f"Playback video started for channel {ch_no}, sub-channel {sub_idx} at {year}-{month}-{day} {hour}:{minute}:{second}.")
            return True
        else:
            error_msg = vms_utils.get_error()
            ctx.error(f"Failed to show playback video for channel {ch_no}, sub-channel {sub_idx} at {year}-{month}-{day} {hour}:{minute}:{second}: {error_msg}")
            logger.error(error_msg)
            return False
    except Exception as e:
        logger.exception(f"Error while showing playback video for channel {ch_no}, sub-channel {sub_idx} at {year}-{month}-{day} {hour}:{minute}:{second}: {str(e)}")
        ctx.error(f"An unexpected error occurred: {str(e)}")
        return False

# Run the async main function
if __name__ == "__main__":
    mcp.run(transport='stdio')
