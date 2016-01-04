## Code generator
##
##
##
## This translate given logic into codes
## Translated codes can be accessed by name in a dictionary
##
##
import re
from copy import deepcopy
from string import Template
from sys import argv
from os import getcwd,chdir
from os.path import dirname,abspath

class WrongConfSyntax(Exception):
    pass
class WrongConfSymantic(Exception):
    pass

# Merge B into A
def merge_list(A,B):
    Anames = [a["colname"] for a in A["cols"]]
    for b in B["cols"]:
        if b["colname"] not in Anames:
            A["cols"].append(b)
    return A

# exclude B out of A
def exclude_list(A,B):
    Bnames = [b["colname"] for b in B["cols"]]
    for a in A["cols"]:
        if a["colname"] in Bnames:
            A["cols"].remove(a)
    return A

# input: list of {name:, type:, obj:}
# return name -> {name:, type:, obj:}
def tomap(A):
    ret={}
    for a in A:
        ret[a['name']]=a
    return ret

def var2flatmap(A,key='obj'):
    ret={}
    for a in A:
        ret[a['name']]=a[key]
    return ret

class Generator:
    def __init__(self,default_type="bigint"):
        self.imported_vars=[] 
            #[ {type:template|list,obj:,name:},...]
        self.templates=[]
            #[ {name:tmpl_name, content:tmpl_content, args:[arg1,arg2...] } ,...]
        self.lists=[] 
            #[ {name:list_name,
            #  cols: [{colname:,coltype:,tmpls:{tmpl:proce,...} ,...] 
        self.default_type=default_type
            # if $type is not given in col, this will be used for $type
        self.export_names=[] 
            # string, 

    def show(self):
        print "templates:"
        for t in self.templates:
            print t
        print "lists:"
        for l in self.lists:
            print l
    
    def is_imported(self,name):
        return name in [i['name'] for i in self.imported_vars]

    
    def is_existing_identifier(self,list_name_str):
        """
        Don't care about imported vars,
        if you create a varname same as imported var, get_var() will return
        the one created by you. 
        imported can be overwritten
        """
        return list_name_str in ([l["name"] for l in self.lists]+[t['name'] for t in self.templates])

    def get_var(self,name,mode="get"):
        """
        this returns {type:template|list,obj:,name:}
        you can get both created vars and imported vars here.
        get_var will lookup local vars first, 
        if `name` can't be found under local-scope, get_var will search for imported vars.
        """
        for t in self.templates:
            if t['name'] == name:
                if mode=='get':
                    return {'type':'template','obj':deepcopy(t),'name':name}
                elif mode=='remove':
                    self.templates.remove(t)
                    return
        for l in self.lists:
            if l['name'] == name:
                if mode=="get":
                    return {'type':'list','obj':deepcopy(l),'name':name}
                elif mode=='remove':
                    self.lists.remove(l)
                    return
        for i in self.imported_vars:
            if i['name'] == name:
                # imported vars' format is {name:,type:,obj:} already
                if mode=='remove':
                    # imported names does not interfere namespace
                    # do nothing when need removal
                    return
                return deepcopy(i)
        if mode == 'remove':
            # that's no problem if name wanted removed
            # is already not existing
            return
        print "var not found:",name
        raise WrongConfSymantic

    def remove_var(self,name):
        return self.get_var(name,mode='remove')

    def translate_list(self,list_obj,template_name):
        translated_items=[]# [str,str...]
        default_type=self.default_type
        for col in list_obj['cols']:
            if template_name not in col['tmpls']:
                # no specification for this template
                # skip by default
                continue

            this_name = col['colname']
            this_type = col['coltype']
            if this_type is None:
                this_type = default_type
            used_tmpl = col['tmpls'][template_name] # dictionay

            translated_items.append(Template(used_tmpl).substitute(this=this_name,type=this_type))
        return ',\n'.join(translated_items)

    def parse_param(self,tmpl_obj,param_str):
        """
        return {$name:value}
        """
        param_value_tmpl = "(\w+)\s*=\s*(((?P<quote>[\"\'])(.*?)(?P=quote))|(\w+))"
        list_or_tmpl_param_tmpl = "(\w+)"
        str_param_tmpl = "(?P<quote>[\"\'])(.*)(?P=quote)"
        pv_tmpl = re.compile(param_value_tmpl)
        obj_tmpl = re.compile(list_or_tmpl_param_tmpl)
        str_tmpl = re.compile(str_param_tmpl)
        caller_name = tmpl_obj['name']
        # {$name:$value}
        parsed_params = {}
        #get [ (param_name, value_str) , ]
        params = pv_tmpl.findall(param_str)
        for pv in params:
            res = obj_tmpl.match(pv[1])
            if res is not None:
                # that is an object, template or list
                obj_info = self.get_var(pv[1])
                if obj_info['type']=='template':
                    # put template body as value
                    # this will inherit vars in this template
                    tmpl_body = obj_info['obj']['content']
                    parsed_params[pv[0]]=tmpl_body
                    continue
                else: # list obj
                    parsed_params[pv[0]]=self.translate_list(obj_info['obj'],caller_name)
                    continue

            res = str_tmpl.match(pv[1])
            if res is not None:
                # just a string
                parsed_params[pv[0]]=res.groups()[1]
                continue
            # not string nor object
            print "unknown parameter for template",caller_name,":",pv
            raise WrongConfSyntax
        caller_params = tmpl_obj['args']
        provided_params = [key for key in parsed_params]
        missing_params = [p for p in caller_params if p not in provided_params]
        if len(missing_params)>0:
            print "call for",caller_name,"missing params:\n",missing_params
            raise WrongConfSymantic
        return parsed_params

    def match_new_template(self,text):
        new_tmpl = "(?:\s|\n)*new\s+template\s+(\w+)(?:\s|\n)*\'\'\'(.*?)\'\'\'(?:\s|\n)*"
        arg_tmpl = "\$(\w+)"
        result = re.match(new_tmpl,text,re.MULTILINE|re.DOTALL)
        if result is None:
            return None
        args = re.findall(arg_tmpl,result.groups()[1],re.MULTILINE)
        # remove old name var
        self.remove_var(result.groups()[0])
        self.templates.append( {"name":result.groups()[0],
            "content":result.groups()[1],
            "args":args} )
        return text[result.end():]

    def match_opr_template(self,text):
        new_tmpl = "(?:\s|\n)*new\s+template\s+(\w+)(?:\s|\n)*=(?:\s|\n)*(\w+)(?:\s|\n)*"
        result = re.match(new_tmpl,text,re.MULTILINE)
        if result is None:
            return None
        endpos = result.end()
        new_tmpl_name = result.groups()[0]
        copy_tmpl = self.get_var(result.groups()[1])['obj']
        copy_tmpl['name'] = new_tmpl_name
        # remove old name var
        self.remove_var(new_tmpl_name)
        self.templates.append(copy_tmpl)
        return text[endpos:]

    def match_call_template(self,text):
        # Doing::
        opr_tmpl = "(?:\s|\n)*new\s+template\s+(\w+)\s*=\s*(\w+)\s*\((.*?)\)(?:\s|\n)*"
        result = re.match(opr_tmpl,text,re.MULTILINE|re.DOTALL)
        if result is None:
            return None
        endpos = result.end()
        new_tmpl_name = result.groups()[0]
        called_tmpl_name = result.groups()[1]
        params_str = result.groups()[2]
        obj_info = self.get_var(called_tmpl_name)
        if obj_info['type'] != 'template':
            print "not template:",called_tmpl_name,"can't call"
            raise WrongConfSymantic
        params = self.parse_param(obj_info['obj'],params_str)
        resolved_content = Template(obj_info['obj']['content']).substitute(params)
        # this agency will deal with varname removing
        self.match_new_template("new template "+new_tmpl_name+"\n\'\'\'\n"+resolved_content+"\n\'\'\'")
        return text[endpos:]

    def match_new_list(self,text):
        new_tmpl = "(?:\s|\n)*new\s+list\s+(\w+)(?:\s|\n)*\'\'\'(.*?)\'\'\'(?:\s|\n)*"
        col_tmpl = "^\s*(\w+)(?:\s*:\s*(\w+))?\s*(.*?)\s*$"
        tmpl_spec_tmpl = "(\w+)\s*:\s*(?P<quote>[\"\'])(.+?)(?P=quote)"
        #parse list name and body
        result = re.match(new_tmpl,text,re.MULTILINE|re.DOTALL)
        if result is None:
            return None
        endpos = result.end()
        grp = result.groups()
        list_name = grp[0]
        col_detail = grp[1]
        cols=[]
        # parse col name and type
        for line in col_detail.split('\n'):
            colres = re.match(col_tmpl,line)
            if colres is None: 
                # treated like a comment
                continue
            col_grp=colres.groups()
            col_name=col_grp[0]
            col_type=col_grp[1]
            tmpl_spec_str=col_grp[2]
            # parse template specifications of this column
            tmpl_specs = re.findall(tmpl_spec_tmpl,tmpl_spec_str)
            tmpls = {}
            for tmpl_spec in tmpl_specs:
                # grp0 is tmpl name, grp1 is quote, grp2 is tmpl specification
                tmpls[tmpl_spec[0]]=tmpl_spec[2]
            cols.append({"colname":col_name,"coltype":col_type,"tmpls":tmpls})
        # remove old at end, this will allow redefine
        self.remove_var(list_name)
        self.lists.append({"name":list_name,"cols":cols})
        return text[endpos:]

    def match_opr_list(self,text):
        opr_tmpl = "(?:\s|\n)*new\s+list\s+(\w+)\s*=\s*((?:\s*\w+\s*)(?:\s*[\+\-]\s*\w+\s*)*)(?:\s|\n)*"
        result = re.match(opr_tmpl,text,re.MULTILINE|re.DOTALL)
        if result is None:
            return None
        list_name = result.groups()[0]
        endpos = result.end()
        # get operation-symbols and arithemetics
        opr_str = result.groups()[1]
        oprs = re.findall("[\+\-]",opr_str)
        var_names = [v.strip() for v in re.split("\+|\-",opr_str)]
        vars=[]
        # find var objects by varname
        # use obj's deepcopy to prevent from mischanging original objs 
        for varname in var_names:
            obj_info = self.get_var(varname)
            obj = obj_info['obj']
            vars.append(deepcopy(obj))

        # perform the +/- operations
        opr_result = vars[0]
        for var in vars[1:]:
            opr = oprs[0]
            oprs.remove(opr)
            if opr == '+':
                opr_result = merge_list(opr_result,var)
            elif opr == '-':
                opr_result = exclude_list(opr_result,var)
        opr_result["name"]=list_name
        # overwrite possible previous 
        self.remove_var(list_name)
        self.lists.append(opr_result)
        return text[endpos:]

    def match_export(self,text):
        exp_tmpl="(?:\s|\n)*export\s+(\w+)(?:\s|\n)*"
        result = re.match(exp_tmpl,text,re.MULTILINE)
        if result is None:
            return None
        endpos = result.end()
        exp_varname = result.groups()[0]
        # check if can export
        if (not self.is_existing_identifier(exp_varname)) and not self.is_imported(exp_varname):
            print "can't export unknown variable:",exp_varname
            raise WrongConfSymantic
        self.export_names.append(exp_varname)
        return text[endpos:]

    def match_import(self,text):
        imp_tmpl="(?:\s|\n)*from\s+(.+?)\s+import\s+(\w+(?:\s*,\s*\w+)*|\*)(?:\s|\n)*"
        result = re.match(imp_tmpl,text,re.MULTILINE|re.DOTALL)
        if result is None:
            return None
        endpos = result.end()
        conf_path = result.groups()[0]
        imports_str = result.groups()[1]
        father_all_exports = Generator().run(conf_path)
        if imports_str=='*':
            # import all from father
            # overwriting importing
            self.imported_vars=[e for e in father_all_exports]+self.imported_vars
        else:
            # just import some from father
            import_list = [i.strip() for i in imports_str.split(',')]
            # check if all wanted varnames are exported by father
            father_all_exported_names = [f['name'] for f in father_all_exports]
            for import_name in import_list:
                if import_name not in father_all_exported_names:
                    print "Error import:",import_name,"not found in",conf_path
                    raise WrongConfSymantic
            self.imported_vars=[iv for iv in father_all_exports if iv['name'] in import_list ]+self.imported_vars
        return text[endpos:]

    def shift_reduce(self,text):
        """
        return None means it has proceeded to the end, parse succeeded.
        raise exception WrongConfSyntax when can't match anythin
        """
        if len(text)==0:
            return None
        left_text = self.match_import(text)
        if left_text is not None:
            return left_text
        left_text = self.match_new_template(text)
        if left_text is not None:
            return left_text
        left_text = self.match_new_list(text)
        if left_text is not None:
            return left_text
        left_text = self.match_opr_list(text)
        if left_text is not None:
            return left_text
        left_text = self.match_call_template(text)
        if left_text is not None:
            return left_text
        # tmpl opr must be called after call tmpl
        left_text = self.match_opr_template(text)
        if left_text is not None:
            return left_text
        left_text = self.match_export(text)
        if left_text is not None:
            return left_text

        print "Syntax Error at:\n^",text
        raise WrongConfSyntax

    def read_conf(self,fname):
        """
==========================================
conf file should obey the following rules:
==========================================

# import syntax

    from ../tool.conf import *
    from tool.conf import baselist

# template is just a simple string-filling function
# dollar-values in a template means parameters

    new tmplate $TmpName
    '''
        $colname:$coltype  $grpname:'dowhat' $grp2:"dowhat"
        -- this is a comment
    '''

# list can be filled into template as a parameter
# when using as a parameter, list unfolds itself into a comma-separated string
# vars that can be refered: $this|$type
    
    new list $Listname
    '''
    $col_name:$type $tmpl_name:"max($this)" $tmpl_name2:"min($this)"
    '''
# list support + - operations
    new list $list2 = $list1 + $list3 - $list4
# call templates like a function
    new template tnew = grpby($a=$b,$c="static_str")
# export clause
    export $alias
        """
        # get text first, because we will go into its dir
        # so as to be able to resolve local depenency
        text = str(open(fname).read()).lower()

        # goto target dir
        cur_dir = getcwd()
        tar_dir = dirname(abspath(fname))
        chdir(tar_dir)

        # removing comments
        comment_removed = re.split("(?:--|##).*?(?=\n|$)",text,re.MULTILINE|re.DOTALL)
        clean_text = ' '.join(comment_removed)
        text_left = clean_text
        while (text_left is not None) and (len(text_left)>0):
            text_left = self.shift_reduce(text_left)
        # go back to original directory
        chdir(cur_dir)

    def export(self):
        """
        return a list of {type:template|list,obj:,name:}
        """
        # var names in self.export_names are already checked to be existed
        export_names = list(set(self.export_names))
        ret=[]
        for e in export_names:
            ret.append(self.get_var(e))
        return ret

    # this is the only legal entrance
    # of the class object
    def run(self,conf_path):
        self.read_conf(conf_path)
        return self.export()

def generate(conf_name):
    # return dictionary of:
    # name -> {type:template|list, obj:, name:}
    return tomap(Generator().run(conf_name))

def gen(conf_name):
    return var2flatmap(Generator().run(conf_name))

#k=generate('test.conf')
#for i in k:
#    print k[i]
#exit()

if __name__ == "__main__":
    args = argv[1:]
    if len(args) != 1:
        print "wrong args, only configration file path is required"
    else:
        for i in generate(args[0]):
            print i
    












#