from asyncio import create_subprocess_exec as exec
import json
from subprocess import Popen, PIPE
from bot import LOGGER
from bot.helper.ext_utils.human_format import human_readable_bytes
from bot.helper.ext_utils.message_utils import editMessage
from bot.helper.ext_utils.misc_utils import ButtonMaker, get_rclone_config
from bot.helper.ext_utils.var_holder import get_rclone_var
from bot.helper.mirror_leech_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_leech_utils.status_utils.status_utils import MirrorStatus, TelegramClient


class RcloneCopy:
    def __init__(self, message, user_id) -> None:
        self.__message = message
        self._user_id= user_id
        self.__rclone_pr= None

    async def copy(self):
        conf_path = get_rclone_config(self._user_id)
        button= ButtonMaker()
        origin_drive = get_rclone_var("COPY_ORIGIN_DRIVE", self._user_id)
        origin_dir = get_rclone_var("COPY_ORIGIN_DIR", self._user_id)
        dest_drive = get_rclone_var("COPY_DESTINATION_DRIVE", self._user_id)
        dest_dir = get_rclone_var("COPY_DESTINATION_DIR", self._user_id)

        cmd = ['rclone', 'copy', f'--config={conf_path}', f'{origin_drive}:{origin_dir}',
                       f'{dest_drive}:{dest_dir}{origin_dir}', '-P']

        rclone_pr = Popen(cmd, stdout=(PIPE),stderr=(PIPE))
        self.__rclone_pr= rclone_pr
        rc_status= RcloneStatus(rclone_pr, self.__message)
        status= await rc_status.progress(status_type= MirrorStatus.STATUS_COPYING, 
                            client_type=TelegramClient.PYROGRAM)
        if status:
            #Get Link
            cmd = ["rclone", "link", f'--config={conf_path}', f"{dest_drive}:{dest_dir}{origin_dir}"]
            process = await exec(*cmd, stdout=PIPE, stderr=PIPE)
            out, err = await process.communicate()
            url = out.decode().strip()
            button.url_buildbutton("GDrive Link", url)
            return_code = await process.wait()
            if return_code != 0:
                LOGGER.info(err.decode().strip())

            #Calculate Size
            cmd = ["rclone", "size", f'--config={conf_path}', "--json", f"{dest_drive}:{dest_dir}{origin_dir}"]
            process = await exec(*cmd, stdout=PIPE, stderr=PIPE)
            out, _ = await process.communicate()
            output = out.decode().strip()
            data = json.loads(output)
            files = data["count"]
            size = human_readable_bytes(data["bytes"])
            
            format_out = f"**Total Files** {files}\n" 
            format_out += f"**Total Size**: {size}"
            await editMessage(format_out, self.__message, reply_markup= button.build_menu(1))
        else:
            self.__rclone_pr.kill()
            await editMessage("Copy Cancelled", self.__message)    