from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6000)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,80}$")]
Items = Annotated[list[Text], Field(max_length=60)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BookSource(StrictModel):
    title: str = Field(default="", max_length=300)
    author: str = Field(default="", max_length=300)
    language: str = Field(default="", max_length=80)
    edition: str = Field(default="", max_length=500)
    translator: str = Field(default="", max_length=200)
    source_url: str = Field(default="", max_length=2000, pattern=r"^(https?://[^\s]+)?$")
    rights_basis: Literal["unknown", "public_domain", "permission", "own_work"] = "unknown"
    territory: str = Field(default="", max_length=200)
    rights_note: str = Field(default="", max_length=2000)


RewriteDimension = Literal["motivation", "relationships", "conflict", "plot_structure", "pov", "theme", "ending", "voice"]


class RewriteRequirements(StrictModel):
    dimensions: list[RewriteDimension] = Field(min_length=3, max_length=8)
    narrative_strategy: Text
    ending_direction: Text
    avoid: Items = Field(min_length=1)

    @model_validator(mode="after")
    def structural_scope(self):
        if len(set(self.dimensions)) != len(self.dimensions):
            raise ValueError("重写维度不可重复")
        if len(set(self.dimensions) - {"voice"}) < 3 or not {"conflict", "plot_structure"} & set(self.dimensions):
            raise ValueError("深度重写至少选择三个结构维度，并包含核心冲突或情节结构")
        return self


class AdaptationBrief(StrictModel):
    idea: Text
    preset: Literal["custom", "localize", "xianxia", "system", "xianxia_system", "suspense", "revenge", "anthology"] = "custom"
    target_language: Name = "简体中文"
    naming_style: Name = "中文姓名，称谓与文化背景统一"
    audience: Name = "成年读者"
    tone: Name = "悬念清晰、人物动机可信"
    preserve: Items = Field(default_factory=list)
    change: Items = Field(default_factory=list)
    constraints: Items = Field(default_factory=list)
    target_units: int = Field(default=3, ge=1, le=200)
    unit_characters: int = Field(default=2000, ge=100, le=30000)
    rewrite: RewriteRequirements | None = None


class FrameworkCharacter(StrictModel):
    id: Identifier
    source_names: list[Name] = Field(min_length=1, max_length=40)
    target_name: Name
    target_aliases: list[Name] = Field(default_factory=list, max_length=40)
    role: Text


class SettingMapping(StrictModel):
    source: Name
    target: Name
    rationale: Text


class AdaptationFramework(StrictModel):
    era: Name
    time_span: Name
    locations: list[Name] = Field(min_length=1, max_length=20)
    historical_policy: Text
    naming_policy: Text
    characters: list[FrameworkCharacter] = Field(default_factory=list, max_length=100)
    setting_mappings: list[SettingMapping] = Field(default_factory=list, max_length=60)
    plot_spine: Items = Field(min_length=1)
    allowed_inventions: Items = Field(default_factory=list)
    prohibited_elements: Items = Field(min_length=1)
    forbidden_terms: list[Name] = Field(default_factory=list, max_length=100)
    scope_note: Text


class NewAdaptation(StrictModel):
    name: Name
    mode: Literal["adaptation", "translation"] = "adaptation"
    chapter_ids: list[str] = Field(min_length=1, max_length=4000)
    brief: AdaptationBrief
    require_framework: Literal[True] = True
    framework: AdaptationFramework | None = None


class NewDeepRewrite(StrictModel):
    name: Name
    brief: AdaptationBrief

    @model_validator(mode="after")
    def needs_rewrite_conditions(self):
        if self.brief.rewrite is None:
            raise ValueError("请填写深度重写的结构要求")
        return self


class Revision(StrictModel):
    expected_revision: int = Field(ge=0)


class UpdateAdaptation(Revision):
    name: Name
    brief: AdaptationBrief
    chapter_ids: list[str] = Field(min_length=1, max_length=4000)


class SubmitFramework(Revision):
    framework: AdaptationFramework
    confirm: bool = False


class Evidence(StrictModel):
    paragraph_id: str
    quote: Annotated[str, StringConstraints(min_length=1, max_length=1500)]


class SourceCharacter(StrictModel):
    name: Name
    aliases: list[Name] = Field(default_factory=list, max_length=40)
    role: Text


class SourceAnalysis(StrictModel):
    summary: Text
    characters: list[SourceCharacter] = Field(default_factory=list, max_length=60)
    setting: Text
    plot_beats: Items = Field(min_length=1)
    opportunities: Items = Field(default_factory=list)
    evidence: list[Evidence] = Field(min_length=1, max_length=30)
    structural_observations: Items = Field(default_factory=list)


class SubmitAnalysis(Revision):
    chunk_id: str
    analysis: SourceAnalysis


class AdaptedCharacter(StrictModel):
    id: Identifier
    source_names: list[Name] = Field(default_factory=list, max_length=40)
    target_name: Name
    target_aliases: list[Name] = Field(default_factory=list, max_length=40)
    role: Text
    motivation: Text
    arc: Text
    relationships: Items = Field(default_factory=list)


class WorldRule(StrictModel):
    id: Identifier
    rule: Text
    cost: Text
    limit: Text


class PowerSystem(StrictModel):
    realms: list[Name] = Field(min_length=1, max_length=30)
    advancement: Text
    costs: Items = Field(min_length=1)
    limits: Items = Field(min_length=1)


class SystemMechanics(StrictModel):
    name: Name
    trigger: Text
    abilities: Items = Field(min_length=1)
    costs: Items = Field(min_length=1)
    limits: Items = Field(min_length=1)


class StoryBible(StrictModel):
    setting: Text
    tone: Text
    naming_strategy: Text
    characters: list[AdaptedCharacter] = Field(min_length=1, max_length=100)
    world_rules: list[WorldRule] = Field(min_length=1, max_length=60)
    immutable_facts: Items = Field(min_length=1)
    power_system: PowerSystem | None = None
    system_mechanics: SystemMechanics | None = None


class OutlineUnit(StrictModel):
    id: Identifier
    title: Name
    source_chapter_ids: list[str] = Field(min_length=1, max_length=4000)
    objective: Text
    conflict: Text
    turning_point: Text
    cliffhanger: Text
    beats: Items = Field(min_length=1)


class OmittedChapter(StrictModel):
    chapter_id: str
    reason: Text


class BaselineEvidence(StrictModel):
    source: Literal["original", "adaptation"]
    chapter_id: str
    paragraph_id: str
    quote: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]


