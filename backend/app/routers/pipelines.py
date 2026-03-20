# Register in main.py:
#   from .routers import pipelines
#   app.include_router(pipelines.router, prefix="/api/v1", tags=["pipelines"])

"""Multi-step pipeline API router."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.session import Session
from ..schemas.pipeline import (
    PipelineCreate,
    PipelineListItem,
    PipelineRead,
    PipelineStep,
    PipelineTemplate,
)
from ..services import pipeline_service

router = APIRouter()


# --- Pipeline templates (hardcoded) ---

PIPELINE_TEMPLATES: list[PipelineTemplate] = [
    PipelineTemplate(
        name="scRNA-seq Analysis",
        description="Single-cell RNA-seq analysis pipeline: load, QC, normalize, cluster.",
        steps=[
            PipelineStep(
                name="Load Data",
                job_type="python",
                code=(
                    "import scanpy as sc\n"
                    "adata = sc.read_h5ad('data.h5ad')\n"
                    "print(f'Loaded {adata.shape[0]} cells, {adata.shape[1]} genes')"
                ),
            ),
            PipelineStep(
                name="Quality Control",
                job_type="python",
                code=(
                    "import scanpy as sc\n"
                    "adata = sc.read_h5ad('data.h5ad')\n"
                    "sc.pp.filter_cells(adata, min_genes=200)\n"
                    "sc.pp.filter_genes(adata, min_cells=3)\n"
                    "adata.var['mt'] = adata.var_names.str.startswith('MT-')\n"
                    "sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], inplace=True)\n"
                    "adata = adata[adata.obs.pct_counts_mt < 20, :].copy()\n"
                    "adata.write('data_qc.h5ad')\n"
                    "print(f'After QC: {adata.shape[0]} cells, {adata.shape[1]} genes')"
                ),
                depends_on=[0],
            ),
            PipelineStep(
                name="Normalize",
                job_type="python",
                code=(
                    "import scanpy as sc\n"
                    "adata = sc.read_h5ad('data_qc.h5ad')\n"
                    "sc.pp.normalize_total(adata, target_sum=1e4)\n"
                    "sc.pp.log1p(adata)\n"
                    "sc.pp.highly_variable_genes(adata, min_mean=0.0125, max_mean=3, min_disp=0.5)\n"
                    "adata.write('data_norm.h5ad')\n"
                    "print(f'Normalized. HVGs: {adata.var.highly_variable.sum()}')"
                ),
                depends_on=[1],
            ),
            PipelineStep(
                name="Cluster",
                job_type="python",
                code=(
                    "import scanpy as sc\n"
                    "adata = sc.read_h5ad('data_norm.h5ad')\n"
                    "sc.pp.pca(adata, n_comps=50)\n"
                    "sc.pp.neighbors(adata, n_neighbors=10, n_pcs=40)\n"
                    "sc.tl.leiden(adata)\n"
                    "sc.tl.umap(adata)\n"
                    "adata.write('data_clustered.h5ad')\n"
                    "print(f'Found {adata.obs.leiden.nunique()} clusters')"
                ),
                depends_on=[2],
            ),
        ],
    ),
    PipelineTemplate(
        name="Variant Analysis",
        description="Variant calling pipeline: index reference, call variants, annotate.",
        steps=[
            PipelineStep(
                name="Index Reference",
                job_type="bash",
                code=(
                    "#!/bin/bash\n"
                    "set -euo pipefail\n"
                    "if [ -f reference.fa ]; then\n"
                    "  samtools faidx reference.fa\n"
                    "  echo 'Reference indexed successfully'\n"
                    "else\n"
                    "  echo 'reference.fa not found — upload it first'\n"
                    "  exit 1\n"
                    "fi"
                ),
            ),
            PipelineStep(
                name="Call Variants",
                job_type="bash",
                code=(
                    "#!/bin/bash\n"
                    "set -euo pipefail\n"
                    "if [ -f aligned.bam ]; then\n"
                    "  bcftools mpileup -f reference.fa aligned.bam | bcftools call -mv -Oz -o variants.vcf.gz\n"
                    "  bcftools index variants.vcf.gz\n"
                    "  echo \"Variants called: $(bcftools view -H variants.vcf.gz | wc -l)\"\n"
                    "else\n"
                    "  echo 'aligned.bam not found — upload it first'\n"
                    "  exit 1\n"
                    "fi"
                ),
                depends_on=[0],
            ),
            PipelineStep(
                name="Annotate",
                job_type="python",
                code=(
                    "import subprocess\n"
                    "result = subprocess.run(\n"
                    "    ['bcftools', 'stats', 'variants.vcf.gz'],\n"
                    "    capture_output=True, text=True\n"
                    ")\n"
                    "for line in result.stdout.splitlines():\n"
                    "    if line.startswith('SN'):\n"
                    "        print(line)"
                ),
                depends_on=[1],
            ),
        ],
    ),
    PipelineTemplate(
        name="Drug Interaction Check",
        description="Check drug-drug interactions: load database, check specific pair.",
        steps=[
            PipelineStep(
                name="Load Drug DB",
                job_type="python",
                code=(
                    "import json, os\n"
                    "# Sample drug interaction database\n"
                    "drug_db = {\n"
                    "    'warfarin': ['aspirin', 'ibuprofen', 'naproxen'],\n"
                    "    'metformin': ['alcohol', 'contrast_dye'],\n"
                    "    'simvastatin': ['grapefruit', 'erythromycin', 'cyclosporine'],\n"
                    "    'lisinopril': ['potassium', 'spironolactone'],\n"
                    "}\n"
                    "with open('drug_db.json', 'w') as f:\n"
                    "    json.dump(drug_db, f, indent=2)\n"
                    "print(f'Loaded {len(drug_db)} drugs with interaction data')"
                ),
            ),
            PipelineStep(
                name="Check Interactions",
                job_type="python",
                code=(
                    "import json\n"
                    "with open('drug_db.json') as f:\n"
                    "    drug_db = json.load(f)\n"
                    "\n"
                    "drug_a, drug_b = 'warfarin', 'aspirin'\n"
                    "interactions_a = drug_db.get(drug_a, [])\n"
                    "interactions_b = drug_db.get(drug_b, [])\n"
                    "\n"
                    "if drug_b in interactions_a or drug_a in interactions_b:\n"
                    "    print(f'WARNING: {drug_a} and {drug_b} have a known interaction!')\n"
                    "else:\n"
                    "    print(f'No known interaction between {drug_a} and {drug_b}')"
                ),
                depends_on=[0],
            ),
        ],
    ),
]


# --- Endpoints ---


@router.get("/pipelines/templates", response_model=list[PipelineTemplate])
async def get_pipeline_templates():
    """Return predefined pipeline templates."""
    return PIPELINE_TEMPLATES


@router.post("/pipelines", response_model=PipelineRead)
async def create_pipeline(body: PipelineCreate, db: AsyncSession = Depends(get_db)):
    """Create and start a multi-step pipeline."""
    # Validate session exists
    result = await db.execute(select(Session).where(Session.id == uuid.UUID(body.session_id)))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not body.steps:
        raise HTTPException(status_code=400, detail="Pipeline must have at least one step")

    # Validate depends_on indices
    for i, step in enumerate(body.steps):
        for dep in step.depends_on:
            if dep < 0 or dep >= len(body.steps) or dep >= i:
                raise HTTPException(
                    status_code=400,
                    detail=f"Step {i} has invalid dependency index {dep}",
                )

    pipeline = await pipeline_service.create_pipeline(
        db,
        session_id=uuid.UUID(body.session_id),
        name=body.name,
        description=body.description,
        steps=body.steps,
    )

    # Enrich for response
    pipeline = await pipeline_service.get_pipeline(db, pipeline.id)
    step_results = pipeline_service.get_step_results(pipeline)

    return PipelineRead(
        id=str(pipeline.id),
        name=pipeline.name,
        description=pipeline.description,
        state=pipeline.state,
        steps=step_results,
        current_step=pipeline.current_step,
        total_steps=pipeline.total_steps,
        created_at=pipeline.created_at.isoformat(),
        started_at=pipeline.started_at.isoformat() if pipeline.started_at else None,
        completed_at=pipeline.completed_at.isoformat() if pipeline.completed_at else None,
    )


@router.get("/pipelines", response_model=list[PipelineListItem])
async def list_pipelines(
    session_id: str | None = Query(default=None, description="Filter by session"),
    db: AsyncSession = Depends(get_db),
):
    """List pipelines, optionally filtered by session."""
    sid = uuid.UUID(session_id) if session_id else None
    pipelines = await pipeline_service.list_pipelines(db, session_id=sid)
    return [
        PipelineListItem(
            id=str(p.id),
            name=p.name,
            state=p.state,
            current_step=p.current_step,
            total_steps=p.total_steps,
            created_at=p.created_at.isoformat(),
        )
        for p in pipelines
    ]


@router.get("/pipelines/{pipeline_id}", response_model=PipelineRead)
async def get_pipeline(pipeline_id: str, db: AsyncSession = Depends(get_db)):
    """Get pipeline with step details and job results."""
    pipeline = await pipeline_service.get_pipeline(db, uuid.UUID(pipeline_id))
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    step_results = pipeline_service.get_step_results(pipeline)
    return PipelineRead(
        id=str(pipeline.id),
        name=pipeline.name,
        description=pipeline.description,
        state=pipeline.state,
        steps=step_results,
        current_step=pipeline.current_step,
        total_steps=pipeline.total_steps,
        created_at=pipeline.created_at.isoformat(),
        started_at=pipeline.started_at.isoformat() if pipeline.started_at else None,
        completed_at=pipeline.completed_at.isoformat() if pipeline.completed_at else None,
    )


@router.post("/pipelines/{pipeline_id}/cancel", response_model=PipelineRead)
async def cancel_pipeline(pipeline_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel a pipeline and all its pending/running jobs."""
    pipeline = await pipeline_service.cancel_pipeline(db, uuid.UUID(pipeline_id))
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # Re-fetch enriched data
    pipeline = await pipeline_service.get_pipeline(db, pipeline.id)
    step_results = pipeline_service.get_step_results(pipeline)
    return PipelineRead(
        id=str(pipeline.id),
        name=pipeline.name,
        description=pipeline.description,
        state=pipeline.state,
        steps=step_results,
        current_step=pipeline.current_step,
        total_steps=pipeline.total_steps,
        created_at=pipeline.created_at.isoformat(),
        started_at=pipeline.started_at.isoformat() if pipeline.started_at else None,
        completed_at=pipeline.completed_at.isoformat() if pipeline.completed_at else None,
    )
