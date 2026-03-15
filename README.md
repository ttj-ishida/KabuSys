# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ（KabuSys）

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された Python パッケージです。  
主な目的は以下の通りです。

- J-Quants 等の外部 API から市場データや財務データを取得して永続化する
- DuckDB を利用したスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 発注・約定の監査ログ（トレーサビリティ）管理
- 戦略（strategy）、発注実行（execution）、監視（monitoring）などの基盤を提供

パッケージはモジュールごとに責務が分離されており、個別に組み合わせて利用できます。

---

## 主な機能一覧

- 環境変数 / .env ファイルの自動読み込み（.env / .env.local、無効化フラグあり）
- 設定管理（`kabusys.config.settings`）
  - 必須変数の取得とバリデーション（環境: development / paper_trading / live、ログレベルの検証等）
- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制限（120 req/min）を遵守する固定間隔レートリミッタ
  - リトライ（指数バックオフ）・401 時のトークン自動リフレッシュ（1 回のみ）
  - ページネーション対応・ID トークンキャッシュ
  - 取得時刻（fetched_at）を UTC で付与（Look-ahead Bias 対策）
  - DuckDB への保存（冪等：ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義／初期化（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 初期化関数 `init_schema` / 既存 DB 接続取得 `get_connection`
- 監査ログ（注文→約定のトレーサビリティ）定義・初期化（`kabusys.data.audit`）
  - signal_events, order_requests, executions テーブル
  - `init_audit_schema`（既存接続への追加） / `init_audit_db`（専用 DB 初期化）
- その他のモジュール骨組み：`strategy`、`execution`、`monitoring`（拡張ポイント）

---

## セットアップ手順

前提：Python 3.9+（型ヒントに Union | を使用しているため互換性に注意）

1. 仮想環境を作成・有効化（推奨）
   - macOS / Linux:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール（最低限 duckdb）
   ```bash
   pip install duckdb
   ```
   （パッケージが PyPI 化されている場合は `pip install kabusys` や `pip install -e .` を利用します）

3. プロジェクトルートに `.env`（および必要なら `.env.local`）を配置
   - 自動ロードはパッケージが配置されたファイルパスから `.git` または `pyproject.toml` を探してプロジェクトルートを判定します。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数（主なもの）

以下は本パッケージで使用される主要な環境変数とデフォルト / 備考です。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（`kabusys.data.jquants_client.get_id_token` で使用）
- KABU_API_PASSWORD (必須)
  - kabuステーション等の API パスワード
- KABU_API_BASE_URL
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH
  - DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH
  - 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV
  - 有効値: development, paper_trading, live（デフォルト: development）
- LOG_LEVEL
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定すると .env 自動読み込みを無効にする

.env のパース仕様（主な点）
- 空行・行頭 `#` はコメント
- `export KEY=val` 形式に対応
- 値にシングル/ダブルクォートを使える（エスケープ処理を考慮）
- クォートなしの場合、`#` の前にスペースまたはタブがあればそれ以降はコメントとして扱う

---

## 使い方（基本例）

以下はライブラリの代表的な使用例です。実行前に必ず必要な環境変数を設定してください。

1. DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # デフォルト path は settings.duckdb_path
```

2. J-Quants から日足を取得して保存
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)

# 例: 銘柄コード 7203（トヨタ自動車）の日足を取得
records = fetch_daily_quotes(code="7203", date_from=date(2023, 1, 1), date_to=date.today())
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

3. 財務データ取得・保存、カレンダー取得 も同様
- fetch_financial_statements / save_financial_statements
- fetch_market_calendar / save_market_calendar

4. ID トークンを明示的に取得する
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
```

5. 監査ログ（order / execution）スキーマを追加
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)
```

（発注処理・戦略実行・モニタは別モジュールで実装して利用してください）

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - schema.py
    - audit.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主なエントリポイント：
- kabusys.config.settings — 環境設定アクセス用
- kabusys.data.jquants_client — J-Quants API クライアント（fetch/save ユーティリティ）
- kabusys.data.schema — DuckDB スキーマ初期化 / 接続取得
- kabusys.data.audit — 監査ログ用テーブル初期化

---

## 開発・運用上の注意事項

- 自動 .env 読み込みはプロジェクトルートを `.git` または `pyproject.toml` で検出します。配布後などでこの自動検出が困難な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で環境変数を準備してください。
- J-Quants API 呼び出しはモジュール内でレート制御とリトライを行いますが、上限（120 req/min）を守るよう設計されています。大量取得やバッチ化の際は注意してください。
- 所有するトークンやパスワードは秘匿して管理してください（.env を git にコミットしない等）。
- DuckDB はファイルベース DB のため、バックアップ・ローテーション設計を運用で検討してください。
- 監査ログは削除しない方針で設計されています（FK は ON DELETE RESTRICT）。トレーサビリティを保つため、データ削除は慎重に行ってください。

---

## よくある質問（FAQ）

Q: .env が自動読み込みされない  
A: パッケージ検出のために .git または pyproject.toml をプロジェクトルートに置いてください。自動読み込みを無効にしている場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認してください。

Q: J-Quants のトークン更新が失敗する  
A: 環境変数 `JQUANTS_REFRESH_TOKEN` の値を確認してください。`get_id_token` は `allow_refresh=False` を内部で使う呼び出しがあるため無限再帰防止が組み込まれています。

---

必要に応じて README を拡張して、CI/CD 手順や具体的な戦略テンプレート、発注フローのサンプルなどを追加できます。追加ドキュメント（DataSchema.md、DataPlatform.md 等）と併せて利用することを推奨します。