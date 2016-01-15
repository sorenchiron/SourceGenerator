##                  Copyright [2015-2016] [Soren Chen]
## 
##    Licensed under the Apache License, Version 2.0 (the "License");
##    you may not use this file except in compliance with the License.
##    You may obtain a copy of the License at
## 
##        http://www.apache.org/licenses/LICENSE-2.0
## 
##    Unless required by applicable law or agreed to in writing, software
##    distributed under the License is distributed on an "AS IS" BASIS,
##    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##    See the License for the specific language governing permissions and
##    limitations under the License.
##
## Code generator
## Content/Context: All Resources/Files Under This Project
## All Published Under Apache 2.0 Licence
## Author: Soren Chen
## Copyright: 2015-2016
## This translate given logic into codes
## Translated codes can be accessed by name in a dictionary
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

#############################################
# private tools
#############################################

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

def var2simplemap(A):
    ret={}
    for a in A:
        if a['type']=="template":
            ret[a['name']]=a['obj']['content']
        elif a['type']=='list':
            ret[a['name']]=a['obj']['cols']
    return ret

#############################################
# Generator Global Settings
#############################################
_EMBEDED_CONF_PREFIX="#@"
    # you can embed conf inside python files now


#############################################
# Main class
#############################################
class Generator:
    """
    SourceGenerator is designed for necessary redundancy management
    When you have to repeat the same list of content in many place
    , with tiny different format decorations, this programme could be of much help.

    You can declare format `plans`(or `templates`) for lists, and create new list using +/- oprs.
    With this, you can create content dependencies.
    When you need to add/delete/modify some columns, you can just modify ONE place, and the other files will
    update temselfs simultaneously and immediately.
    """
    def __init__(self,default_type="bigint",embeded_conf=False):
        self.imported_vars=[] 
            #[ {type:template|list,obj:,name:},...]
        self.templates = []
            #[ {name:tmpl_name, content:tmpl_content, args:[arg1,arg2...] } ,...]
        self.lists = [] 
            #[ {name:list_name,
            #  cols: [{colname:,coltype:,tmpls:{tmpl:proce,...} ,...] 
        self.default_type = default_type
            # if $type is not given in col, this will be used for $type
        self.export_names = [] 
            # string, 
        self.embeded_conf = embeded_conf
            # unless ext is .conf, all files are treated as embeded conf 
        self.var_trace = {}
            # name->{  father_file -> [father_vars,]  }
            # if `name` is created locally, set to argv[0], which is self filename.
            # and set father_vars to [empty]

        self.result=None
            # result is generated in export(),and return to caller
        self.fname=None
            # only to save the fname recorded by read_conf()

    def show(self):
        from pprint import pprint
        print "templates:"
        for t in self.templates:
            pprint(t)
        print "lists:"
        for l in self.lists:
            pprint(l)
    
    def is_conf_file(self,filename):
        confname_tmpl=".+\.conf"
        return re.match(confname_tmpl,filename,re.I) is not None

    def is_imported(self,name):
        return name in [i['name'] for i in self.imported_vars]

    def record_var_trace(self,var_name,father_filename,*father_vars):
        if (father_filename is None) or (father_filename == "this"):
            # use self conf-filename
            father_filename=self.fname
        father_filename=abspath(father_filename)
        # ensure var_name in trace map
        if var_name not in self.var_trace:
            self.var_trace[var_name]={}
        # ensure father_filename in trace map for var_name
        if father_filename not in self.var_trace[var_name]:
            self.var_trace[var_name][father_filename]=[]
        # ensure father_vars are put under father_filename
        for father_var in father_vars:
            if father_var not in self.var_trace[var_name][father_filename]:
                self.var_trace[var_name][father_filename].append(father_var)

    def deep_resolve_trace(self):
        updated=True
        self_filename=abspath(self.fname)

        def is_final_var(var_name):
            # tell if a var is generic var.
            #  Don't see this ->   if all of its local deps are final or are itself, then this var is final.  
            father_files=self.var_trace[var_name]
            # only inspect non-imported vars, because imported vars are all final.
            for father_filename in [f for f in father_files if f==self_filename]:
                if len(father_files[father_filename]) != 0:
                    return False
            return True
        def collect_leaves(var_name):
            deps=self.var_trace[var_name]
            ## TODO: flatten the tree and get only the leaf nodes
            while updated:
                update=False
                for name in self.var_trace:
                    traces=self.var_trace[name]
                    for father_filename in traces:
                        dep_var_names = [ n for n in traces[father_filename] if n!=name or father_filename!=self_filename ] # prevent self-reference


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
                # record consanguinity
                self.record_var_trace(caller_name,"this",pv[1])
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

    def match_new_template(self,text,trace=True):
        """
        when called by match_call_template(), trace is explicitly set False.
        Because match_call_template() will have already recorded the consanguinity in parse_param().
        """
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
        if trace: 
            # record local var consanguinity, empty father_vars
            self.record_var_trace(result.groups()[0],"this")
        return text[result.end():]

    def match_opr_template(self,text):
        """rename of template"""
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
        # record consanguinity
        self.record_var_trace(new_tmpl_name,"this",result.groups()[1])

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
        # consanguinity is recorded inside parse_param()
        params = self.parse_param(obj_info['obj'],params_str)
        resolved_content = Template(obj_info['obj']['content']).substitute(params)
        # this agency will deal with varname removing
        self.match_new_template("new template "+new_tmpl_name+"\n\'\'\'\n"+resolved_content+"\n\'\'\'",False)
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
        # record consanguinity
        self.record_var_trace(list_name,"this")
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
                # only record consanguinity for + operator
                # because consanguinity doesn't come from `-` opr
                self.record_var_trace(list_name,"this",var['name']) 
            elif opr == '-':
                opr_result = exclude_list(opr_result,var)
        opr_result["name"]=list_name
        # overwrite possible previous 
        self.remove_var(list_name)
        self.lists.append(opr_result)
        return text[endpos:]

    def match_export(self,text):
        exp_tmpl="(?:\s|\n)*export(?:\s|\n)+(\w+(?:(?:\s|\n)*,(?:\s|\n)*\w+)*)(?:\s|\n)*"
        result = re.match(exp_tmpl,text,re.MULTILINE)
        if result is None:
            return None
        endpos = result.end()
        exp_varnames_str = result.groups()[0]
        for exp_varname in [e.strip() for e in exp_varnames_str.split(',')]:
            # check if can export
            if (not self.is_existing_identifier(exp_varname)) and not self.is_imported(exp_varname):
                print "can't export unknown variable:",exp_varname
                raise WrongConfSymantic
            self.export_names.append(exp_varname)
        # exports don't record consanginity, because they declare no variables
        return text[endpos:]

    def match_import(self,text):
        imp_tmpl="(?:\s|\n)*from\s+(.+?)\s+import\s+(\w+(?:\s*,\s*\w+)*|\*)(?:\s|\n)*"
        result = re.match(imp_tmpl,text,re.MULTILINE|re.DOTALL)
        if result is None:
            return None
        endpos = result.end()
        conf_path = result.groups()[0]
        imports_str = result.groups()[1]
        embeded_conf=False
        if not self.is_conf_file(conf_path):
            # not a .conf file, which we assume:
            # conf is embeded
            embeded_conf=True
        father = Generator(embeded_conf=embeded_conf)
        father_all_exports = father.run(conf_path)
        if imports_str=='*':
            # import all from father
            # overwriting importing
            self.imported_vars=[e for e in father_all_exports]+self.imported_vars
            # gather names of imported vars
            import_list=[e['name'] for e in father_all_exports]
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
        # record consanguinity
        # since vars from fathers are already resolved by fathers' Generator.
        # we just use fathers' trace.
        for i in import_list:
            self.var_trace[i]=father.var_trace[i]

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

    # return long text string
    def resolve_embeded_conf(self,fname):
        embed_pattern="^\s*"+_EMBEDED_CONF_PREFIX+"\s*(.*)"
        ep=re.compile(embed_pattern)
        resolved_lines=[]
        for line in open(fname,'r'):
            line = str(line).lower()
            res = ep.match(line)
            if res is None:
                continue
            resolved_lines.append(res.groups()[0])
        return "\n".join(resolved_lines)
    
    def read_conf(self,fname=None,conf_str=None):
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
        if conf_str is not None:
            text=conf_str.lower()
            # directly given confstr,means resolved embeded mode.
            # use self filename
            fname=argv[0]
        else:
            # use fname to find configurations
            if fname is None:
                # apply in_src_conf mode
                self.embeded_conf=True
                # resolving from py-src file
                fname=argv[0]
            if not self.is_conf_file(fname):
                # assume it an embeded conf src
                self.embeded_conf=True
            # get text first, because we will go into its dir later
            # so as to be able to resolve local depenency
            if self.embeded_conf:
                text = self.resolve_embeded_conf(fname)
            else:
                text = str(open(fname).read()).lower()

        self.fname=fname
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
        return a list of {name:, type:template|list,obj:}
        """
        # var names in self.export_names are already checked to be existed
        export_names = list(set(self.export_names))
        ret=[]
        for e in export_names:
            ret.append(self.get_var(e))
        self.result=ret
        return ret

    # this is the only legal entrance
    # of the class object
    def run(self,conf_path=None,conf_str=None):
        self.read_conf(conf_path,conf_str)
        return self.export()
#### END OF CLASS Generator


#############################################
# Entrance Interfaces
# Shorter the function name is,
#      , more concise the format is.
#############################################

def generate(conf_name=None):
    """returns dictionary of: name -> {type:template|list, obj:, name:}"""
    return tomap(Generator().run(conf_name))

def gen(conf_name=None):
    """
    returns: name -> obj     
    obj is {name:,cols:} or {name:,content:,args:}
    """
    return var2flatmap(Generator().run(conf_name))

def G(conf_name=None):
    """returns: name -> str_content|[{colname,coltype,tmpls:{tmpl:proce}]"""
    return var2simplemap(Generator().run(conf_name))
####################END######################


#############################################
# Public Tools
#############################################

def findall_root_select(text):
    """
    Used to analyze the source files before adapting it into SourceGenerator template
    Using this function, you can see clearly the 'source-getting' behaviors
    and know what columns it imports and where it imports from  
    """
    # ((?!select).)     
    # means any character that is not preceded by `select`
    tmpl="select(?:\s|\n)((?:(?!select).)+?)from(?:\s|\n)+((?:\w+\s*::\s*)?\w+)"
    sel=re.compile(tmpl,re.DOTALL)
    res=sel.findall(text)
    stripped_res=[]
    # clean formats
    for r in res:
        body=  '\n'.join([l.strip() for l in r[0].split('\n')])
        source= r[1].strip()
        stripped_res.append( (body,source) )       
    return sorted(stripped_res,key=lambda x:len(x[1]),reverse=True)

def indent(lines, amount, ch=' '):
    padding = amount * ch
    return padding + ('\n'+padding).join(lines.split('\n'))



#############################################
#
#############################################
version=" 1.1 Beta "

require_argument = True
no_argument = False
no_doc = None
no_abbr = None
arg_is_set = True
arg_not_set = False
arg_val = None
arg_type_fullname = 1
arg_type_abbr = 2
arg_type_value = -1

first_level_args=[]
max_first_level_args_num=1

def __tell_arg_type__(arg):
    m = re.match("^\-\-(\w+)", arg)
    if m is not None:
        return (arg_type_fullname, m.groups()[0])
    m = re.match("^\-(\w+)", arg)
    if m is not None:
        return (arg_type_abbr, m.groups()[0])
    return (arg_type_value, arg)


def __locate_arg_no__(flag_type, flag, arg_map, arg_index):
    query_name = ""
    if flag_type == arg_type_fullname:
        query_name = "full name"
    elif flag_type == arg_type_abbr:
        query_name = "abbreviation"
    i = 0
    for arg_info in arg_map:
        if arg_info[arg_index[query_name]] == flag:
            return i
        i += 1
    return 0

def __format_help_doc__(arg_item, arg_index):
    if arg_item[arg_index["doc"]] is not no_doc:
            abbr = arg_item[arg_index["abbreviation"]]
            arg = arg_item[arg_index["has argument"]]

            if abbr is no_abbr:
                abbr = "  "
            else:
                abbr = '-'+abbr

            if arg is no_argument:
                arg = ""
            else:
                arg = "one arg,"

            doc = "--%s %s\t:%s %s" % (arg_item[arg_index["full name"]],abbr,arg,arg_item[arg_index["doc"]])
            return doc
    return no_doc

def __help_bad_arg__(bad_arg, arg_map, arg_index):
    help_result = []
    for arg_item in arg_map:
        if (bad_arg in arg_item[arg_index["full name"]] or
        (arg_item[arg_index["abbreviation"]] is not no_abbr and
            bad_arg in arg_item[arg_index["abbreviation"]] ) or
        ( arg_item[arg_index["doc"]] is not no_doc and
            bad_arg in arg_item[arg_index["doc"]] )
        ):
            help_result.append(__format_help_doc__(arg_item, arg_index))
    return help_result

def __none__(sa, *args):
    print("not implemented")

def __bad_arg__(sa, arg_map, arg_index, value):
    print("bad arguments:", value)
    print("please use help to see the usage")
    exit(0)

def __help__(sa, arg_map, arg_index):
    print(sa.__class__.__doc__)
    for info in arg_map:
        doc = __format_help_doc__(info, arg_index)
        if doc is not no_doc:
            print(doc)
    exit(0)

def __arg_e__(sa, arg_map, arg_index, value):
    res=findall_root_select(open(value,'r').read())
    print "====explaining source file===="
    for r in res:
        print "- - - - - - - - - -"
        print "Table",r[1]
        print indent(r[0],4)
    exit(0)

def __run__(sa, arg_map, arg_index):
    if len(first_level_args) != 1:
        print "wrong args, only configration file path is required"
        exit(0) 
    sa.run(first_level_args[0])

def __arg_show__(sa, arg_map, arg_index):
    sa.show()



__arg_map__ = [
    ["version",no_abbr,__none__,no_argument,arg_not_set,arg_val,"SourceGenerator, version "+version+" by sorenchen. copyright 2016-2017"],
    ["bad arg", no_abbr, __bad_arg__, no_argument, arg_not_set, arg_val,no_doc],
    ["help", 'h', __none__, no_argument, arg_not_set, arg_val,"yeild embeded configuration mode"],
    ["explain", 'e', __arg_e__, require_argument, arg_not_set, arg_val,"yeild embeded configuration mode"],
    ["conf", 'c', __none__, no_argument, arg_not_set, arg_val,"yeild configuration file mode"],
    ## run stage
    ["run", no_abbr, __run__, no_argument, arg_is_set, arg_val,no_doc],  # This is the RUN[] stage
    ## run over
    ["show", no_abbr, __arg_show__, no_argument, arg_is_set, arg_val,no_doc] 
]

__arg_index__ = {"full name": 0, "abbreviation": 1, "function": 2, "has argument": 3, "argument set": 4,
                 "argument value": 5,"doc":6}


def __resolve_arguments__(args, arg_map, arg_index):
    total = len(args)
    dealing = 0
    while dealing <= total - 1:
        (arg_type, value) = __tell_arg_type__(args[dealing])
        if arg_type < 0:
            if len(first_level_args)<max_first_level_args_num:
                # can accept first level args
                first_level_args.append(value)
                dealing+=1
                continue
            # can't tolerate more first level args, error
            print ("sqla: bad argument input at:",value)
            help_result = __help_bad_arg__(value,arg_map,arg_index)
            if len(help_result)>0:
                print ("sqla assuming you want these:")
                for h in help_result:
                    print (h)
            exit()
        no = __locate_arg_no__(arg_type, value, arg_map, arg_index)
        if arg_map[no][arg_index["has argument"]]:
            if dealing + 1 >= total or __tell_arg_type__(args[dealing + 1])[
                0] > 0:  # if no further args given OR  type is flag or abbr flag
                print("sqla: flag", value, "requires one argument, none given")
                exit(0)
            dealing += 1
            arg_map[no][arg_index["argument value"]] = args[dealing]
        arg_map[no][arg_index["argument set"]] = True
        dealing += 1


def __exec__(sa, arg_map, arg_index):
    for arg in arg_map:
        if arg[arg_index["argument set"]]:
            if arg[arg_index["has argument"]]:
                arg[arg_index["function"]](sa, arg_map, arg_index, arg[arg_index["argument value"]])
            else:
                arg[arg_index["function"]](sa, arg_map, arg_index)


if __name__ == "__main__":
    if len(argv) > 1:
        args = argv[1:]
        __resolve_arguments__(args, __arg_map__, __arg_index__)
    g=Generator()
    __exec__(g, __arg_map__, __arg_index__)


    












#