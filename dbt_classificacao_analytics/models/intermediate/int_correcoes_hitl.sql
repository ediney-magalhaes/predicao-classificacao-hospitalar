with ranked as (
    select *,
            row_number() over(
                partition by safra_mes
                order by data_revisao desc
            ) as rn
    from {{ ref('stg_audit__hitl_events') }}
)
select
    safra_mes,
    data_revisao,
    revisor,
    total_registros,
    correcoes_grupo,
    correcoes_complexidade,
    correcoes_ambos,
    taxa_correcao_grupo,
    taxa_correcao_complexidade,
    tempo_revisao_min,
    versao_modelo
from ranked
where rn = 1