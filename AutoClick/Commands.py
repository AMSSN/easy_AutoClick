from lmTools import *

# TODO 这里是通过id和self.cmds进行索引，按照链表的概念应该存放上下一个的地址或者对象本身。
# TODO 如果一定要通过索引的方式，应该将当id置为自增，与self.cmds列表索引进行绑定。
'''
方案1需要在new的时候进行绑定,就不需要MyCommands.new_OP了，直接new一个OP后，进行链接，
     MyCommands就只需要有首OP，和一个控制运行的run函数就行了，甚至不需要一个单独的类，只要一个静态的run方法就行了
方案2复杂度略高，不知道还有没有其他风险。
     new的时候不需要传入id，设置为默认自增，这样在new的时候逻辑不友好
'''


class OP:
    def __init__(self, id):
        self.id = id
        self.last_id = None
        self.next_id = None
        # command adn operate.
        self.commands = None
        self.operate = None

    def run(self):
        print("self.id=", self.id)
        # print("self.last_id", self.last_id)
        # print("self.next_id", self.next_id)


class MyCommands:
    def __init__(self):
        self.cmds = []
        pass

    def new_OP(self, id, last_id, next_id, commands, operate):
        newop = OP(id)
        newop.last_id = last_id
        newop.next_id = next_id
        newop.commands = commands
        newop.operate = operate
        self.cmds.append(newop)

    def run(self):
        # 按照规则运行
        assert len(self.cmds) != 0, "cmds=0, Please check Commands.cmds!"
        current_command = self.cmds[0]
        while current_command.next_id is not None:
            current_command.run()
            current_command = self.cmds[current_command.next_id - 1]
