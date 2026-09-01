select
    safra_mes,
    count(*) as total_predicoes,
    countif(acerto_grupo) as acertos_grupo,
    countif(acerto_complexidade) as acertos_complexidade,
    count(*) - countif(acerto_grupo) as erros_grupo,
    count(*) - countif(acerto_complexidade) as erros_complexidade,
    versao_modelo
from {{ ref('int_avaliacao_predicoes') }}
where tem_predicao_modelo = true
group by 1, 7
