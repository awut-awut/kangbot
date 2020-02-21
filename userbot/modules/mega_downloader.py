# Copyright (C) 2020 Adek Maulana.
# All rights reserved.
#
# Redistribution and use of this script, with or without modification, is
# permitted provided that the following conditions are met:
#
# 1. Redistributions of this script must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
#  THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS" AND ANY EXPRESS OR IMPLIED
#  WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO
#  EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
#  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
#  WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
#  OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#  ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from subprocess import PIPE, Popen

import re
import json
import os

from pySmartDL import SmartDL
from os.path import exists
from urllib.error import HTTPError

from userbot import CMD_HELP, LOGS
from userbot.events import register


def subprocess_run(cmd):
    reply = ''
    subproc = Popen(cmd, stdout=PIPE, stderr=PIPE,
                    shell=True, universal_newlines=True)
    talk = subproc.communicate()
    exitCode = subproc.returncode
    if exitCode != 0:
        reply += ('An error was detected while running the subprocess:\n'
                  f'exit code: {exitCode}\n'
                  f'stdout: {talk[0]}\n'
                  f'stderr: {talk[1]}')
        return reply
    return talk


@register(outgoing=True, pattern=r"^.mega(?: |$)(.*)")
async def mega_downloader(megadl):
    await megadl.edit("`Processing...`")
    textx = await megadl.get_reply_message()
    link = megadl.pattern_match.group(1)
    if link:
        pass
    elif textx:
        link = textx.text
    else:
        await megadl.edit("`Usage: .mega <mega url>`")
        return
    if not link:
        await megadl.edit("`No MEGA.nz link found!`")
    await mega_download(link, megadl)


async def mega_download(url, megadl):
    try:
        link = re.findall(r'\bhttps?://.*mega.*\.nz\S+', url)[0]
    except IndexError:
        await megadl.edit("`No MEGA.nz link found`\n")
        return
    cmd = f'bin/megadirect {link}'
    result = subprocess_run(cmd)
    try:
        data = json.loads(result[0])
    except json.JSONDecodeError:
        await megadl.edit("`Error: Can't extract the link`\n")
        return
    file_name = data['file_name']
    file_url = data['url']
    file_hex = data['hex']
    file_raw_hex = data['raw_hex']
    if exists(file_name):
        os.remove(file_name)
    if not exists(file_name):
        temp_file_name = file_name + '.temp'
        downloaded_file_name = "./" + "" + temp_file_name
        downloader = SmartDL(file_url, downloaded_file_name, progress_bar=False)
        try:
            downloader.start(blocking=False)
        except HTTPError as e:
            await megadl.edit(str(e))
            LOGS.info(str(e))
            return
        display_message = None
        while not downloader.isFinished():
            status = downloader.get_status().capitalize()
            total_length = downloader.filesize if downloader.filesize else None
            downloaded = downloader.get_dl_size()
            percentage = int(downloader.get_progress() * 100)
            progress = downloader.get_progress_bar()
            speed = downloader.get_speed(human=True)
            estimated_total_time = downloader.get_eta(human=True)
            try:
                current_message = (
                    f"**{status}**..."
                    f"\nFile Name: `{file_name}`\n"
                    f"\n{progress} `{percentage}%`"
                    f"\n{humanbytes(downloaded)} of {humanbytes(total_length)}"
                    f" @ {speed}"
                    f"\nETA: {estimated_total_time}"
                )
                if display_message != current_message:
                    await megadl.edit(current_message)
                    display_message = current_message
            except Exception as e:
                LOGS.info(str(e))
        if downloader.isSuccessful():
            download_time = downloader.get_dl_time(human=True)
            if exists(temp_file_name):
                await megadl.edit("Decrypting file...")
                decrypt_file(file_name, temp_file_name, file_hex, file_raw_hex)
                await megadl.edit(f"`{file_name}`\n\n"
                                  "Successfully downloaded\n"
                                  f"Download took: {download_time}")
        else:
            await megadl.edit("Failed to download...")
            for e in downloader.get_errors():
                LOGS.info(str(e))
    return


def decrypt_file(file_name, temp_file_name, file_hex, file_raw_hex):
    cmd = ("cat '{}' | openssl enc -d -aes-128-ctr -K {} -iv {} > '{}'"
           .format(temp_file_name, file_hex, file_raw_hex, file_name))
    subprocess_run(cmd)
    os.remove(r"{}".format(temp_file_name))
    return


def humanbytes(size):
    """Input size in bytes,
    outputs in a human readable format"""
    # https://stackoverflow.com/a/49361727/4723940
    if not size:
        return ""
    # 2 ** 10 = 1024
    power = 2**10
    raised_to_pow = 0
    dict_power_n = {0: "", 1: "Ki", 2: "Mi", 3: "Gi", 4: "Ti"}
    while size > power:
        size /= power
        raised_to_pow += 1
    return str(round(size, 2)) + " " + dict_power_n[raised_to_pow] + "B"


CMD_HELP.update({
    "mega":
    ".mega <mega url>\n"
    "Usage: Reply to a mega link or paste your mega link to\n"
    "download the file into your userbot server\n\n"
    "Only support for *FILE* only.\n"
})
