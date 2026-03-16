# KabuSys

日本株向け自動売買 / データプラットフォームのコアライブラリ。  
J-Quants API から市場データを取得して DuckDB に保存し、品質チェック・監査ログ・ETL パイプラインを提供します。

主な設計方針：
- API レート制限・リトライ・トークン自動更新を備えた堅牢なデータ取得
- DuckDB を中心とした 3 層データレイヤ（Raw / Processed / Feature）と Execution / Audit 層
- ETL の冪等性（ON CONFLICT DO UPDATE）・品質チェック・監査トレーサビリティ

---

## 機能一覧

- 設定管理
  - 環境変数および .env / .env.local の自動読み込み（パッケージルート検出）
  - 必須環境変数の検証
- J-Quants API クライアント（data/jquants_client.py）
  - 日足（OHLCV）、財務四半期データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応、指数バックオフリトライ、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で付与
  - DuckDB への冪等保存関数（save_*）
- DuckDB スキーマ（data/schema.py）
  - Raw / Processed / Feature / Execution 用テーブル群とインデックスの作成
  - init_schema() / get_connection()
- ETL パイプライン（data/pipeline.py）
  - 差分更新（最終取得日ベース、バックフィル）、カレンダー先読み、品質チェック付きの日次 ETL（run_daily_etl）
  - 個別ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
- 品質チェック（data/quality.py）
  - 欠損・スパイク（前日比）・重複・日付整合性チェック
  - 問題は QualityIssue オブジェクトリストとして返却（error / warning）
- 監査ログ（data/audit.py）
  - シグナル → 発注要求 → 約定 のトレーサビリティテーブル群（order_request_id を冪等キーに）
  - init_audit_schema()/init_audit_db()
- その他
  - ETL 結果集約データクラス（ETLResult）
  - パッケージ公開モジュール構成（kabusys.data / strategy / execution / monitoring）

---

## 必要要件（開発環境）

- Python 3.10 以上（型演算子 `|` 等の構文を使用）
- duckdb（DuckDB Python バインディング）
- 標準ライブラリ（urllib 等）で動作

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# 開発中にパッケージとして使う場合
pip install -e .
```

※ requirements.txt が別途ある場合はそれを参照してください。

---

## 環境変数 / .env

パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を自動で読み込みます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須は README 内で明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

簡単な .env 例:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化する:

   ```bash
   git clone <REPO_URL>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストールする:

   ```bash
   pip install --upgrade pip
   pip install duckdb
   pip install -e .   # package を開発モードでインストール（任意）
   ```

3. プロジェクトルートに `.env`（と必要なら `.env.local`）を作成し、必要な環境変数を設定する。

4. DuckDB スキーマを初期化する（コード内から実行）:

   Python REPL / スクリプト例:

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

5. （監査ログを別 DB に分ける場合）
   - 既存接続に監査スキーマを追加する:

   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

   - 監査専用 DB を作成する場合:

   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要 API と例）

以下はライブラリを直接使う簡単な例です。スクリプトやジョブスケジューラから呼び出して運用します。

- ETL（日次実行）:

```python
from datetime import date
import logging

from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# ログ設定
logging.basicConfig(level=settings.log_level)

# DB 初期化（まだ作成していない場合）
conn = init_schema(settings.duckdb_path)

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date.today())

# ETL 結果の確認
print(result.to_dict())
```

- J-Quants 生データの直接取得:

```python
from kabusys.data import jquants_client as jq

# トークンは内部で settings.jquants_refresh_token を参照して取得される
data = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
print(len(data))
```

- DuckDB スキーマ操作:

```python
from kabusys.data.schema import get_connection, init_schema
conn = init_schema("data/kabusys.duckdb")
# または既存 DB へ接続
conn2 = get_connection("data/kabusys.duckdb")
```

- 品質チェックを個別に実行:

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

注意点:
- J-Quants API にはレート制限（120 req/min）があります。jquants_client で間隔調整・リトライを内部的に行っていますが、大量取得をする際は配慮してください。
- id_token のキャッシュと 401 時の自動リフレッシュを実装しています。get_id_token は allow_refresh=False の呼び出しに注意（無限再帰防止設計）。
- DuckDB 側では ON CONFLICT DO UPDATE を用いた冪等保存を行います。

---

## ディレクトリ構成

パッケージ内の主なファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理（自動 .env ロード）
    - data/
      - __init__.py
      - jquants_client.py          — J-Quants API クライアント（取得・保存）
      - schema.py                  — DuckDB スキーマ定義・初期化
      - pipeline.py                — ETL パイプライン（run_daily_etl 等）
      - quality.py                 — データ品質チェック
      - audit.py                   — 監査ログテーブル定義・初期化
      - pipeline.py
    - strategy/
      - __init__.py                — 戦略層（将来的に拡張）
    - execution/
      - __init__.py                — 発注実行層（将来的に拡張）
    - monitoring/
      - __init__.py                — 監視 / メトリクス（将来的に拡張）

ドキュメント参照:
- DataSchema.md / DataPlatform.md がプロジェクト内にある想定（実装コメントに基づく設計参照）。

---

## 運用上の注意 / ベストプラクティス

- 本番（live）モードでは `KABUSYS_ENV=live` を設定し、安全な認証情報管理（Vault 等）と監査ログ保存先を検討してください。
- ETL は外部 API の変更やデータ欠損に対して堅牢に設計されていますが、品質チェック結果（QualityIssue）の重大度に応じて人手の判断やアラートを設定してください。
- 発注 / 実取引の機能は監査・冪等性を重視しているものの、取引ロジック・ブローカー API 実装は別途必要です（execution モジュールの実装を追加してください）。
- テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うか、テスト用 .env を用いて設定の切り替えを行ってください。

---

必要に応じて README を拡張して、運用ガイド、CI/CD、テスト手順、具体的な戦略実装例、Slack 通知サンプル等を追加できます。追加で書いてほしいセクションがあれば教えてください。