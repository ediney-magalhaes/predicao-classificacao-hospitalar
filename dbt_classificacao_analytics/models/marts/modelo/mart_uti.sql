with movimentacoes_uti as (
    select *
    from {{ ref('int_movimentacoes_uti') }}

),

agregado_por_atendimento as (

    select
        atendimento,

        logical_or(eh_uti) as teve_uti,

        sum(case when eh_uti then minutos_na_unidade else 0 end) as minutos_totais_uti,
        round(sum(case when eh_uti then minutos_na_unidade else 0 end) / 60.0, 1) as horas_totais_uti,
        round(sum(case when eh_uti then minutos_na_unidade else 0 end) / 1440.0, 1) as dias_totais_uti,

        count(case when eh_uti then 1 end) as qtd_passagens_uti,

    from movimentacoes_uti
    group by atendimento

)

select * from agregado_por_atendimento