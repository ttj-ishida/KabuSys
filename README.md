# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
マーケットデータの取得・ETL、特徴量計算、シグナル生成、ニュース収集、監査ログなどを包含するモジュール群です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API など外部データソースから株価・財務・カレンダー・ニュースを取得し DuckDB に保存する ETLパイプライン
- 研究で作成したファクターを用いた特徴量生成（正規化・フィルタ）
- 正規化済み特徴量と AI スコアを統合した売買シグナル生成（BUY / SELL）
- ニュース RSS の収集と記事→銘柄の紐付け
- DuckDB ベースのスキーマ・監査ログ構造によりデータ品質とトレーサビリティを担保

設計上のポイント：
- ルックアヘッドバイアスに配慮し「target_date 時点のみ」のデータで処理
- DuckDB を中心に冪等性（ON CONFLICT / INSERT ... DO UPDATE 等）を重視
- 外部ライブラリ依存は最小限（duckdb / defusedxml 等）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ・トークン自動更新）
  - pipeline: 日次 ETL（市場カレンダー・株価・財務）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS 収集、テキスト前処理、記事保存、銘柄抽出
  - calendar_management: 営業日判定・next/prev トレード日取得等
  - stats: Zスコア正規化など統計ユーティリティ
- research/
  - factor_research: momentum, volatility, value などファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering: 生ファクターの正規化・ユニバースフィルタ・features テーブルへの保存
  - signal_generator: features と ai_scores を統合して final_score を計算、BUY/SELL の signals 保存
- execution/, monitoring/: 発注・監視系の雛形（本リポジトリではモジュールの骨組みを含む）
- config: 環境変数読み込み・設定管理（.env/.env.local 自動読み込み、必要環境変数チェック）

---

## 前提条件

- Python 3.10 以上（型注釈に | を使用）
- DuckDB（Python パッケージ）
- defusedxml（RSS パーシングの安全対策）
- ネットワークアクセス（J-Quants API、RSS フィード等）

推奨パッケージ（例）:
- duckdb
- defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンしパッケージをインストール
```bash
git clone <repo-url>
cd <repo>
pip install -e .
```
（編集可能インストール。pyproject.toml / setup.py がある想定）

2. 必要パッケージをインストール（手動）
```bash
pip install duckdb defusedxml
```

3. 環境変数を設定（.env または OS 環境変数）
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config._find_project_root が .git や pyproject.toml を基準に探索します）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（稼働に必要）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード
- SLACK_BOT_TOKEN : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID : Slack チャネル ID

オプション:
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : モニタリング DB（デフォルト data/monitoring.db）

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=supersecret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期化（データベーススキーマ）

DuckDB に初期スキーマを作成するには data.schema.init_schema を使用します。  
デフォルトの duckdb パスは settings.duckdb_path で設定されています（環境変数 DUCKDB_PATH で上書き可）。

サンプル:
```python
from kabusys.config import settings
from kabusys.data import schema

# settings.duckdb_path は Path オブジェクトを返します（デフォルト data/kabusys.duckdb）
conn = schema.init_schema(settings.duckdb_path)
```

この関数はテーブル作成を冪等に行い、接続オブジェクトを返します。

---

## 使い方（代表的なワークフロー）

以下は典型的な日次処理の流れ例です。

1) DuckDB 初期化（1回）
```python
from kabusys.config import settings
from kabusys.data import schema

conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL（市場カレンダー・株価・財務の差分取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量構築（features テーブルへ書き込み）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

5) ニュース収集の実行例
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes

# known_codes は銘柄コード一覧（例: DuckDB から取得）
known_codes = {"7203", "6758", "9984"}

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

注記:
- generate_signals は ai_scores / positions / features テーブルを参照します。AIスコアを投入する処理は別途必要です（モジュール外）。
- run_daily_etl 等は内部で jquants_client を使って API にアクセスします。API トークン（JQUANTS_REFRESH_TOKEN）が必要です。

---

## 主要 API (抜粋)

- kabusys.config.settings — 設定オブジェクト（環境変数アクセス）
- kabusys.data.schema.init_schema(db_path) — スキーマ初期化
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...) — 日次 ETL
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes — 株価取得・保存
- kabusys.strategy.build_features(conn, target_date) — 特徴量構築
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights) — シグナル生成
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection — RSS 収集・保存

詳細は各モジュールの docstring を参照してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）
- __init__.py
- config.py — 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ含む）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - schema.py — DuckDB スキーマ定義と init_schema
  - stats.py — zscore_normalize 等統計ユーティリティ
  - news_collector.py — RSS 収集・前処理・DB 保存
  - calendar_management.py — 営業日判定・カレンダーバッチ
  - audit.py — 監査ログ用スキーマ（signal_events / order_requests / executions 等）
  - features.py — データ層の機能公開（zscore_normalize の re-export）
- research/
  - __init__.py
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — 将来リターン, IC, 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — features テーブル構築ロジック
  - signal_generator.py — final_score 計算・BUY/SELL 生成
- execution/ — 発注実装のための雛形（発展させる場所）
- monitoring/ — モニタリング / 監視用コード（雛形）

---

## 補足・運用上の注意

- 環境設定: 必須の環境変数が未設定だと Settings プロパティが ValueError を投げます。`.env.example` を元に .env を作成してください（リポジトリにサンプルがある想定）。
- レート制限: J-Quants API の制限（120 req/min）を respect する実装です。大量取得時は注意。
- データ品質: pipeline.run_daily_etl は品質チェックを実行できます（quality モジュールを利用）。品質問題が検出されても ETL は継続し、呼び出し元で決定を行う設計です。
- セキュリティ: news_collector は SSRF 対策や defusedxml を使った XML パースを行っていますが、公開環境での実行時はネットワーク制御とログ管理を整備してください。

---

## 貢献・開発

- バグ報告、機能提案は Issue を作成してください。
- 新機能はテスト（ユニット/統合）を追加のうえ PR を送ってください。

---

ライセンスなどの情報はリポジトリ内の LICENSE ファイルを参照してください。

---

以上が KabuSys の簡易 README です。追加で CI の設定例、運用手順（cron や Airflow でのスケジューリング例）、.env.example のテンプレートなどが必要であれば作成します。