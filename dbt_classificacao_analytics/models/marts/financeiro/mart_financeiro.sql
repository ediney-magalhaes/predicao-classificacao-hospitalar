with valor_por_atendimento as(
    select
        nr_atendimento,
        round(sum(valor_faturado), 2) as valor_faturado,
        round(sum(valor_recebido), 2) as valor_recebido,
        round(sum(valor_glosa), 2) as valor_glosa
    from {{ ref('int_valor_contas_financeiro') }}
    group by 1
),

financeiro_enriquecido as(
    select
        financeiro.nr_atendimento,
        financeiro.valor_faturado,
        financeiro.valor_recebido,
        financeiro.valor_glosa,
        saidas.complexidade_sus,
        saidas.grupo_sus,
        saidas.convenio,
        coalesce(convenio_fonte.fonte, 'Não Mapeado') as fonte_convenio
    from valor_por_atendimento as financeiro
    inner join {{ ref('stg_bronze__saidas') }} as saidas
        on financeiro.nr_atendimento = saidas.atendimento
    left join {{ ref('mapa_convenio_fonte') }} as convenio_fonte
        on saidas.registro_ans = convenio_fonte.registro_ans
)

select * from financeiro_enriquecido
