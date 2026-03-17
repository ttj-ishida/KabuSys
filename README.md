# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
J-Quants / kabuステーション 等の外部 API からデータを取得し、DuckDB に保存・品質チェック・監査ログを行うためのモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を主目的とした Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- RSS フィードからのニュース収集（SSRF 対策・トラッキング除去・冪等保存）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・前後営業日検索）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）

設計上、冪等性・トレーサビリティ・セキュリティ（SSRF・XML攻撃・メモリ DoS 等）に配慮しています。

---

## 主な機能一覧

- data/jquants_client.py
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーの取得
  - レート制限（120 req/min）・指数バックオフリトライ・401 時のトークン自動更新
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- data/news_collector.py
  - RSS フィード収集、テキスト前処理（URL除去・空白正規化）、記事IDは正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策、gzip サイズ制限、defusedxml による XML 攻撃対策
  - DuckDB への冪等保存（INSERT ... RETURNING、トランザクションまとめ）
  - 銘柄コード抽出（4桁数字、既知銘柄セットに基づく）
- data/schema.py
  - DuckDB スキーマ（Raw / Processed / Feature / Execution）を定義・初期化
- data/pipeline.py
  - 日次 ETL の実行（calendar → prices → financials → 品質チェック）
  - 差分更新、backfill、品質チェックの統合
- data/calendar_management.py
  - market_calendar を基にした is_trading_day/next_trading_day/prev_trading_day/get_trading_days 等
  - 夜間の calendar_update_job（差分取得・バックフィル・安全チェック）
- data/quality.py
  - 欠損・スパイク・重複・日付不整合のチェック（QualityIssue を返す）
- data/audit.py
  - 監査用テーブル定義（signal_events / order_requests / executions）と初期化
- config.py
  - 環境変数/.env の自動読み込み（プロジェクトルートを .git または pyproject.toml により探索）
  - 主要設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH など）をプロパティで取得

---

## 動作環境・依存関係

- Python 3.10 以上（型ヒントの union 型（|）を使用）
- 主な依存パッケージ（pip でインストール）
  - duckdb
  - defusedxml

（必要に応じて追加の HTTP/Slack クライアント等を利用するユーティリティは別途追加）

例:
```bash
python -m pip install "duckdb" "defusedxml"
```

---

## セットアップ手順

1. リポジトリをクローン／ダウンロード

2. Python 仮想環境を作成・有効化（推奨）
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\Scripts\activate    # Windows
```

3. 依存パッケージをインストール
```bash
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
```

4. 環境変数を設定
- ルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を作成すると、自動で読み込まれます（config.py の自動ロード）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテストで利用）。

必須となる主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）

任意／デフォルト値あり:
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視用、デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment （development/paper_trading/live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

例 .env（サンプル）:
```text
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意: config.Settings は未設定の必須変数に対して ValueError を投げます。

---

## 使い方（基本例）

以下は Python スクリプト／インタラクティブでの利用例です。実際は CLI ラッパーやジョブスケジューラ（cron, systemd timer, Airflow など）から呼び出すことを想定しています。

1. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# デフォルト: data/kabusys.duckdb を作成（親ディレクトリ自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2. 日次 ETL を実行（差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可
print(result.to_dict())
```

3. RSS ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# sources を省略するとデフォルトの RSS ソースを使用
res = run_news_collection(conn, known_codes={"7203", "6758"})  # known_codes は任意
print(res)
```

4. カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

5. 監査ログテーブルの初期化（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
init_audit_schema(conn)
```

ログレベルは環境変数 `LOG_LEVEL` で制御してください。

---

## よくある運用パターン

- 日次 ETL を夜間バッチで実行（run_daily_etl）。先に calendar を取得し、営業日判定に使用。
- RSS ニュースは定期実行（短い間隔でポーリング）。新規記事に対して銘柄抽出・news_symbols に紐付け。
- 発注・約定・ポートフォリオは別モジュール（execution、strategy）と連携し、監査ログで追跡。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットして自動 env ロードを無効化し、テスト用 env を明示的に設定する。

---

## ディレクトリ構成

プロジェクト内の主要ファイルとディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理 (.env 自動読み込み)
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（取得・保存・リトライ）
    - news_collector.py                — RSS ニュース収集・保存・銘柄抽出
    - schema.py                        — DuckDB スキーマ定義・初期化
    - pipeline.py                      — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py           — マーケットカレンダー管理（営業日ロジック）
    - audit.py                         — 監査ログの DDL と初期化
    - quality.py                       — データ品質チェック
  - strategy/
    - __init__.py                       — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                       — 発注実行関連（拡張ポイント）
  - monitoring/
    - __init__.py                       — 監視用モジュール（拡張ポイント）

ドキュメントや設計仕様は DataPlatform.md / DataSchema.md 等が参照される想定です（このリポジトリの外部仕様）。

---

## 注意点 / 補足

- 環境変数が未設定の場合、config.Settings のプロパティが ValueError を投げます。必須変数は .env.example などを参考に準備してください。
- J-Quants API のレート制限（120 req/min）に注意してください（jquants_client はレート制御を内蔵）。
- DuckDB はトランザクションと INSERT ... RETURNING を利用しており、データ整合性に配慮しています。
- RSS 収集は外部 URL を扱うため、SSRF 対策やサイズ制限が組み込まれていますが、運用環境でもネットワークの安全設定を推奨します。
- execution / strategy / monitoring は拡張ポイントとして設計されており、ブローカー連携やアルゴリズムは別途実装してください。

---

この README はコードベースに基づいてまとめた概要です。利用方法や運用ルールは運用チームのポリシーに合わせて追加・調整してください。質問や補足があれば教えてください。