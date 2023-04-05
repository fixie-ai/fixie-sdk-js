/**
 * This should be kept in sync with the `AgentConfig` dataclass.
 */
interface AgentConfig {
  handle: string;
  name?: string;
  description: string;
  more_info_url: string;
  language: string;
  entry_point: string;
  deployment_url?: string;
  public?: boolean;
}
export default function serve(agent: AgentConfig, port: number) {

}