"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Crosshair, FileImage, Plus, RotateCcw, ScanLine, X } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import type {
  CreateRunResponse,
  RocketListResponse,
  RocketResponse,
  RunDetailResponse,
  FindingSchema,
  UploadReferenceResponse,
} from "@/lib/schemas";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { VerdictBadge } from "@/components/verdict/VerdictBadge";
import { ManualInputsDialog } from "@/components/report/ManualInputsDialog";
import { useRunStream } from "@/hooks/use-run-stream";
import { ANGLES, QuadrantResults } from "./QuadrantResults";
import { CameraGuideHUD } from "./CameraGuideHUD";
import { RocketProfileDialog } from "./RocketProfileDialog";
import { MultiAngleUploader } from "./MultiAngleUploader";
import { CountUp } from "@/components/react-bits/CountUp";
import { MicroSlats } from "./MicroSlats";
import { TelemetryHeading } from "./TelemetryHeading";

const imageSchema = z
  .custom<File>((value) => value instanceof File, "Choose an image")
  .refine(
    (file) => ["image/jpeg", "image/png", "image/webp"].includes(file.type),
    "Use JPG, PNG, or WebP",
  )
  .refine((file) => file.size <= 10 * 1024 * 1024, "Image exceeds 10 MB");
const captureSchema = z.object({
  rocket_id: z.string().min(1, "Select a rocket profile"),
  front: imageSchema,
  right: imageSchema,
  back: imageSchema,
  left: imageSchema,
});
const profileSchema = z.object({
  name: z.string().trim().min(1, "Enter a vehicle name").max(100),
  vehicle_class: z.string().trim().min(1, "Enter a vehicle class").max(50),
  notes: z.string().trim().max(500).optional(),
  front: imageSchema,
  right: imageSchema,
  back: imageSchema,
  left: imageSchema,
});

function CapturePreview({ file, label }: { file?: File; label: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!file) {
      setUrl(null);
      return;
    }
    const next = URL.createObjectURL(file);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [file]);
  return url ? (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={url}
      alt={`${label} capture preview`}
      className="absolute inset-0 h-full w-full object-contain p-3"
    />
  ) : (
    <div className="flex flex-col items-center gap-3 text-muted-foreground">
      <Crosshair className="h-10 w-10 stroke-1" />
      <span className="text-xs font-mono uppercase tracking-widest">Awaiting capture</span>
    </div>
  );
}

