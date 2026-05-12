import os, sys
import json



def calculate_sum( numbers ):
    total=0
    for n in numbers :
        total = total+n
    return total


x=10
y =20
unused_variable = "I am never used"

def very_long_function_name_with_many_parameters(parameter_one, parameter_two, parameter_three, parameter_four):
    if parameter_one == None:
        return parameter_two+parameter_three+parameter_four
    return parameter_one


print(calculate_sum([1,2,3,4,5]))
