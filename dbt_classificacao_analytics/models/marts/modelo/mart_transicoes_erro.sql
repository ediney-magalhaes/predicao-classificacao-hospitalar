with transicoes_grupo as(
    select
        safra_mes,
        previsao_grupo,
        grupo_sus,
        count(*) as total_grupo
    from {{ ref('int_avaliacao_predicoes') }}
    where acerto_grupo = false
    group by 1, 2, 3
),

transicoes_complexidade as(
    select
        safra_mes,
        previsao_complexidade,
        complexidade_sus,
        count(*) as total_complexidade
    from {{ ref('int_avaliacao_predicoes') }}
    where acerto_complexidade = false
    group by 1, 2, 3
),

unificado as(
    select
        safra_mes,
        previsao_grupo as previsto,
        grupo_sus as real,
        total_grupo as total,
        'grupo' as variavel
    from transicoes_grupo

    union all

    select
        safra_mes,
        previsao_complexidade as previsto,
        complexidade_sus as real,
        total_complexidade as total,
        'complexidade' as variavel
    from transicoes_complexidade
),

ranqueado as(
    select
        *,
        row_number() over(partition by safra_mes, variavel order by total desc) as posicao
    from unificado
)

select *
from ranqueado
where posicao <= 5