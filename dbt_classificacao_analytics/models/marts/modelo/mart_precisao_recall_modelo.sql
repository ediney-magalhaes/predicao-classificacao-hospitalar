with unificado as(
    select
        safra_mes,
        previsao_grupo as previsto,
        grupo_sus as real,
        'grupo' as variavel
    from {{ ref('int_avaliacao_predicoes') }}
    where previsao_grupo is not null and grupo_sus is not null

    union all

    select
        safra_mes,
        previsao_complexidade as previsto,
        complexidade_sus as real,
        'complexidade' as variavel
    from {{ ref('int_avaliacao_predicoes') }}
    where previsao_complexidade is not null and complexidade_sus is not null
),

tp_por_classe as(
    select
        safra_mes,
        variavel,
        previsto as classe,
        count(*) as tp
    from unificado
    where previsto = real
    group by 1, 2, 3
),

fp_por_classe as(
    select
        safra_mes,
        variavel,
        previsto as classe,
        count(*) as fp
    from unificado
    where previsto != real
    group by 1, 2, 3
),

fn_por_classe as(
    select
        safra_mes,
        variavel,
        real as classe,
        count(*) as fn
    from unificado
    where previsto != real
    group by 1, 2, 3
),

todas_classes as(
    select distinct
        safra_mes,
        variavel,
        previsto as classe
    from unificado

    union distinct

    select distinct
        safra_mes,
        variavel,
        real as classe
    from unificado
),

contagens as(
    select
        todas_classes.safra_mes,
        todas_classes.variavel,
        todas_classes.classe,
        coalesce(tp_por_classe.tp, 0) as tp,
        coalesce(fp_por_classe.fp, 0) as fp,
        coalesce(fn_por_classe.fn, 0) as fn
    from todas_classes
    left join tp_por_classe
        on todas_classes.safra_mes = tp_por_classe.safra_mes
        and todas_classes.variavel = tp_por_classe.variavel
        and todas_classes.classe = tp_por_classe.classe
    left join fp_por_classe
        on todas_classes.safra_mes = fp_por_classe.safra_mes
        and todas_classes.variavel = fp_por_classe.variavel
        and todas_classes.classe = fp_por_classe.classe
    left join fn_por_classe
        on todas_classes.safra_mes = fn_por_classe.safra_mes
        and todas_classes.variavel = fn_por_classe.variavel
        and todas_classes.classe = fn_por_classe.classe
)

select
    safra_mes,
    variavel,
    classe,
    tp,
    fp,
    fn,
    safe_divide(tp, tp + fp) as precision,
    safe_divide(tp, tp + fn) as recall,
    safe_divide(2 * safe_divide(tp, tp + fp) * safe_divide(tp, tp + fn),
                safe_divide(tp, tp + fp) + safe_divide(tp, tp + fn)
                ) as f1_score
from contagens