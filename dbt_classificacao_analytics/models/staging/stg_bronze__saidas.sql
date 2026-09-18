with bronze as(
    select *,
            safe_cast(replace(dtsumario, ',', '.') as float64) as dtsumario_numerico,
            safe_cast(replace(previsao_alta, ',', '.') as float64) as previsao_alta_numerico
    from {{ source('bronze', 'bronze_saidas_anonimizado') }}
)
select
    atendimento,
    prontuario,
    idade,
    sexo,
    nr_dias,
    municipio,
    uf,
    registro_ans,
    convenio,
    coalesce(
    safe.parse_datetime('%d/%m/%Y %H:%M', dt_atendimento),
    safe.parse_datetime('%Y-%m-%d %H:%M', dt_atendimento)
    ) as dt_atendimento,
    origem_atendimento,
    tipo_internacao,
    ds_servico,
    coalesce(
    safe.parse_datetime('%d/%m/%Y %H:%M:%S', previsao_alta),
    safe.parse_datetime('%Y-%m-%d %H:%M:%S', previsao_alta),
    datetime_add(
        datetime_add(
            datetime(date '1899-12-30'),
            interval cast(previsao_alta_numerico as int64) day
        ),
        interval cast((previsao_alta_numerico - cast(previsao_alta_numerico as int64)) * 86400 as int64) second
    )
    ) as previsao_alta,
    coalesce(
    safe.parse_datetime('%d/%m/%Y %H:%M:%S', concat(dt_alta," ",lpad(hr_alta, 8, '0'))),
    safe.parse_datetime('%Y-%m-%d %H:%M:%S', concat(dt_alta," ",lpad(hr_alta, 8, '0')))
    ) as dt_alta,
    unidade_saida,
    motivo_alta,
    especialidade,
    cid_entrada,
    procedimento_entrada,
    cod_proc_1,
    desc_proc_1,
    coalesce(
        safe.parse_date('%d/%m/%Y', entrada_uti),
        date_add(date '1899-12-30', interval safe_cast(entrada_uti as int64) day)
    ) as entrada_uti,
    coalesce(
    safe.parse_date('%d/%m/%Y', dt_saida),
    safe.parse_date('%Y-%m-%d', dt_saida),
    date_add(date '1899-12-30', interval safe_cast(dt_saida as int64) day)
    ) as dt_saida,
    qtd_diarias_uti,
    qtd_uco,
    qtd_uco_retag,
    qtd_uti_geral,
    qtd_uti_cirurgica_2,
    qtd_uti_geral_3,
    qtd_uti_neo,
    qtd_uti_ped,
    qtd_uti_alerta,
    qtd_passagens_uti,
    cid_1_principal,
    ds_especialid_med_presc,
    ds_especialid_med_sumario,
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
    resp_alta,
    cirurgia,
    hash_nome_paciente,
    hash_nm_med_presc,
    hash_medico_sumario_alta,
    hash_medico_resp_atend,
    capitulo_breve,
    grupo_cid,
    grupo_sus,
    previsao_grupo,
    confianca_grupo,
    complexidade_sus,
    previsao_complexidade,
    confianca_complexidade,
    procedimento_1,
    safra_mes,
    cast(data_ingestao as timestamp) as data_ingestao
from bronze