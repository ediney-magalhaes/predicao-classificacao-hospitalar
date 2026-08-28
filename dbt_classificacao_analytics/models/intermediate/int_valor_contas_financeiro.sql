select
    nr_interno_conta,
    nr_atendimento,
    convenio,
    round(sum(valor), 2) as valor_faturado,
    round(sum(valor_recebido), 2) as valor_recebido,
    round(sum(valor_glosa), 2) as valor_glosa
from {{ ref('stg_financeiro__contas') }}
group by 1,2,3