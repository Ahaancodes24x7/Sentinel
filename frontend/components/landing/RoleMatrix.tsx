import { can } from "@/lib/rbac";
import { ROLE_CAPS, ROLES, ROLE_LABEL } from "./content";
import { Section } from "./Section";

export function RoleMatrix() {
  return (
    <Section
      id="roles"
      index="04"
      eyebrow="Access"
      title="Role-based access, mirrored from the backend gates"
      lede="The same matrix drives the navigation, the action buttons, and the API's own checks. Access is provisioned per person."
    >
      <div className="overflow-x-auto border border-line bg-surface">
        <table className="w-full min-w-[36rem] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line">
              <th scope="col" className="label px-4 py-2 text-left !text-ink">
                Capability
              </th>
              {ROLES.map((r) => (
                <th
                  key={r}
                  scope="col"
                  className="label px-4 py-2 text-center !text-ink"
                >
                  {ROLE_LABEL[r]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROLE_CAPS.map((c) => (
              <tr key={c.cap} className="border-b border-line last:border-b-0">
                <td className="px-4 py-2 text-muted">{c.label}</td>
                {ROLES.map((r) => (
                  <td key={r} className="px-4 py-2 text-center">
                    {can(r, c.cap) ? (
                      <span className="text-clear" title="Granted">
                        &#9679;
                        <span className="sr-only">granted</span>
                      </span>
                    ) : (
                      <span className="text-line" title="Not granted">
                        &mdash;
                        <span className="sr-only">not granted</span>
                      </span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}
