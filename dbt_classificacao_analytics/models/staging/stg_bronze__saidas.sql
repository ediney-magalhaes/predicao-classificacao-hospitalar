with bronze as(
    select *,
            safe_cast(replace(dtsumario, ',', '.') as float64) as dtsumario_numerico
    from {{ source('bronze', 'bronze_saidas_anonimizado') }}
)
select
    coalesce(
    safe.parse_date('%d/%m/%Y', entrada_uti),
    safe.parse_date('%Y-%m-%d', entrada_uti)
    ) as entrada_uti,
    coalesce(
    safe.parse_date('%d/%m/%Y', dt_saida),
    safe.parse_date('%Y-%m-%d', dt_saida)
    ) as dt_saida,
    coalesce(
    safe.parse_datetime('%d/%m/%Y %H:%M', dt_atendimento),
    safe.parse_datetime('%Y-%m-%d %H:%M', dt_atendimento)
    ) as dt_atendimento,
    coalesce(
    safe.parse_datetime('%d/%m/%Y %H:%M:%S', previsao_alta),
    safe.parse_datetime('%Y-%m-%d %H:%M:%S', previsao_alta)
    ) as previsao_alta,
    coalesce(
    safe.parse_datetime('%d/%m/%Y %H:%M:%S', dtsumario),
    safe.parse_datetime('%Y-%m-%d %H:%M:%S', dtsumario),
    datetime_add(
        datetime_add(
            datetime(date '1899-12-30'),
            interval cast(dtsumario_numerico as int64) day
        ),
        interval cast((dtsumario_numerico - cast(dtsumario_numerico as int64)) * 86400 as int64) second
    )
    ) as dt_sumario,
    coalesce(
    safe.parse_datetime('%d/%m/%Y %H:%M:%S', concat(dt_alta," ",lpad(hr_alta, 8, '0'))),
    safe.parse_datetime('%Y-%m-%d %H:%M:%S', concat(dt_alta," ",lpad(hr_alta, 8, '0')))
    ) as dt_alta
from bronze