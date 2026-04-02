# KabuSys

日本株向けのデータプラットフォーム & 自動売買（リサーチ／ETL／監視／監査）ライブラリです。  
本リポジトリはデータ取得（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算、ETLパイプライン、監査ログスキーマなどを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数（.env）
- ディレクトリ構成
- 注意事項 / 運用メモ

---

## プロジェクト概要

KabuSys は以下の要件を満たすことを目的としたライブラリです。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL
- RSS ベースのニュース収集と前処理（SSRF対策、トラッキング除去、正規化）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別・マクロ）
- 日次 ETL パイプライン、データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ファクター計算と特徴量解析ユーティリティ
- 監査ログ用の冪等なテーブル定義（signal / order_request / execution）
- 設定は環境変数（.env）で管理。パッケージ起動時に自動で .env/.env.local を読み込む仕組みあり（無効化可能）。

設計方針の一例: ルックアヘッドバイアス回避（datetime.today() の直接参照を避ける）、冪等性、外部依存（OpenAI/J-Quants）は明確に分離している点が特徴です。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存関数）
  - 市場カレンダー管理（営業日計算・calendar_update_job）
  - ニュース収集（RSS fetch / 前処理 / DB 保存）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログ初期化（監査テーブル DDL / インデックス / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai/
  - ニュース NLP（銘柄別 ai_score を ai_scores テーブルへ）
  - マクロセンチメント & 市場レジーム判定（ETF 1321 の MA200 と LLM を組合せ）
- research/
  - ファクタ計算（momentum, value, volatility 等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- config.py
  - 環境変数読み込み・検証（自動 .env ロード、必須変数チェック）
- audit / 実行履歴などの監査トレース

---

## セットアップ手順

前提
- Python 3.10+（typing | 区切り的に 3.10+ を想定）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトが pyproject/requirements を提供している場合はそれに従ってください）
   - 開発用に `pip install -e .` でパッケージをインストールできる想定

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置することで自動読み込みされます（config.py がプロジェクトルートを探索）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. データベース準備
   - デフォルト DuckDB パス: data/kabusys.duckdb（settings.duckdb_path）
   - 監査ログ用 SQLite/別 DB は設定可能（settings.sqlite_path など）

---

## 必須 / 主要環境変数（.env に記載する例）

必須（実行時に _require によってチェックされる）
- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
- KABU_API_PASSWORD=<kabu_api_password>          （kabuステーション連携用）
- SLACK_BOT_TOKEN=<slack_bot_token>
- SLACK_CHANNEL_ID=<slack_channel_id>
- OPENAI_API_KEY=<openai_api_key>                （AI モジュール実行時に必要）

オプション（デフォルト値あり）
- KABUSYS_ENV=development|paper_trading|live       （デフォルト: development）
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  （自動 .env 読み込みを無効にする）

.env の例:
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡易サンプル）

以下はライブラリ内部 API を直接呼ぶ簡単な例です。実運用では適切なログ設定・エラーハンドリング・ジョブスケジューラ（cron / systemd timer / Airflow 等）を組み合わせてください。

- 日次 ETL を実行する（prices / financials / calendar の差分取得と品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written} scores")
```

- 市場レジーム判定を行う（ETF 1321 MA200 + マクロ LLM）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル(signal_events, order_requests, executions等)が作成されます
```

- 研究用ユーティリティ（例: momentum 計算）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとの辞書リスト
```

---

## ディレクトリ構成（主なファイル）

（src/kabusys 配下）

- __init__.py (version=0.1.0)
- config.py
- ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント（銘柄別）
  - regime_detector.py     — マクロ + MA200 による市場レジーム判定
- data/
  - __init__.py
  - pipeline.py            — ETL パイプライン / run_daily_etl 等
  - etl.py                 — ETL 結果型の再エクスポート
  - jquants_client.py      — J-Quants API クライアント & 保存関数
  - news_collector.py      — RSS 取得・前処理・保存
  - calendar_management.py — 市場カレンダー管理 / 営業日判定
  - quality.py             — データ品質チェック
  - audit.py               — 監査ログ DDL / init_audit_db
  - stats.py               — zscore_normalize 等
- research/
  - __init__.py
  - factor_research.py     — momentum / value / volatility
  - feature_exploration.py — forward returns / IC / factor summary
- research/*, ai/*, data/* に随所のドキュメント文字列あり

---

## 注意事項 / 運用メモ

- セキュリティ
  - news_collector は SSRF 対策やコンテンツ長制限、defusedxml の利用などを行っていますが、本番運用ではネットワーク制御（アウトバウンド許可先）や追加の監視を推奨します。
- OpenAI 呼び出し
  - news_nlp / regime_detector は OpenAI API（gpt-4o-mini）を使用します。API 呼び出しはリトライ戦略や 5xx/429 の処理を含みますが、API キーの管理やコスト制御はユーザ側で行ってください。
- Look-ahead Bias
  - 多くの処理はルックアヘッドバイアスを避けるように設計されています（target_date パラメタ、DB クエリの排他条件など）。バックテストで使用する際は取得時点の fetched_at 等に注意してください。
- DB 互換性
  - DuckDB のバージョン差異（executemany の仕様、配列バインドの違い等）に注意して下さい。コード内にも回避策がいくつか実装されています。
- ローカル環境でのテスト
  - .env をテスト用トークンやモックエンドポイントで設定して実行してください。
- 自動 .env ロード
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml を起点）を探索して `.env` / `.env.local` を自動読込します。テストでこれを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

必要があれば次の内容も追加で作成できます:
- .env.example（テンプレート）
- requirements.txt / pyproject.toml 例
- より詳細な運用手順（systemd / cron / Airflow 連携例）
- ユニットテストの書き方とモック対象一覧

ご希望があれば、README の別フォーマット（英語版・短縮版）や追加のセットアップスクリプトも作成します。