export function MultiAngleInspection() {
  const [runId, setRunId] = useState<string | null>(null);
  const [showProfile, setShowProfile] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [enrollmentId, setEnrollmentId] = useState<string | null>(null);
  const form = useForm<z.infer<typeof captureSchema>>({
    resolver: zodResolver(captureSchema),
    defaultValues: { rocket_id: "" },
  });
  const profile = useForm<z.infer<typeof profileSchema>>({ resolver: zodResolver(profileSchema) });
  const registerCapture = form.register;
  useEffect(() => {
    for (const { key } of ANGLES) registerCapture(key);
  }, [registerCapture]);
  const files = form.watch();
  const captures = ANGLES.filter(({ key }) => files[key]).length;
  const rockets = useQuery({
    queryKey: ["rockets"],
    queryFn: () => apiClient.get<RocketListResponse>("/api/rockets"),
  });
  const stream = useRunStream(runId);
  const run = useQuery({
    queryKey: ["inspection", runId],
    enabled: !!runId,
    queryFn: () => apiClient.get<RunDetailResponse>(`/api/runs/${runId}`),
    refetchInterval: (query) => (query.state.data?.status === "running" ? 1500 : false),
  });
  const findings = useQuery({
    queryKey: ["inspection-findings", runId],
    enabled: !!runId,
    queryFn: () => apiClient.get<FindingSchema[]>(`/api/runs/${runId}/findings`),
    refetchInterval: run.data?.status === "running" ? 1500 : false,
  });
  const refreshRun = run.refetch;
  const refreshFindings = findings.refetch;
  useEffect(() => {
    if (stream.status === "completed" || stream.status === "failed") {
      void refreshRun();
      void refreshFindings();
    }
  }, [stream.status, refreshRun, refreshFindings]);

  const createProfile = useMutation({
    mutationFn: async (values: z.infer<typeof profileSchema>) => {
      const rocket = enrollmentId
        ? await apiClient.get<RocketResponse>(`/api/rockets/${enrollmentId}`)
        : await apiClient.post<RocketResponse>("/api/rockets", {
            name: values.name,
            vehicle_class: values.vehicle_class,
            notes: values.notes,
          });
      setEnrollmentId(rocket.id);
      for (const { key } of ANGLES) {
        const body = new FormData();
        body.append("file", values[key]);
        await apiClient.upload<UploadReferenceResponse>(
          `/api/rockets/${rocket.id}/references/${key}`,
          body,
        );
      }
      return rocket;
    },
    onSuccess: async (rocket) => {
      await rockets.refetch();
      form.reset({ ...form.getValues(), rocket_id: rocket.id });
      profile.reset();
      setEnrollmentId(null);
      setShowProfile(false);
    },
  });
  const inspect = useMutation({
    mutationFn: (values: z.infer<typeof captureSchema>) => {
      const body = new FormData();
      body.append("rocket_id", values.rocket_id);
      for (const { key } of ANGLES) body.append(key, values[key]);
      return apiClient.upload<CreateRunResponse>("/api/inspections", body);
    },
    onSuccess: (response) => setRunId(response.run_id),
  });
  const allFindings =
    findings.data && findings.data.length >= stream.findings.length
      ? findings.data
      : stream.findings;
  const activeVerdict = run.data?.verdict ?? stream.verdict;
  const busy = inspect.isPending || (!!runId && (!run.data || run.data.status === "running"));
  const failed = run.data?.status === "failed" || stream.status === "failed";

  return (
    <div className="space-y-6">
      <div className="grid gap-6 border-b border-border pb-6 md:grid-cols-[1fr_auto] md:items-end">
        <div className="space-y-3">
          <p className="flex items-center gap-2 text-xs font-mono uppercase tracking-[0.2em] text-steel">
            <ScanLine className="h-4 w-4" /> <TelemetryHeading />
          </p>
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">
            A clearer view of flight readiness.
          </h2>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Inspect body, fins, and launchpad conditions across four views. Each finding stays
            linked to its capture; all views inform one deterministic decision.
          </p>
        </div>
        <div className="border-l-2 border-steel pl-5 font-mono">
          <p className="text-4xl tracking-tight">
            <CountUp to={captures} duration={0.4} />
            <span className="text-lg text-muted-foreground"> / 04</span>
          </p>
          <p className="mt-1 text-xs uppercase tracking-widest text-muted-foreground">
            Images selected
          </p>
          <MicroSlats count={captures} />
        </div>
      </div>

      {!runId && (
        <>
          <Card className="p-5">
            <div className="flex flex-wrap items-end gap-4">
              <div className="min-w-48 flex-1 space-y-2">
                <label
                  htmlFor="rocket-profile"
                  className="text-xs font-mono uppercase tracking-widest text-muted-foreground"
                >
                  01 / Vehicle profile
                </label>
                <select
                  id="rocket-profile"
                  {...form.register("rocket_id")}
                  disabled={inspect.isPending}
                  className="block w-full rounded-md border border-border bg-background p-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="">
                    {rockets.isPending ? "Loading vehicles..." : "Select a registered vehicle"}
                  </option>
                  {rockets.data?.items.map((rocket) => (
                    <option key={rocket.id} value={rocket.id}>
                      {rocket.name} / {rocket.vehicle_class}
                    </option>
                  ))}
                </select>
                {form.formState.errors.rocket_id && (
                  <p role="alert" className="text-xs text-destructive">
                    {form.formState.errors.rocket_id.message}
                  </p>
                )}
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  profile.reset();
                  setEnrollmentId(null);
                  createProfile.reset();
                  setShowProfile(true);
                }}
                disabled={inspect.isPending}
              >
                <Plus className="mr-2 h-4 w-4" /> Register vehicle
              </Button>
              {files.rocket_id && (
                <Button
                  type="button"
                  variant="outline"
                  disabled={inspect.isPending}
                  onClick={() => {
                    const selected = rockets.data?.items.find(
                      (rocket) => rocket.id === files.rocket_id,
                    );
                    if (!selected) return;
                    profile.reset({
                      name: selected.name,
                      vehicle_class: selected.vehicle_class,
                      notes: selected.notes ?? "",
                    });
                    setEnrollmentId(selected.id);
                    setShowProfile(true);
                  }}
                >
                  Enroll reference set
                </Button>
              )}
            </div>
            {rockets.isError && (
              <div role="alert" className="mt-3 text-sm text-destructive">
                Unable to load vehicles.{" "}
                <Button variant="outline" onClick={() => rockets.refetch()}>
                  Retry
                </Button>
              </div>
            )}
            <RocketProfileDialog
              open={showProfile}
              onOpenChange={setShowProfile}
              busy={createProfile.isPending}
            >
              <form
                className="mt-5 space-y-5 border-t border-border pt-5"
                onSubmit={profile.handleSubmit((values) => createProfile.mutate(values))}
              >
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="space-y-2 text-xs">
                    Vehicle name
                    <input
                      {...profile.register("name")}
                      readOnly={!!enrollmentId}
                      placeholder="Aero-X Mk IV"
                      className="block w-full rounded border border-border bg-background p-2 text-sm"
                    />
                    <span className="text-destructive">
                      {profile.formState.errors.name?.message}
                    </span>
                  </label>
                  <label className="space-y-2 text-xs">
                    Vehicle class
                    <input
                      {...profile.register("vehicle_class")}
                      readOnly={!!enrollmentId}
                      placeholder="Research vehicle"
                      className="block w-full rounded border border-border bg-background p-2 text-sm"
                    />
                    <span className="text-destructive">
                      {profile.formState.errors.vehicle_class?.message}
                    </span>
                  </label>
                </div>
                <label className="block space-y-2 text-xs">
                  Vehicle notes
                  <textarea
                    {...profile.register("notes")}
                    readOnly={!!enrollmentId}
                    maxLength={500}
                    rows={2}
                    className="block w-full rounded border border-border bg-background p-2 text-sm"
                    placeholder="Reference setup, vehicle configuration, or inspection notes"
                  />
                </label>
                <div>
                  <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
                    <div>
                      <p className="text-xs font-mono uppercase tracking-widest text-steel">
                        Golden reference set
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Use clear 4:3 images, at least 640 by 480 pixels, from the standard setup.
                      </p>
                    </div>
                    <span className="text-xs text-muted-foreground">Four images required</span>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                    {ANGLES.map((angle) => {
                      const baseline = profile.watch(angle.key);
                      return (
                        <label
                          key={angle.key}
                          className="cursor-pointer rounded-md border border-border bg-background p-3 text-xs focus-within:ring-2 focus-within:ring-ring"
                        >
                          <span className="flex items-center justify-between font-medium">
                            <span>{angle.label}</span>
                            <span className="font-mono text-muted-foreground">
                              {angle.degrees}&deg;
                            </span>
                          </span>
                          <span className="mt-3 block truncate text-muted-foreground">
                            {baseline?.name ?? "Select baseline image"}
                          </span>
                          <input
                            type="file"
                            accept="image/jpeg,image/png,image/webp"
                            className="sr-only"
                            aria-label={`${angle.label} golden reference`}
                            onChange={(event) => {
                              const file = event.target.files?.[0];
                              if (file) {
                                profile.setValue(angle.key, file, { shouldValidate: true });
                              }
                            }}
                          />
                          {profile.formState.errors[angle.key] && (
                            <span className="mt-2 block text-destructive">
                              {profile.formState.errors[angle.key]?.message}
                            </span>
                          )}
                        </label>
                      );
                    })}
                  </div>
                </div>
                <div className="flex items-center justify-between gap-3 border-t border-border pt-4">
                  <p className="text-xs text-muted-foreground">
                    References are stored server-side and compared independently for each angle.
                  </p>
                  <Button disabled={createProfile.isPending}>
                    {createProfile.isPending
                      ? "Registering references..."
                      : "Save vehicle and references"}
                  </Button>
                </div>
                {createProfile.isError && (
                  <p role="alert" className="text-sm text-destructive">
                    {createProfile.error.message}
                  </p>
                )}
              </form>
            </RocketProfileDialog>
            {files.rocket_id &&
              rockets.data?.items.find((rocket) => rocket.id === files.rocket_id) && (
                <div className="mt-4 space-y-3 border-t border-border pt-4">
                  <p className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
                    Enrolled golden references /{" "}
                    {rockets.data.items.find((rocket) => rocket.id === files.rocket_id)
                      ?.reference_count ?? 0}{" "}
                    of 4
                  </p>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {ANGLES.map((angle) => {
                      const reference = rockets.data.items
                        .find((rocket) => rocket.id === files.rocket_id)
                        ?.references?.find((item) => item.quadrant === angle.key);
                      return (
                        <div
                          key={angle.key}
                          className="overflow-hidden rounded border border-border bg-background"
                        >
                          <div className="relative aspect-[4/3]">
                            {reference ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img
                                src={reference.image_url}
                                alt={`${angle.label} enrolled baseline`}
                                className="h-full w-full object-contain"
                              />
                            ) : (
                              <p className="flex h-full items-center justify-center p-2 text-xs text-muted-foreground">
                                Baseline missing
                              </p>
                            )}
                          </div>
                          <p className="border-t border-border p-2 text-xs font-mono">
                            {angle.label} / {angle.degrees}&deg;
                          </p>
                        </div>
                      );
                    })}
                  </div>
                  {(rockets.data.items.find((rocket) => rocket.id === files.rocket_id)
                    ?.reference_count ?? 0) < 4 && (
                    <p className="text-xs text-hold">
                      Missing baselines will produce degraded warnings. Complete enrollment before
                      using reference comparison.
                    </p>
                  )}
                </div>
              )}
          </Card>

          <form
            onSubmit={form.handleSubmit((values) => inspect.mutate(values))}
            className="space-y-5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
                02 / Quadrant captures
              </p>
              <p className="text-xs text-muted-foreground">JPG, PNG, WebP / 10 MB per image</p>
            </div>
            <MultiAngleUploader
              disabled={inspect.isPending}
              onCapture={(quadrant, file) =>
                form.setValue(quadrant, file, { shouldValidate: true })
              }
            >
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {ANGLES.map((angle, index) => (
                  <Card key={angle.key} className="overflow-hidden">
                    <div className="flex items-center justify-between border-b border-border p-4">
                      <span className="font-medium">{angle.label}</span>
                      <span className="font-mono text-sm text-muted-foreground">
                        {angle.degrees}&deg;
                      </span>
                    </div>
                    <div className="relative flex aspect-[4/3] items-center justify-center bg-background">
                      <span className="absolute left-3 top-3 text-xs font-mono text-muted-foreground">
                        Q0{index + 1}
                      </span>
                      <CapturePreview file={files[angle.key]} label={angle.label} />
                      <CameraGuideHUD label={angle.label} />
                    </div>
                    <div className="space-y-3 border-t border-border p-4">
                      <p className="truncate text-xs text-muted-foreground">
                        {files[angle.key]?.name ??
                          `Capture the ${angle.label.toLowerCase()} of the vehicle`}
                      </p>
                      <div className="flex items-center gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          className="flex-1"
                          disabled={inspect.isPending}
                          onClick={() => document.getElementById(`capture-${angle.key}`)?.click()}
                        >
                          <FileImage className="mr-2 h-4 w-4" />
                          {files[angle.key] ? "Replace" : "Select image"}
                        </Button>
                        {files[angle.key] && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            aria-label={`Remove ${angle.label} image`}
                            disabled={inspect.isPending}
                            onClick={() => form.resetField(angle.key)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                      <input
                        id={`capture-${angle.key}`}
                        aria-label={`${angle.label} image`}
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        className="sr-only"
                        disabled={inspect.isPending}
                        onChange={(event) => {
                          const file = event.target.files?.[0];
                          if (file) form.setValue(angle.key, file, { shouldValidate: true });
                          event.target.value = "";
                        }}
                      />
                      {form.formState.errors[angle.key] && (
                        <p role="alert" className="text-xs text-destructive">
                          {form.formState.errors[angle.key]?.message}
                        </p>
                      )}
                    </div>
                  </Card>
                ))}
              </div>
            </MultiAngleUploader>
            <div className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-border bg-card p-5">
              <div>
                <p className="text-sm font-medium">
                  Four perspectives. A single inspection record.
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Each angle is aligned to its golden reference before structural differences are
                  assessed. Alignment failures remain visible as degraded warnings.
                </p>
              </div>
              <Button
                type="submit"
                disabled={inspect.isPending || captures < 4 || !files.rocket_id}
                className="h-11 px-6"
              >
                {inspect.isPending ? "Uploading captures..." : "Run four-angle inspection"}
                <ArrowUpRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
            {inspect.isError && (
              <p role="alert" className="text-sm text-destructive">
                {inspect.error.message}
              </p>
            )}
          </form>
        </>
      )}

      {runId && (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="space-y-3 p-5">
              <p className="text-xs font-mono uppercase text-muted-foreground">
                Aggregate launch decision
              </p>
              {activeVerdict ? (
                <VerdictBadge verdict={activeVerdict} size="lg" />
              ) : (
                <p className="text-lg font-semibold">
                  {failed ? "Inspection incomplete" : "Evaluation in progress"}
                </p>
              )}
              <p className="text-xs text-muted-foreground">Computed by deterministic rules</p>
            </Card>
            <Card className="space-y-3 p-5">
              <p className="text-xs font-mono uppercase text-muted-foreground">Inspection log</p>
              <p className="font-mono text-3xl">
                {allFindings.length}
                <span className="ml-2 text-sm text-muted-foreground">findings</span>
              </p>
              <p className="text-xs text-muted-foreground">
                {busy
                  ? "Processing quadrant checks"
                  : failed
                    ? "Run failed; review required"
                    : "Visual checks complete"}
              </p>
            </Card>
            <Card className="space-y-3 p-5">
              <p className="text-xs font-mono uppercase text-muted-foreground">Range conditions</p>
              <p className="text-sm">Weather and manual clearance are required before GO.</p>
              <Button
                variant="outline"
                onClick={() => setManualOpen(true)}
                disabled={busy || failed}
              >
                Enter manual inputs
              </Button>
            </Card>
          </div>
          {failed && (
            <p role="alert" className="text-sm text-destructive">
              {run.data?.status_reason ??
                stream.failure?.message ??
                "Inspection failed. Start a new run."}
            </p>
          )}
          {run.isError && (
            <p role="alert" className="text-sm text-destructive">
              Cannot retrieve inspection status.{" "}
              <Button variant="outline" onClick={() => run.refetch()}>
                Retry
              </Button>
            </p>
          )}
          <QuadrantResults images={run.data?.quadrants ?? []} findings={allFindings} />
          <div className="flex gap-3">
            <Button
              variant="outline"
              disabled={busy}
              onClick={() => {
                setRunId(null);
                form.reset();
                inspect.reset();
              }}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              New inspection
            </Button>
            {!busy && !failed && (
              <Button asChild>
                <Link href={`/report/${runId}`}>
                  View inspection report
                  <ArrowUpRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            )}
          </div>
          <ManualInputsDialog
            open={manualOpen}
            onOpenChange={setManualOpen}
            runId={runId}
            onSubmit={async (values) => {
              await apiClient.post(`/api/runs/${runId}/manual-inputs`, values);
              setManualOpen(false);
              await run.refetch();
              await findings.refetch();
            }}
          />
        </>
      )}
    </div>
  );
}
