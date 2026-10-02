import { useId, useState, type FormEvent } from "react";
import { useCreateCourse, useUpdateCourse } from "../../api/courses";
import type { Course } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Field } from "../../components/ui/Field";
import { Modal } from "../../components/ui/Modal";

const SEMESTER_SUGGESTIONS = ["Fall", "Spring", "Summer", "Winter"];

function currentSemester(): string {
  const month = new Date().getMonth();
  if (month <= 4) return "Spring";
  if (month <= 7) return "Summer";
  return "Fall";
}

interface CourseFormModalProps {
  open: boolean;
  onClose: () => void;
  course?: Course; // edit mode when provided
  onSaved?: (course: Course) => void;
}

export function CourseFormModal({ open, onClose, course, onSaved }: CourseFormModalProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={course ? "Edit course" : "Create a course"}
      description={course ? undefined : "You can add materials right after creating it."}
    >
      <CourseForm
        course={course}
        onCancel={onClose}
        onSaved={(saved) => {
          onClose();
          onSaved?.(saved);
        }}
      />
    </Modal>
  );
}

type FieldErrors = Partial<Record<"name" | "semester" | "year", string>>;

function CourseForm({
  course,
  onCancel,
  onSaved,
}: {
  course?: Course;
  onCancel: () => void;
  onSaved: (course: Course) => void;
}) {
  const id = useId();
  const createCourse = useCreateCourse();
  const updateCourse = useUpdateCourse(course?.id ?? -1);
  const mutation = course ? updateCourse : createCourse;

  const [name, setName] = useState(course?.name ?? "");
  const [semester, setSemester] = useState(course?.semester ?? currentSemester());
  const [year, setYear] = useState(String(course?.year ?? new Date().getFullYear()));
  const [description, setDescription] = useState(course?.description ?? "");
  const [errors, setErrors] = useState<FieldErrors>({});

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const yearNumber = Number(year);
    const nextErrors: FieldErrors = {};
    if (!name.trim()) nextErrors.name = "Give the course a name.";
    if (!semester.trim()) nextErrors.semester = "Enter the semester.";
    if (!Number.isInteger(yearNumber) || yearNumber < 2000 || yearNumber > 2100) {
      nextErrors.year = "Enter a year between 2000 and 2100.";
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    const input = {
      name: name.trim(),
      semester: semester.trim(),
      year: yearNumber,
      description: description.trim() || null,
    };
    if (course) updateCourse.mutate(input, { onSuccess: onSaved });
    else createCourse.mutate(input, { onSuccess: onSaved });
  }

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      <Field label="Course name" htmlFor={`${id}-name`} required error={errors.name}>
        <input
          id={`${id}-name`}
          className="input"
          value={name}
          maxLength={200}
          placeholder="e.g. Container Fundamentals"
          aria-invalid={Boolean(errors.name)}
          data-autofocus
          onChange={(event) => setName(event.target.value)}
        />
      </Field>

      <div className="form-row">
        <Field label="Semester" htmlFor={`${id}-semester`} required error={errors.semester}>
          <input
            id={`${id}-semester`}
            className="input"
            value={semester}
            maxLength={50}
            list={`${id}-semesters`}
            aria-invalid={Boolean(errors.semester)}
            onChange={(event) => setSemester(event.target.value)}
          />
          <datalist id={`${id}-semesters`}>
            {SEMESTER_SUGGESTIONS.map((suggestion) => (
              <option key={suggestion} value={suggestion} />
            ))}
          </datalist>
        </Field>
        <Field label="Year" htmlFor={`${id}-year`} required error={errors.year}>
          <input
            id={`${id}-year`}
            className="input"
            type="number"
            inputMode="numeric"
            min={2000}
            max={2100}
            value={year}
            aria-invalid={Boolean(errors.year)}
            onChange={(event) => setYear(event.target.value)}
          />
        </Field>
      </div>

      <Field
        label="Description"
        htmlFor={`${id}-description`}
        hint="Optional. Helps the assistant judge which questions belong to this course."
      >
        <textarea
          id={`${id}-description`}
          className="textarea"
          rows={3}
          maxLength={2000}
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
      </Field>

      {mutation.error && (
        <p className="form-error" role="alert">
          {mutation.error.message}
        </p>
      )}

      <div className="modal-actions">
        <Button onClick={onCancel}>Cancel</Button>
        <Button type="submit" variant="primary" loading={mutation.isPending}>
          {course ? "Save changes" : "Create course"}
        </Button>
      </div>
    </form>
  );
}
