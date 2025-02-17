import asyncio

from typing import Coroutine, Callable, Any, List
from amiyabot.network.httpServer import ServerEventHandler
from core import log
from core.util import Singleton

TASK_CORO = Callable[[], Coroutine[Any, Any, None]]
CUSTOM_CHECK = Callable[[int], Coroutine[Any, Any, bool]]


class TimedTask:
    def __init__(self, task: TASK_CORO, each: int = None, custom: CUSTOM_CHECK = None):
        self.task = task
        self.each = each
        self.custom = custom

    async def check(self, t) -> bool:
        if self.custom:
            return await self.custom(t)
        if self.each:
            return t >= self.each and t % self.each == 0
        return False


class TasksControl(metaclass=Singleton):
    def __init__(self):
        self.timed_tasks: List[TimedTask] = list()
        self.alive = True

        ServerEventHandler.on_shutdown.append(self.stop)

    def timed_task(self, each: int = None, custom: CUSTOM_CHECK = None):
        """
        注册定时任务
        非严格定时，因为执行协程会产生切换的耗时。所以此注册器定义的循环时间为"约等于"。

        :param each:   循环执行间隔时间，单位（秒）
        :param custom: 自定义循环规则
        :return:
        """

        def register(task: TASK_CORO):
            self.timed_tasks.append(TimedTask(task, each, custom))

        return register

    async def run_tasks(self, step: int = 1):
        try:
            t = 0
            while self.alive:
                await asyncio.sleep(step)

                if not self.timed_tasks:
                    continue

                t += step
                for task in self.timed_tasks:
                    if await task.check(t):
                        async with log.catch('TimedTask Error:'):
                            await task.task()

        except KeyboardInterrupt:
            pass

    def stop(self):
        self.alive = False
