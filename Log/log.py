import logging
import os
import datetime
import enum

class SingletonType(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonType, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

# python 3 style
class Logger(object, metaclass=SingletonType):
    # __metaclass__ = SingletonType   # python 2 Style
    _logger = None

    def __init__(self, node_num=None):
        self._logger = logging.getLogger("crumbs")
        self._logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s \t [%(levelname)s | %(filename)s:%(lineno)s] > %(message)s')

        now = datetime.datetime.now()
        dirname = "./logfiles"

        if not os.path.isdir(dirname):
            os.mkdir(dirname)
        if node_num is None:
            fileHandler = logging.FileHandler(dirname + "/log_" + now.strftime("%Y-%m-%d_%H-%M-%S")+".log")
        else:
            fileHandler = logging.FileHandler(dirname + "/log_" + now.strftime("%Y-%m-%d_%H-%M-%S")+"_{}.log".format(node_num))

        # streamHandler = logging.StreamHandler()

        fileHandler.setFormatter(formatter)
        # streamHandler.setFormatter(formatter)

        self._logger.addHandler(fileHandler)
        # self._logger.addHandler(streamHandler)

    def get_logger(self):
        return self._logger

# a simple usecase
# if __name__ == "__main__":
#     logger = MyLogger.__call__().get_logger()
#     logger.info("Hello, Logger")
#     logger.debug("bug occured")