# This example creates simple Task with no inputs nor outputs
# On execution, it simple prints a "Hello World" message in console

def init(self):
    return True
    
def isReady(self):
    return True
    
def process(self):
    self.info("HelloWorld","Hello World")
    return True