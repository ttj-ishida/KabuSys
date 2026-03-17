# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データプラットフォームのコアライブラリです。J-Quants API からマーケットデータや財務データ、RSS ニュースを取得して DuckDB に保存し、ETL・品質チェック・カレンダー管理・監査ログなどを提供します。戦略や発注ロジックは strategy / execution 層で組み合わせて利用します。

---

## 主な特徴

- J-Quants API クライアント
  - 株価日足 (OHLCV)、四半期財務データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）対策とリトライ（指数バックオフ）
  - 401 受信時はリフレッシュトークンで自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look‑ahead Bias を抑制

- ニュース収集
  - RSS フィードから記事を収集して前処理（URL除去・空白正規化）
  - URL 正規化 → SHA-256 で一意 ID を作成し冪等保存
  - SSRF や XML Bomb 対策（defusedxml、リダイレクト検査、サイズ制限）
  - 記事と銘柄コードの紐付け（抽出ロジックと一括保存）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマ定義
  - init_schema() による冪等な初期化と各種インデックス作成

- ETL パイプライン
  - 差分更新（最終取得日ベース）とバックフィル機能
  - カレンダー先読み、品質チェック（欠損・スパイク・重複・日付不整合）
  - run_daily_etl() により日次パイプラインを一括実行

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day 等のユーティリティ
  - calendar_update_job による夜間差分更新とバックフィル

- 監査ログ（Audit）
  - signal → order_request → execution のトレースを保存する監査テーブル
  - 発注の冪等キーや UTC タイムスタンプ運用をサポート

- データ品質チェック
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks() でまとめて実行し、QualityIssue リストを返却

---

## 必要条件 / 依存関係

- Python 3.10 以上（型ヒントに | None 構文を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール例（プロジェクトルートで）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージを editable インストールする場合（pyproject.toml がある想定）
pip install -e .
```

必要に応じて他のパッケージ（requests 等）が追加される可能性があります。

---

## 環境変数 / 設定

設定は環境変数および .env ファイルから読み込まれます（kabusys.config.Settings を通じてアクセス）。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベースURL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動 .env ロード
- プロジェクトルートにある `.env` と `.env.local` が自動的に読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

例: .env の最小例（.env.example として保存）

```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン

```bash
git clone <repo_url>
cd <repo_root>
```

2. 仮想環境を作り依存をインストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# もし pyproject.toml がある場合:
pip install -e .
```

3. .env を作成して必要な環境変数を設定（上記参照）。

4. DuckDB スキーマを初期化

Python REPL で:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # デフォルトパスに合わせる
# （または :memory: でインメモリ DB）
```

監査ログ専用 DB を分けたい場合:

```python
from kabusys.data import audit
conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要ユースケース）

以下は主要な関数の使い方サンプルです。実行は Python スクリプトやバッチジョブから行います。

1) 日次 ETL（データ取得・保存・品質チェック）

```python
from datetime import date
import logging
from kabusys.data import schema, pipeline

logging.basicConfig(level=logging.INFO)

# DB 初期化済みの接続を取得
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

2) RSS ニュース収集（既知銘柄リストを渡して銘柄紐付けまで実行）

```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources をカスタマイズ可能。既知銘柄コードのセットを渡す。
known_codes = {"7203", "6758", "9984"}  # 例
result = news_collector.run_news_collection(conn, known_codes=known_codes)
print(result)  # {source_name: new_count}
```

3) J-Quants の ID トークン取得（リフレッシュトークンを明示する場合）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

4) マーケットカレンダー関連

```python
from datetime import date
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
today = date.today()
is_trading = calendar_management.is_trading_day(conn, today)
next_td = calendar_management.next_trading_day(conn, today)
```

5) 品質チェックのみ実行

```python
from kabusys.data import quality, schema
conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn)
for i in issues:
    print(i)
```

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下の主なファイル/モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      — RSS ニュース収集・前処理・DB 保存
    - schema.py              — DuckDB スキーマ定義と初期化
    - pipeline.py            — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py — マーケットカレンダー管理ユーティリティ
    - audit.py               — 監査ログ（信号→発注→約定の記録）
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略層のエントリ（将来的な戦略モジュール）
  - execution/
    - __init__.py            — 発注 / 約定 / ブローカー連携（拡張用）
  - monitoring/
    - __init__.py            — 監視・アラート用モジュール（拡張用）

---

## 開発メモ / 設計に関する注意点

- すべての DB 保存処理は冪等性を重視（INSERT ... ON CONFLICT DO UPDATE / DO NOTHING）しています。
- 取得時刻（fetched_at / created_at）は UTC を基本に取り扱います。
- ニュース収集は SSRF や XML 攻撃対策を行い、安全性に配慮しています（defusedxml、リダイレクト検査、受信サイズ上限）。
- J-Quants API 呼び出しはレート制限とリトライ戦略を実装済みです。429 の場合は Retry-After を優先します。
- settings は自動で .env/.env.local を読み込みますが、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動読込を抑制できます。

---

## 今後の拡張ポイント（例）

- strategy 層に実際の売買アルゴリズム・特徴量生成ロジックを追加
- execution 層で実際の発注アダプタ（kabu API、証券会社API）実装
- monitoring に Slack / Prometheus 連携を追加
- CI での DB マイグレーション・単体テスト整備

---

README に書かれているサンプルはあくまで開始手順です。実運用前に必ず開発環境で動作確認、適切なログ・監視・エラーハンドリングの追加、機密情報管理（トークンの安全保管）を行ってください。質問や追加したいサンプルがあれば教えてください。