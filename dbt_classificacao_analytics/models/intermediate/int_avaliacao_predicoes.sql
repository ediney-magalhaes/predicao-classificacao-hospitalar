select
    origem.atendimento,
    origem.safra_mes,
    origem.grupo_sus,
    origem.previsao_grupo,
    origem.complexidade_sus,
    origem.previsao_complexidade,
    case when origem.previsao_grupo is not null then true else false end as tem_predicao_modelo,
    case when origem.previsao_grupo is not null then (origem.grupo_sus = origem.previsao_grupo) else null end as acerto_grupo,
    case when origem.previsao_complexidade is not null then (origem.complexidade_sus = origem.previsao_complexidade) else null end as acerto_complexidade,
    versao.versao_modelo
from {{ ref('stg_bronze__saidas') }} as origem
left join {{ ref('int_correcoes_hitl') }} as versao
    on origem.safra_mes = versao.safra_mes