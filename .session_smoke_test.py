from services.local_ai import is_control_query, parse_user_instruction_to_plan_local

print('is_control_query tests:')
for t in ['открой хром', 'что такое нейронная сеть', 'скриншот', 'расскажи про википедию']:
    print(t, '->', is_control_query(t))
print('\nparse tests:')
print(parse_user_instruction_to_plan_local('открой chrome'))
print(parse_user_instruction_to_plan_local('скриншот'))
print('done')
