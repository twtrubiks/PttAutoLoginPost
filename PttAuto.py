"""PTT 自動登入發文工具 - Python 3.13 版本

注意：PTT 已關閉 telnet 連線，改用 SSH 連線
"""

import sys
import asyncio
import re
from typing import Optional
try:
    import asyncssh
except ImportError:
    print("錯誤：需要安裝 asyncssh")
    print("請執行：pip install asyncssh")
    sys.exit(1)


class Ptt:
    def __init__(self, host: str, user: str, password: str) -> None:
        """初始化 PTT SSH 連線

        Args:
            host: PTT 主機位址
            user: PTT 使用者帳號
            password: PTT 使用者密碼
        """
        self._host: str = host
        self._user: str = user
        self._password: str = password
        self._ssh_conn: Optional[asyncssh.SSHClientConnection] = None
        self._ssh_process: Optional[asyncssh.SSHClientProcess] = None
        self._content: str = ''
        self._connected: bool = False

    async def is_success(self) -> bool:
        """檢查登入狀態並處理各種情況

        Returns:
            bool: 登入是否成功
        """
        # 檢查登入失敗情況
        if "密碼不對" in self._content:
            print("密碼不對或無此帳號。程式結束")
            # 立即斷開連線，不再進行其他操作
            await self.disconnect()
            return False

        # 處理重複登入
        if "您想刪除其他重複登入" in self._content:
            print("刪除其他重複登入的連線....")
            await self._write_data("y\r\n")
            await asyncio.sleep(10)
            self._content = await self._read_data()

        # 處理其他提示
        if "請按任意鍵繼續" in self._content:
            print("資訊頁面，按任意鍵繼續...")
            await self._write_data("\r\n")
            await asyncio.sleep(6)
            self._content = await self._read_data()

        if "您要刪除以上錯誤嘗試" in self._content:
            print("刪除以上錯誤嘗試...")
            await self._write_data("y\r\n")
            await asyncio.sleep(6)
            self._content = await self._read_data()

        if "您有一篇文章尚未完成" in self._content:
            print('刪除尚未完成的文章....')
            await self._write_data("q\r\n")
            await asyncio.sleep(6)
            self._content = await self._read_data()

        # 最終檢查登入狀態
        return await self._check_final_login_status()

    async def _check_final_login_status(self) -> bool:
        """檢查最終登入狀態

        Returns:
            bool: 是否成功登入到主選單
        """
        # 檢查是否到達主選單
        success_indicators = [
            "主功能表",
            "(M)ail",
            "(A)nnounce",
            "(F)avorite",
            "(T)alk",
            "(U)ser",
            "(C)hat",
            "(P)lay",
            "(N)amelist",
            "(G)oodbye"
        ]

        if any(indicator in self._content for indicator in success_indicators):
            print("登入成功！")
            return True
        else:
            print("登入狀態不明確，可能需要進一步處理")
            return False

    async def input_user_password(self) -> bool:
        """輸入使用者帳號密碼

        Returns:
            bool: 是否成功輸入帳號密碼
        """
        # 檢查多種可能的提示文字
        login_prompts = [
            "請輸入代號",
            "代號",
            "guest",
            "new",
            "輸入代號"
        ]

        # 檢查是否包含任何登入提示
        has_login_prompt = any(prompt in self._content for prompt in login_prompts)

        if has_login_prompt:
            print('輸入帳號中...')
            await self._write_data(self._user + "\r\n")
            await asyncio.sleep(1)
            print('輸入密碼中...')
            await self._write_data(self._password + "\r\n")
            await asyncio.sleep(3)
            self._content = await self._read_data(timeout=5.0)
            return await self.is_success()
        else:
            print("未找到登入提示，網站可能繁忙或連線異常")
            return False

    async def connect(self) -> bool:
        """使用 luit + SSH 連線到 PTT

        Returns:
            bool: 連線是否成功
        """
        try:
            # 使用 luit -encoding big5 ssh bbs@ptt.cc 的方式連線
            # 這樣可以正確處理 Big5 編碼
            self._ssh_conn = await asyncssh.connect(
                self._host,
                username='bbs',       # 使用 bbs 作為使用者名稱
                password=None,        # SSH 不需要密碼
                known_hosts=None,     # 忽略 host key 檢查
                client_keys=None      # 不使用密鑰認證
            )

            # 啟動互動式 shell，模擬 luit 的環境
            self._ssh_process = await self._ssh_conn.create_process(
                term_type='vt100',     # 使用 vt100 終端類型
                term_size=(80, 24),    # 標準終端尺寸
                encoding='big5',       # 設定 Big5 編碼
                env={
                    'LANG': 'zh_TW.Big5',
                    'LC_ALL': 'zh_TW.Big5',
                    'TERM': 'vt100'
                },
                errors='replace'       # 用替換字符處理編碼錯誤
            )

            self._connected = True

            # 讀取初始歡迎訊息
            await asyncio.sleep(3)
            data = await self._read_data(timeout=5.0)
            self._content = data

            if "系統過載" in self._content:
                print('系統過載, 請稍後再來')
                await self.disconnect()
                sys.exit(1)
            return True
        except Exception as e:
            print(f"SSH 連線錯誤: {e}")
            return False

    async def disconnect(self) -> None:
        """斷開 SSH 連線"""
        if not self._connected:
            return

        print("正在斷開 SSH 連線...")
        try:
            if self._ssh_process:
                try:
                    self._ssh_process.close()
                    # 設置 3 秒超時，避免無限等待
                    await asyncio.wait_for(self._ssh_process.wait_closed(), timeout=3.0)
                except asyncio.TimeoutError:
                    print("SSH process 關閉超時，強制結束")
                except Exception as e:
                    print(f"關閉 SSH process 時發生錯誤: {e}")

            if self._ssh_conn:
                try:
                    self._ssh_conn.close()
                    # 設置 3 秒超時，避免無限等待
                    await asyncio.wait_for(self._ssh_conn.wait_closed(), timeout=3.0)
                except asyncio.TimeoutError:
                    print("SSH 連線關閉超時，強制結束")
                except Exception as e:
                    print(f"關閉 SSH 連線時發生錯誤: {e}")

        except Exception as e:
            print(f"斷開連線過程中發生未預期錯誤: {e}")
        finally:
            self._ssh_process = None
            self._ssh_conn = None
            self._connected = False
            print("SSH 連線已斷開")

    async def _read_data(self, timeout: float = 3.0) -> str:
        """讀取 SSH 資料

        Args:
            timeout: 讀取超時時間

        Returns:
            str: 讀取到的資料
        """
        if not self._ssh_process:
            return ''

        try:
            # 由於已經設定 encoding='big5'，asyncSSH 會自動處理編碼
            data = await asyncio.wait_for(
                self._ssh_process.stdout.read(4096), timeout=timeout
            )

            if data:
                # 移除 ANSI 控制字符和其他終端控制字符
                clean_data = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', data)
                clean_data = re.sub(r'\x1b\([AB]', '', clean_data)
                clean_data = re.sub(r'\x1b\]0;[^\x07]*\x07', '', clean_data)  # 移除標題設定
                clean_data = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', clean_data)

                return clean_data
            return ''
        except asyncio.TimeoutError:
            return ''
        except Exception as e:
            print(f"讀取資料錯誤: {e}")
            return ''

    async def _write_data(self, data: str) -> None:
        """寫入 SSH 資料

        Args:
            data: 要寫入的資料
        """
        if not self._connected:
            print("連線已斷開，無法寫入資料")
            return

        if self._ssh_process and self._ssh_process.stdin:
            # 由於已經設定 encoding='big5'，asyncSSH 會自動處理編碼
            try:
                self._ssh_process.stdin.write(data)
                # 設置超時避免無限等待
                await asyncio.wait_for(self._ssh_process.stdin.drain(), timeout=2.0)
            except asyncio.TimeoutError:
                print("寫入資料超時")
                # 連線可能有問題，標記為斷開
                self._connected = False
            except Exception as e:
                print(f"寫入資料錯誤: {e}")
                # 連線可能有問題，標記為斷開
                self._connected = False

    async def login(self) -> bool:
        """執行登入程序

        Returns:
            bool: 登入是否成功
        """
        try:
            if await self.input_user_password():
                print("----------------------------------------------")
                print("------------------ 登入完成 ------------------")
                print("----------------------------------------------")
                return True
            print("沒有可輸入帳號的欄位，網站可能掛了")
            return False
        except Exception as e:
            print(f"登入過程發生錯誤: {e}")
            return False

    async def logout(self) -> None:
        """執行登出程序"""
        try:
            print("登出中...")
            # q = 上一頁，直到回到首頁為止，g = 離開，再見
            await self._write_data("qqqqqqqqqg\r\ny\r\n")
            await asyncio.sleep(1)
            await self.disconnect()
            print("----------------------------------------------")
            print("------------------ 登出完成 ------------------")
            print("----------------------------------------------")
        except Exception as e:
            print(f"登出過程發生錯誤: {e}")
            try:
                await self.disconnect()
            except Exception:
                pass

    async def post(self, board: str, title: str, content: str) -> bool:
        """在指定看板發文

        Args:
            board: 看板名稱
            title: 文章標題
            content: 文章內容

        Returns:
            bool: 發文是否成功
        """
        try:
            print("發文中...")
            # s 進入要發文的看板
            await self._write_data('s')
            await self._write_data(board + '\r\n')
            await asyncio.sleep(1)
            await self._write_data('q')
            await asyncio.sleep(2)
            # 請參考 http://donsnotes.com/tech/charsets/ascii.html#cntrl
            # Ctrl+P
            await self._write_data('\x10')
            # 發文類別
            await self._write_data('1\r\n')
            await self._write_data(title + '\r\n')
            await asyncio.sleep(1)
            # Ctrl+X
            await self._write_data(content + '\x18')
            await asyncio.sleep(1)
            # 儲存文章
            await self._write_data('s\r\n')
            # 不加簽名檔
            await self._write_data('0\r\n')
            print("----------------------------------------------")
            print("------------------ 發文成功 ------------------")
            print("----------------------------------------------")
            return True
        except Exception as e:
            print(f"發文過程發生錯誤: {e}")
            return False


