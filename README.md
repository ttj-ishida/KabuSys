# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants や RSS 等からデータを取得・保存し、ETL / 品質チェック / ファクター計算 / 監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から日次株価・財務データ・市場カレンダーを取得して DuckDB に保存
- RSS からニュースを収集して記事・銘柄紐付けを作成
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 特徴量（モメンタム・ボラティリティ・バリュー等）計算、IC/統計解析
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（signal → order → execution までのトレーサビリティ）
- 設定は環境変数 / .env ファイルで管理（自動ロード機能あり）

設計方針として、DuckDB を中心に標準ライブラリで堅牢に動作するよう作られており、本番の発注処理へ直接アクセスするモジュールは分離されています。

---

## 機能一覧

- データ取得・保存（data/jquants_client.py）
  - 日次株価（OHLCV）取得（ページネーション対応、レートリミット、トークン自動リフレッシュ、リトライ）
  - 財務データ取得
  - 市場カレンダー取得
  - DuckDB への冪等的保存（ON CONFLICT / DO UPDATE）

- ETL / パイプライン（data/pipeline.py）
  - 差分取得（最終取得日を基に差分のみ取得）
  - 日次 ETL の統合エントリ（run_daily_etl）
  - バックフィル対応、品質チェック連携

- スキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成

- データ品質チェック（data/quality.py）
  - 欠損データ、スパイク、重複、日付不整合の検出
  - QualityIssue オブジェクトで問題を返却

- ニュース収集（data/news_collector.py）
  - RSS フィード取得（SSRF対策、gzip制限、XML脆弱性対策）
  - 記事IDは正規化URLのSHA-256ハッシュ（冪等性）
  - raw_news / news_symbols への保存

- カレンダー管理（data/calendar_management.py）
  - market_calendar の差分更新ジョブ
  - 営業日判定 / 前後営業日取得 / 期間営業日リスト等のユーティリティ

- 研究用モジュール（research/）
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索（forward returns, IC, factor summary, rank）
  - z-score 正規化ユーティリティ（data.stats.zscore_normalize を再エクスポート）

- 監査ログ（data/audit.py）
  - signal_events / order_requests / executions テーブルによる監査トレース
  - UTC タイムスタンプ管理、冪等性設計

- 設定管理（config.py）
  - 環境変数 / .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須設定の取得ラッパー（settings オブジェクト）

---

## 動作要件 / 依存

- Python 3.10+
  - 型アノテーションで `X | None` を使用するため 3.10 以上を想定しています。
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例:

```
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# パッケージを開発インストールする場合（pyproject.toml / setup があれば）
# pip install -e .
```

（プロジェクトに pyproject.toml がある想定なら pip install -e . で依存をまとめて入れられます）

---

## 環境変数

主な必須/推奨環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG/INFO/…（デフォルト: INFO）

自動で .env / .env.local をプロジェクトルートから読み込みます（.git または pyproject.toml がルート検出条件）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
2. Python 仮想環境の作成・有効化
3. 依存のインストール（duckdb, defusedxml 等）
4. 必要な環境変数を `.env` に設定
5. DuckDB スキーマ初期化

具体例:

```bash
git clone <repo-url>
cd <repo-dir>

python -m venv .venv
source .venv/bin/activate

pip install duckdb defusedxml

# .env を作成（上の環境変数を設定）
cp .env.example .env
# 編集してトークン等を設定

# スキーマ初期化（Python REPL またはスクリプト）
python - <<'PY'
from kabusys.data import schema
from kabusys.config import settings
# settings.duckdb_path は環境変数を参照している
conn = schema.init_schema(settings.duckdb_path)
print("DuckDB initialized:", settings.duckdb_path)
PY
```

監査ログ専用 DB の初期化:

```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要ユースケース・サンプル）

以下は代表的な利用例です。実際はアプリのエントリポイントやジョブスケジューラ（cron / Airflow 等）から呼び出します。

- DuckDB スキーマの初期化

```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
```

- 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from kabusys.config import settings
from datetime import date

conn = schema.get_connection(settings.duckdb_path)  # 既存 DB に接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブを実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出で使う既知の銘柄コード集合（例: set of "7203"）
known_codes = {"7203", "6758", ...}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # ソースごとの新規保存数
```

- ファクター計算（研究用）

```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
target = date(2024, 1, 4)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 将来リターン計算（IC 評価用）
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

# ある factor カラム（例: mom_1m）と fwd_1d の IC を計算
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")

# カラム群の統計サマリ
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])

# Z スコア正規化
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- J-Quants API から直接データを取って保存

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from kabusys.config import settings
from datetime import date

conn = schema.get_connection(settings.duckdb_path)
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

---

## 主要 API（抜粋）

- kabusys.config.settings — 環境設定アクセサ
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL 実行（戻り: ETLResult）
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.quality.run_all_checks — 品質チェック実行
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.stats.zscore_normalize — 正規化ユーティリティ
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化

---

## ディレクトリ構成

リポジトリの主なファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集と保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — 統計ユーティリティ（zscore 等）
    - pipeline.py            — ETL パイプライン（差分取得/日次 ETL）
    - features.py            — 特徴量公開インターフェース
    - calendar_management.py — カレンダー管理・更新ジョブ
    - audit.py               — 監査ログ初期化
    - quality.py             — データ品質チェック
    - etl.py                 — ETL ユーティリティの公開
  - research/
    - __init__.py
    - feature_exploration.py — forward returns / IC / factor summary
    - factor_research.py     — momentum / volatility / value 計算
  - strategy/                — 戦略関連（パッケージ用プレースホルダ）
  - execution/               — 発注/執行関連（パッケージ用プレースホルダ）
  - monitoring/              — 監視 / メトリクス（プレースホルダ）

---

## 開発上の注意・設計メモ

- .env の自動読込はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から行われます。テストなどで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限（120 req/min）を守るため固定間隔レートリミティングを実装しています。大量取得時はレートやバックオフ挙動に注意してください。
- DuckDB の INSERT は ON CONFLICT 句で冪等性を担保していますが、外部からデータを直接挿入する場合は重複や制約違反の可能性に注意してください。
- ニュース収集では SSRF・XML Bomb・gzip サイズ制限など複数の防御策を実装済みです。RSS の多様な形式に対する堅牢性を重視しています。
- 監査ログは削除しない前提で設計されており、全てのタイムスタンプは UTC を使う想定です。

---

## 貢献 / 拡張案

- kabuステーションとの発注連携（execution モジュールの拡張）
- Slack / モニタリング統合（monitoring モジュールの実装）
- モデル学習パイプライン（特徴量 → 学習 → スコア保存）
- ETL の並列化・スケジューリング向け改善（Airflow / Prefect 等の導入）

---

必要な追加ドキュメント（例: .env.example、データベース移行手順、運用 Runbook 等）を用意することで導入がスムーズになります。README に追記したい項目や、サンプルスクリプトの追加希望があれば教えてください。