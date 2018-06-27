import importlib


def load_function(function_path):
    """
    dynamically load a function from a string
    """

    func_data = function_path.split(".")
    module_path = ".".join(func_data[:-1])
    func_str = func_data[-1]

    module = importlib.import_module(module_path)

    return getattr(module, func_str)
