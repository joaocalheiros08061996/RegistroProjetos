from infra.database.connection import get_connection


class SupabasePrivacyAcknowledgementRepository:
    def record_signup_acknowledgement(
        self,
        *,
        user_id: str,
        policy_version: str,
        email_hash: str,
        ip_hash: str,
    ) -> None:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into auth_privacy_acknowledgements (
                    user_id,
                    policy_version,
                    status,
                    source,
                    email_hash,
                    ip_hash,
                    acknowledged_at
                )
                values (%s, %s, 'ACKNOWLEDGED', 'SIGNUP', %s, %s, now())
                on conflict (user_id, policy_version)
                do update set
                    status = 'ACKNOWLEDGED',
                    source = 'SIGNUP',
                    email_hash = excluded.email_hash,
                    ip_hash = excluded.ip_hash,
                    acknowledged_at = now(),
                    recorded_at = now(),
                    administrative_reason = null
                """,
                (user_id, policy_version, email_hash, ip_hash),
            )
            conn.commit()
