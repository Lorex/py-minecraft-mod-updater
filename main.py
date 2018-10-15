#!python3

import io
import os
import sys
import logging
import coloredlogs
import subprocess
import urllib.request
import yaml
import base64
import json
import time
import psutil
import shutil
import git
from git import RemoteProgress
from git import Repo

# 是否輸出 DEBUG 訊息?
DEBUG = False
VERSION_URL = "http://gitlab.sita.tech/api/v4/projects/23/repository/files/?file_path=version.yml&ref=master"

# 全域變數
logger = logging.getLogger(__name__)
# 設定 git 路徑
os.environ['GIT_PYTHON_GIT_EXECUTABLE'] = os.getcwd() + '\\git\\bin\\git.exe'


def reporthook(count, block_size, total_size):
    global start_time
    if count == 0:
        start_time = time.time()
        return
    duration = time.time() - start_time
    progress_size = int(count * block_size)
    if duration == 0:
        return
    speed = int(progress_size / (1024 * duration))
    percent = min(int(count*block_size*100/total_size), 100)
    sys.stdout.write("\r...%d%%, %d MB, %d KB/s，花費時間： %d 秒" %
                     (percent, progress_size / (1024 * 1024), speed, duration))
    sys.stdout.flush()



class gitProgressHook(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        percent = int(cur_count / (max_count or 100.0) *100)
        sys.stdout.write("\r...正在同步檔案：%d / %d，已完成： %d%%" % (cur_count, max_count or 100, percent))
        sys.stdout.flush()




def main():
    print('''
    ===================================
    |     普羅伺服器 自動更新程式     |
    |           v1.0.181015           |
    ===================================
    ''')

    # 設定 Minecraft root path
    MINECRAFT_PATH = os.getenv('APPDATA') + '\\.minecraft'

    # =====================
    # 進行前置檢查
    # =====================

    # 檢查是否能對外連線
    logger.info('初始化連線中...')
    ping = os.system("ping -c 1 gitlab.sita.tech > nul 2>nul")
    if not ping == 0:
        logging.fatal('錯誤：無法連線到更新伺服器！')
        os._exit(1)
    logger.success('已成功連線到更新伺服器！')

    # 找更新描述檔然後 parse 他
    logger.info('正在下載更新描述檔...')
    get_json = json.loads(urllib.request.urlopen(
        VERSION_URL).read().decode('utf-8'))
    raw_info = base64.b64decode(get_json['content']).decode('utf-8')
    INFO = yaml.load(raw_info)

    logger.success('下載完成！')
    logger.info('')
    logger.info('Java 版本需求：' + INFO['JAVA_VERSION'])
    logger.info('Forge 版本需求：' + INFO['FORGE_VERSION'])
    logger.info('最新模組包版本：' + INFO['MODPACK_VERSION'])
    logger.info('')

    # 檢查 Minecraft 是否已安裝，沒有的話直接死給你看
    logging.info('偵測安裝中...')
    if not os.path.isdir(MINECRAFT_PATH):
        logger.fatal('錯誤：找不到 Minecraft 安裝路徑，你可能沒安裝 Minecraft？')
        os._exit(1)

    # 檢查有沒有安裝 Java，沒有的話直接死給你看
    logger.info('檢查 Java 版本中...')

    from shutil import which

    if which('java') is None:
        logger.fatal('錯誤：找不到 Java，哥你在跟我開玩笑吧？')
        os._exit(1)
    else:
        sp = (subprocess.check_output(
            ['java', '-version'], stderr=subprocess.STDOUT)).decode('utf-8')
        if sp.find(INFO['JAVA_VERSION']) == -1:
            logger.fatal('錯誤：Java 版本不正確，必須為 ' + INFO['JAVA_VERSION'] + ' 版本')
            os._exit(1)
        else:
            logger.success('已安裝正確版本的 Java！')

    # 檢查 Forge 有沒有安裝，版本對不對
    logger.info('檢查 Forge 版本中...')
    if not os.path.isdir(MINECRAFT_PATH + '\\versions\\' + INFO['FORGE_VERSION']):
        # 沒安裝
        # 下載新版 Forge
        logger.warning('警告：Forge 版本不正確，必須為 ' + INFO['FORGE_VERSION'] + ' 版本')
        logger.info('  正在下載 Forge...')
        urllib.request.urlretrieve(INFO['FORGE_LINK'], 'forge.exe', reporthook)
        print('')
        logger.success('  下載完成！')
        logger.info('  開始安裝 Forge...')
        os.system('.\\forge.exe')
        
        # 等待 Forge 跑完
        while "javaw.exe" in (p.name() for p in psutil.process_iter()):
            time.sleep(1)

        logger.success('  安裝完成！')
    else:
        logger.success('已安裝正確版本的 Forge！')

    # =====================
    # 更新模組包
    # =====================

    # inner def function: init_mods()
    def init_mods():
        git.Repo.clone_from(
            url=INFO['GIT_URL'],
            to_path=MINECRAFT_PATH + '\\mods',
            progress=gitProgressHook()
        )

        logger.info('')
        logger.success('模組初始化成功！')
        logger.success('已成功安裝最新版本模組，目前版本：' + INFO['MODPACK_VERSION'])
        logger.success('您現在已經可以開始遊戲！')
        os.system('pause')
        os._exit(0)

    # inner def function: pull_mods()
    def pull_mods():
        logger.info('正在進行更新中...')
        repo = Repo(MINECRAFT_PATH + '\\mods')
        
        # 如果被竄改過則還原
        if repo.is_dirty() == True:
            repo.index.checkout(force = True)
        
        remote = repo.remote()
        remote.pull(progress=gitProgressHook())

        logger.info('')
        logger.success('模組更新成功！')
        logger.success('已成功安裝最新版本模組，目前版本：' + INFO['MODPACK_VERSION'])
        logger.success('您現在已經可以開始遊戲！')
        os.system('pause')
        os._exit(0)

    # 檢查 git 是否可用
        if not os.path.isfile(os.environ['GIT_PYTHON_GIT_EXECUTABLE']):
            logger.fatal('錯誤：找不到相依性套件，自動更新程式可能已毀損，請重新至以下連結下載自動更新程式：')
            logger.fatal(INFO['UPDATOR_LINK'])
            os._exit(1)

    # 檢查 Git 是否已經 init 好
    logger.info('')
    logger.info('檢查模組資料夾狀態...')
    if not os.path.isdir(MINECRAFT_PATH + '\\mods'):
        logger.warning('模組資料夾不存在，將開始進行資料夾初始化...')
        init_mods()
    if not os.path.isdir(MINECRAFT_PATH + '\\mods\\.git'):
        # 砍掉 mod 資料夾
        logger.warning('尚未初始化，進行資料夾初始化並安裝最新版模組中...')
        logger.warning('注意：此操作將會移除原有 mods 資料夾內的所有模組！')

        os.chdir(MINECRAFT_PATH)
        shutil.rmtree(MINECRAFT_PATH + '\\mods')

        init_mods()
    
    logger.info('檢查模組包版本狀態...')
    # 檢查本機版本描述檔是否存在
    if not os.path.isfile(MINECRAFT_PATH + '\\mods\\version.yml'):
        repo = Repo(MINECRAFT_PATH + '\\mods')
        logger.error('錯誤：本機版本描述檔已毀損，進行檔案復原中...')
        repo.index.checkout(force=True)
        logger.success('檔案復原完成！')
        
    with open(MINECRAFT_PATH + '\\mods\\version.yml', 'r', encoding='utf-8') as f:
        doc = yaml.load(f)
    CURRENT = doc


    # 檢查是否有新版本
    if not CURRENT['MODPACK_VERSION'] == INFO['MODPACK_VERSION']:
        logger.warning('有可用的更新！')
        logger.warning('本機模組包版本：' + CURRENT['MODPACK_VERSION'])
        logger.warning('最新模組包版本：' + INFO['MODPACK_VERSION'])
        
        pull_mods()
    else:
        logger.success('無可用更新！')
        repo = Repo(MINECRAFT_PATH + '\\mods')

        # 如果被竄改過則還原
        if repo.is_dirty() == True:
            logger.warning('偵測到模組檔案已變更！')
            logger.warning('進行檔案復原中...')
            repo.index.checkout(force=True)
            logger.success('檔案復原完成！')

        logger.info('')
        logger.success('您安裝的是最新版本模組，目前版本：' + INFO['MODPACK_VERSION'])
        logger.success('您現在已經可以開始遊戲！')
        os.system('pause')
        os._exit(0)

        



if __name__ == "__main__":

    # 設定視窗顏色
    os.system('color 0f')

    # 新增 Logger 種類
    logging.SUCCESS = 25  # between WARNING and INFO
    logging.addLevelName(logging.SUCCESS, 'SUCCESS')
    setattr(logger, 'success', lambda message, *
            args: logger._log(logging.SUCCESS, message, args))

    # 設定 Logger
    if DEBUG:
        coloredlogs.install(
            level='DEBUG',
            fmt='[%(levelname)-.1s] %(message)s'
        )
    else:
        coloredlogs.install(
            level='INFO',
            fmt='[%(levelname)-.1s] %(message)s'
        )

    # 清除畫面然後開始，我好想睡覺，幹。
    os.system('cls')
    main()