class StructuralChange(StrictModel):
    dimension: RewriteDimension
    before: Text
    after: Text
    reason: Text
    target_unit_ids: list[Identifier] = Field(min_length=1, max_length=200)
    evidence: list[BaselineEvidence] = Field(min_length=2, max_length=12)


class RewriteDesign(StrictModel):
    diagnosis: Text
    narrative_strategy: Text
    ending: Text
    changes: list[StructuralChange] = Field(min_length=3, max_length=8)
    retained_elements: Items = Field(min_length=1)
    removed_elements: Items = Field(min_length=1)


class AdaptationPlan(StrictModel):
    logline: Text
    synopsis: Text
    bible: StoryBible
    units: list[OutlineUnit] = Field(min_length=1, max_length=200)
    omitted_chapters: list[OmittedChapter] = Field(default_factory=list, max_length=4000)
    rewrite_design: RewriteDesign | None = None


class SubmitPlan(Revision):
    plan: AdaptationPlan


class AdaptationDraft(StrictModel):
    title: Name
    paragraphs: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=12000)]] = Field(min_length=1, max_length=1500)
    summary: Text
    continuity_notes: Items = Field(min_length=1)
    change_notes: Items = Field(min_length=1)
    source_chunk_ids: list[str] = Field(min_length=1, max_length=10000)
    source_paragraph_ids: list[str] | None = Field(default=None, min_length=1, max_length=1500)


class SubmitDraft(Revision):
    draft: AdaptationDraft


CheckCategory = Literal["names", "world_rules", "causality", "continuity", "brief", "source_traceability", "framework_fit", "structural_change", "independent_expression", "translation_fidelity", "translation_completeness"]


class ReviewChecks(StrictModel):
    names: bool
    world_rules: bool
    causality: bool
    continuity: bool
    brief: bool
    source_traceability: bool
    framework_fit: bool | None = None
    structural_change: bool | None = None
    independent_expression: bool | None = None
    translation_fidelity: bool | None = None
    translation_completeness: bool | None = None


class Finding(StrictModel):
    category: CheckCategory
    severity: Literal["error", "warning", "info"]
    message: Text


class AdaptationReview(StrictModel):
    draft_revision: int = Field(ge=1)
    reviewed_chunk_ids: list[str] = Field(min_length=1, max_length=10000)
    summary: Text
    checks: ReviewChecks
    findings: list[Finding] = Field(default_factory=list, max_length=100)


class SubmitAdaptationReview(Revision):
    review: AdaptationReview


class FinalizeAdaptation(Revision):
    name: Name


class RewriteComparison(StrictModel):
    dimension: RewriteDimension
    unit_id: Identifier
    paragraph_id: str
    quote: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
    baseline: list[BaselineEvidence] = Field(min_length=2, max_length=12)
    judgment: Text
    passed: bool


class RewriteAudit(StrictModel):
    unit_revisions: dict[str, int]
    reviewed_chunk_ids: list[str] = Field(min_length=1, max_length=10000)
    summary: Text
    comparisons: list[RewriteComparison] = Field(min_length=3, max_length=2400)
    remaining_risks: Items = Field(default_factory=list)


class SubmitRewriteAudit(Revision):
    audit: RewriteAudit
