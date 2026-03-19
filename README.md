# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータレイヤに採用し、J-Quants API からのデータ取得、ETL、品質チェック、特徴量計算、ニュース収集、監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を持つ Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得するクライアント
- DuckDB に対するスキーマ定義と初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース（RSS）収集と記事→銘柄紐付け
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数 / 設定管理（.env 自動読み込み機構）

設計方針としては「本番口座への直接操作を行わないデータ収集／研究部分」と「監査・発注周りを分離した設計」を取っており、DuckDB を用いてローカルで高速かつ冪等的に運用できるようになっています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - fetch / save の冪等保存（DuckDB への ON CONFLICT 更新）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- data/schema
  - DuckDB のスキーマ（Raw / Processed / Feature / Execution / Audit）を定義・初期化
  - init_schema, get_connection など
- data/pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- data/news_collector
  - RSS 取得、HTML の簡易前処理、記事の冪等保存、銘柄コード抽出（4桁コード）
  - SSRF 対策、受信サイズ制限、gzip 解凍ガードなどの安全設計
- data/quality
  - 欠損・スパイク・重複・日付不整合のチェック
  - run_all_checks による一括実行
- research/factor_research, research/feature_exploration
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- data/audit
  - シグナル・発注・約定の監査テーブル定義と初期化ユーティリティ
- config
  - .env / 環境変数の自動ロード（プロジェクトルート検出）、Settings クラス経由でアクセス

---

## 前提 / 必要環境

- Python 3.10+
  - コード中に型ヒントで `X | None`（PEP 604）が使用されています
- 必須 Python パッケージ（最低限）
  - duckdb
  - defusedxml

（実際の運用では logging 設定や Slack 連携等で追加パッケージを導入する場合があります）

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. インストール（編集可能モード）
   - pip install -e .

5. 環境変数（.env）を作成
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効）。
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (省略可)
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb  (省略可)
     - SQLITE_PATH=data/monitoring.db    (省略可)
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO|DEBUG|... (デフォルト: INFO)

6. DuckDB スキーマ初期化例（Python）
   - 以下の例スクリプトを実行して DB とテーブルを作成します。

   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   # settings.duckdb_path は .env または環境変数から取得されます
   conn = schema.init_schema(settings.duckdb_path)
   ```

   - 監査ログのみ別 DB に分けたい場合:
   ```python
   from kabusys.data import audit
   conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要ユースケース）

以下は最小限の使い方例です。実運用ではログ設定やエラーハンドリング、ジョブスケジューラ（cron / Airflow / systemd timer など）と組み合わせてください。

1. 日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data import pipeline, schema
from kabusys.config import settings

# DB 初期化済み（init_schema を既に実行している前提）
conn = schema.get_connection(settings.duckdb_path)

# 日次 ETL を実行（ターゲット日を指定または None=今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())

# ETLResult を確認
print(result.to_dict())
if result.has_errors or result.has_quality_errors:
    # アラートやログ送信などの処理
    pass
```

2. ニュース収集ジョブ（RSS）を実行する

```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)

# known_codes は銘柄候補のセット（例: all listed codes を事前に取得）
known_codes = {"7203", "6758", "9984"}

results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

3. 研究用ファクター計算（例：モメンタム、IC）

```python
from datetime import date
from kabusys.data import schema
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

conn = schema.get_connection("data/kabusys.duckdb")
t = date(2024, 1, 15)

momentum = calc_momentum(conn, t)         # list[dict]
forward = calc_forward_returns(conn, t)   # list[dict]

# Spearman ランク相関（IC）計算の例
ic_val = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic_val)

# Z スコア正規化
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
summary = factor_summary(normalized, ["mom_1m", "mom_3m", "mom_6m"])
print(summary)
```

4. J-Quants API からデータを直接フェッチして保存する（テストやバックフィル）

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from kabusys.config import settings
from datetime import date

conn = schema.get_connection(settings.duckdb_path)
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = jq.save_daily_quotes(conn, records)
print("saved", saved)
```

---

## 設定（重要な環境変数）

主要な設定は Settings クラス経由でアクセスします（kabusys.config.settings）。主に以下を設定してください。

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API のパスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須): Slack 通知先チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意): ログレベル（DEBUG/INFO/...）

.env の読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 開発・デバッグのヒント

- settings.is_live / is_paper / is_dev を使って環境ごとに挙動を切り替えられます。
- J-Quants クライアントは内部でレート制御とリトライを行います。API 呼び出しの単位や並列実行には注意してください。
- news_collector は SSRF・XML 全般攻撃対策を施しています。テスト時は _urlopen をモック可能です。
- DuckDB のスキーマ初期化は冪等です。init_schema を複数回呼んでも安全に動作します。
- 品質チェック（data.quality）では重大度（"error"/"warning"）で分けて報告します。ETL の継続判断は呼び出し側で行ってください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - etl.py
    - quality.py
  - research/
    - __init__.py
    - feature_exploration.py
    - factor_research.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各モジュールの責務：
- data: データ取得・保存・ETL・品質チェック・スキーマ定義
- research: ファクター計算・研究ユーティリティ
- execution: 発注・ブローカ連携（発注実装は将来的に）
- monitoring: 監視 / メトリクス（骨組み）

---

## ライセンス / コントリビュート

本 README はコードベースの説明を目的としています。実際のライセンス・コントリビュート方法はリポジトリの LICENSE / CONTRIBUTING ファイルに従ってください。

---

必要であれば、README に以下を追加できます：
- 実際の requirements.txt（推奨バージョン）
- CI / GitHub Actions の設定例
- デプロイ / 運用手順（cron, systemd, Kubernetes 等）
- Slack などへの通知サンプルコード

どの追加情報が欲しいか教えてください。