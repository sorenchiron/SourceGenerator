==========================================
conf file should obey the following rules:
==========================================

## import syntax
`
    from ../tool.conf import *
    from tool.conf import baselist,extlist
`
## template is just a simple string-filling function
## dollar-values in a template means parameters
`
    new tmplate $TmpName
    '''
        $colname:$coltype  $grpname:'dowhat' $grp2:"dowhat"
    '''
        -- this is a comment
        ## also a comment
        
        -not comment,error
        #not comment,error
`
## list can be filled into template as a parameter
## when using as a parameter, list unfolds itself into a comma-separated string
# vars that can be refered: $this|$type
 `   
    new list $Listname
    '''
    $col_name:$type $tmpl_name:"max($this)" $tmpl_name2:"min($this)"
    '''
`
## list support + - operations
`
    new list $list2 = $list1 + $list3 - $list4
    new lsit renamed_list = original_list
`
## call templates like a function
`
    new template tnew = grpby($a=$b,$c="static_str")
`
## export clause
`
    export $alias
`