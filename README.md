# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データ収集（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログなどのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群から構成されたシステムライブラリです。

- J‑Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB ベースのスキーマ定義・初期化
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（複数コンポーネントスコアの統合、BUY/SELL の決定）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策等を考慮）
- 監査ログ（シグナル→発注→約定のトレース用テーブル）

設計方針として「ルックアヘッドバイアスの排除」「冪等性（idempotency）」「外部依存を最小化（DuckDB を中心）」が重視されています。

---

## 主な機能一覧

- data/
  - jquants_client: J‑Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
  - schema: DuckDB スキーマ定義と init_schema()
  - pipeline: 差分 ETL（run_daily_etl 等）
  - news_collector: RSS 取得 → raw_news 保存、銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats, features: 共通統計ユーティリティ（zscore_normalize 等）
- research/
  - factor_research: momentum/volatility/value の計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリ
- strategy/
  - feature_engineering.build_features: features テーブルの作成・UPSERT
  - signal_generator.generate_signals: features + ai_scores を統合して signals を生成
- execution/（発注・ブローカー連携層のためのプレースホルダ）
- monitoring/（監視・ログ収集等のためのプレースホルダ）
- audit: 監査ログ用テーブル（signal_events, order_requests, executions）

---

## 前提要件（セットアップ）

推奨環境:
- Python 3.9+
- 必要パッケージ（例）:
  - duckdb
  - defusedxml
  - （標準ライブラリのみで動作する部分が多いですが、HTTP の利用や XML パースに上記が必要です）

例（仮の requirements）:
pip install duckdb defusedxml

プロジェクトを editable install:
pip install -e .

（プロジェクトに requirements.txt や pyproject.toml があればそちらを利用してください）

---

## 環境変数 / 設定

自動的にプロジェクトルートの `.env` / `.env.local` をロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。

必須（Settings.require で要求されるもの）
- JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabu ステーション API 用パスワード（発注実装時）
- SLACK_BOT_TOKEN : Slack 通知用トークン（通知を行う場合）
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

任意（デフォルトあり）
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUS_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 sqlite のパス（デフォルト: data/monitoring.db）

.env の例（.env.example を参考に作成してください）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（簡易）

1. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存ライブラリをインストール
   pip install duckdb defusedxml

3. 環境変数を準備
   - プロジェクトルートに `.env` を作成（上記参照）
   - または環境変数として export してください

4. DuckDB スキーマを初期化
   Python REPL またはスクリプトで:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

---

## 使い方（主な API と例）

以下は最小限の例スニペットです。適宜ロギング設定や例外処理を追加してください。

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL（J‑Quants から差分取得して保存）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を省略すると本日が対象
  print(result.to_dict())

- 特徴量の構築（features テーブルへ）
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date(2025, 1, 10))
  print(f"upserted features: {n}")

- シグナル生成（signals テーブルへ）
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2025, 1, 10))
  print(f"signals written: {total}")

- ニュース収集ジョブ（RSS 取得→raw_news 保存→銘柄紐付け）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 例えば有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}

- J‑Quants の ID トークン取得（必要に応じて）
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # JQUANTS_REFRESH_TOKEN が環境変数で必要

注意:
- 各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。
- 多くの操作（features の作成、signals 生成、ETL）は「日付単位での置換（冪等）」の実装になっており、複数回実行しても整合性が保たれるように設計されています。

---

## ディレクトリ構成

ソース木（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - stats.py
  - features.py
  - calendar_management.py
  - audit.py
  - pipeline.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
  - feature_engineering.py
  - signal_generator.py
- execution/
  - __init__.py
- monitoring/  # プレースホルダ（実装があれば追加）
- その他: ドキュメント（DataSchema.md、StrategyModel.md 等）は参照設計書として想定

各モジュールの簡単な説明
- config.py: 環境変数読み込み・Settings の定義（自動 .env ロード機能あり）
- data/schema.py: DuckDB の DDL 定義と init_schema()
- data/jquants_client.py: J‑Quants API の取得・保存ユーティリティ（fetch_*/save_*）
- data/pipeline.py: ETL のオーケストレーション（run_daily_etl 等）
- research/factor_research.py: momentum/volatility/value ファクター計算
- strategy/feature_engineering.py: features テーブル作成（正規化・ユニバースフィルタ）
- strategy/signal_generator.py: final_score を計算して BUY/SELL シグナル生成
- data/news_collector.py: RSS フィードの取得 / 前処理 / raw_news への保存 / 銘柄抽出

---

## 運用上の注意

- J‑Quants API はレート制限やレスポンスの変動があるため、jquants_client は内部でレート制御とリトライを行います。API 利用時は適切にログを監視してください。
- env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探す）を基準に行います。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルパスの親ディレクトリが存在しない場合、init_schema() が自動で作成します。
- ニュース収集では SSRF/ZIP bomb 対策・XML ハンドリングに注意が払われていますが、外部フィードの取り扱いは十分に検証してください。
- 本ライブラリ自体は発注（execution）層と分離設計になっており、実際のブローカー API 連携を行う場合は execution 層・監査（audit）を適切に組み合わせて実装してください。

---

## テスト / 開発ヒント

- テスト実行時は環境変数読み込みを抑止するために:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB をインメモリで使うと高速に単体テスト可能:
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")

---

この README はコードベースに含まれる設計・実装コメントを元にまとめたものです。より詳細な設計仕様（DataPlatform.md / StrategyModel.md / Research docs 等）がプロジェクトに含まれている想定なので、運用前にそちらもご参照ください。