class token2mdataMapper:
    def __init__(self, node):
        self.m_node = node
        self.m_params=["gamma","gamut"]
        self.m_ignore=["path","baseName","frame","ext"]

    def nc2mdata(self,up):
        params={}
        gamut=None
        mdata=up.getMediaFileInfoData()
        nc=up.getNameConvention()
        items=nc.getItems()
        for item in items:
            if item.isPlaceHolder():
                name=item.name()
                if name in self.m_ignore:
                    self.m_node.info("token2mdataMapper:ignored","{} ignored".format(name))
                    continue
                value=up.getPlaceHolderValue(name)
                asParam=""
                if name in self.m_params:                
                    params[name]=value
                    asParam="(param)"
                self.m_node.info("token2mdataMapper:nc2mdata","adding token{} {}={}".format(asParam,name,value))
                mdata.setToken(name,value)
        # now parse special params
        if "gamut" in params and "gamma" in params:
            up.setParam("uniColor","uniColor:{}:{}".format(params["gamut"],params["gamma"]))
        up.setMediaFileInfoData(mdata)
        return up
  