async def main() -> None:
    """主程式入口點"""
    # 設定連線參數
    host: str = 'ptt.cc'
    user: str = 'Your PTT ID'      # 請修改為您的 PTT 帳號
    password: str = 'Your PTT Password'  # 請修改為您的 PTT 密碼

    # 建立 PTT 連線物件
    ptt: Optional[Ptt] = None
    post_success: bool = False

    try:
        ptt = Ptt(host, user, password)
        await asyncio.sleep(1)

        # 嘗試連線
        if not await ptt.connect():
            print("連線失敗")
            return

        # 嘗試登入
        if not await ptt.login():
            print("登入失敗")
            return

        # 發文到 test 看板
        print("開始發文...")
        post_success = await ptt.post('test', '發文文字測試', '這是一篇測試,哇哈哈')
        if post_success:
            print("發文成功！")
            # 只有成功發文才正常登出
            await ptt.logout()
        else:
            print("發文失敗")

    except KeyboardInterrupt:
        print("\n使用者中斷程式")
        if ptt and ptt._connected:
            print("正在強制斷開連線...")
    except Exception as e:
        print(f"程式執行錯誤: {e}")
        if ptt and ptt._connected:
            print("發生錯誤，正在斷開連線...")
    finally:
        # 確保無論如何都會斷開連線
        if ptt:
            # 如果發文失敗，只斷開連線，不執行正常登出流程
            if not post_success and ptt._connected:
                await ptt.disconnect()
            # 如果發文成功，logout() 已經包含了 disconnect()
            # 如果還是連線狀態，表示 logout() 可能失敗了，需要強制斷開
            elif post_success and ptt._connected:
                print("登出可能失敗，強制斷開連線...")
                await ptt.disconnect()

def run_main() -> None:
    """運行主程式的同步包裝器"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程式被使用者中斷")


if __name__ == "__main__":
    run_main()
