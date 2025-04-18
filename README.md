# MCP Server - VMS Integration

A Model Context Protocol (MCP) server designed to connect to a CCTV recording program (VMS) to retrieve recorded and live video streams. It also provides tools to control the VMS software, such as showing live or playback dialogs for specific channels at specified times.

## Features

- Retrieve video channel information, including connection and recording status.
- Fetch recording dates and times for specific channels.
- Fetch live or recorded images from video channels.
- Show live video streams or playback dialogs for specific channels and timestamps.
- Control PTZ (Pan-Tilt-Zoom) cameras by moving them to preset positions.
- Comprehensive error handling and logging.

## Prerequisites

- Python 3.12+
- `vmspy` library (for VMS integration)
- `Pillow` library (for image processing)

## Configuration

The server uses the following default configuration for connecting to the VMS:
- mcp_vms_config.py
```python
vms_config = {
    'img_width': 320,
    'img_height': 240,
    'pixel_format': 'RGB',
    'url': '127.0.0.1',
    'port': 3300,
    'access_id': 'admin',
    'access_pw': 'admin',
}
```

## Install VMS Server

You need to install the VMS server from http://surveillance-logic.com. Please download and install it before using this MCP server.

Also, download the vmspy Python library from the link below and extract the files into the mcp_vms directory:
https://sourceforge.net/projects/security-vms/files/vmspy-1.2-python312-x64.zip/download
