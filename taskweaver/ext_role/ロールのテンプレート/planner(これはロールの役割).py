★テンプレートなので余計なものは削除した


from taskweaver.ext_role.web_explorer.driver import SeleniumDriver
from taskweaver.memory.attachment import AttachmentType
from taskweaver.module.event_emitter import PostEventProxy


★これがロールの役割になっている。ただ、厳密なロールではないので引数は自由に設計して良い
class VisionPlanner:
    def __init__(self, api_key: str, endpoint: str, driver: SeleniumDriver, prompt: str = None):
        self.gpt4v_key = api_key
        self.gpt4v_endpoint = endpoint

        self.headers = {
            "Content-Type": "application/json",
            "api-key": api_key,
        }
        self.driver = driver
        self.previous_actions = []
        self.step = 0
        self.prompt = prompt


    def get_actions():
        pass


    def get_objective_done(
        self,
        objective: str,
        post_proxy: PostEventProxy,　　　　★呼び出し元のロールから post_proxy を受け取ることができる。つまり、ロールからロールを呼び出すことができる。
        save_screenshot: bool = True,
    ):

        while True:
            post_proxy.update_attachment(　　　　　　　　　　　　　　　★アタッチメント(添付ファイル)の更新。ここで更新することで、呼び出し元のアタッチメントが更新されているか？？
                message=json.dumps(plan, indent=2),
                type=AttachmentType.web_exploring_plan,
            )

            if is_stop:
                post_proxy.update_message(　　　　　　　　　　　　　　★メッセージの更新。ここでフロントエンドのメッセージが更新されているはず
                    f"The previous task is stopped.\n"
                    f"The actions taken are:\n{self.previous_actions}.\n"
                    f"The current link is: {self.driver.driver.current_url}.\n"
                    f"The message is: {stop_message}",
                )
                break

            if inner_step > 10:
                post_proxy.update_message(　　　　　　　　　　　　　　★メッセージの更新。ここでフロントエンドのメッセージが更新されているはず
                    f"The actions taken are:\n{self.previous_actions}.\n"
                    "Failed to achieve the objective. Too many steps. "
                    "Could you please split the objective into smaller subtasks?",
                )

        self.step += inner_step
