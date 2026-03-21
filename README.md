# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants からのデータ取得、DuckDB への永続化、リサーチ用ファクター計算、特徴量の構築、シグナル生成、ニュース収集などを一貫してサポートします。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（サンプルコード）
- 環境変数（.env）
- ディレクトリ構成

---

プロジェクト概要
- 目的: J-Quants 等の外部データソースから日本株データを収集・保存し、リサーチ→特徴量→シグナル→発注という流れの基盤機能を提供する。
- 設計方針:
  - DuckDB を単一のローカル DB として使用（インメモリやファイルベース可）。
  - 取得は冪等（ON CONFLICT / upsert）で行い、後出し修正を吸収するためのバックフィルをサポート。
  - ルックアヘッドバイアスを防ぐため、各処理は target_date 時点のデータのみを参照。
  - 外部発注層（ブローカー API）への依存を最低限にしてテスト可能性を高める。

---

機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（無効化可）
  - 必須環境変数の検証
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント（ページネーション・自動トークン更新・レート制限・リトライ）
  - 株価（日足）、財務データ、JPX カレンダーの取得と DuckDB への保存
- スキーマ管理（kabusys.data.schema）
  - DuckDB のテーブルDDL定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) で初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 日次差分 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、重複排除、記事ID生成（URL 正規化 + SHA256）
  - SSRF 対策、gzip 制限、XML 安全パーサ（defusedxml）
  - raw_news / news_symbols への冪等保存
- 研究用ファクター（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - z-score 正規化ユーティリティ
- 特徴量構築（kabusys.strategy.feature_engineering）
  - research が生成した raw factor を正規化・フィルタ・保存（features テーブル）する build_features
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成して signals テーブルに保存する generate_signals
  - Bear レジーム判定、エグジット（ストップロス等）ロジックを含む
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / next/prev_trading_day / calendar 更新ジョブ
- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定のトレーサビリティ用スキーマ定義（order_request_id 等の冪等キー）

---

セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型合成などを利用）
- Git クローンができる環境

1. リポジトリをクローン
   git clone <this-repo-url>
   cd <repo>

2. 仮想環境（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install --upgrade pip
   pip install duckdb defusedxml

   （将来的に pyproject.toml / requirements.txt があれば pip install -e . などを使用）

4. DuckDB スキーマ初期化
   Python REPL やスクリプトで以下を実行して DB を作成:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # デフォルトパスは .env で設定可能

5. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml を基準）に .env または .env.local を置いてください。
   自動読み込みはデフォルトで有効（テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携時）
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: 通知先チャンネル ID

- 任意 / デフォルトあり
  - KABU_API_BASE_URL: kabu API のベースURL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

サンプル .env.example
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

簡単な使い方（Python スニペット）

1) DB を初期化する
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL を実行する（J-Quants トークンは環境変数で自動取得）
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定することも可
print(result.to_dict())

3) 特徴量を構築する（target_date の features を作る）
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, date(2025, 1, 31))
print(f"features updated: {count}")

4) シグナルを生成する
from kabusys.strategy import generate_signals
from datetime import date
n_signals = generate_signals(conn, date(2025, 1, 31), threshold=0.6)
print(f"signals generated: {n_signals}")

5) ニュース収集ジョブを実行する
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 既知銘柄集合
res = run_news_collection(conn, known_codes=known_codes)
print(res)

6) カレンダー更新ジョブ（夜間バッチ）
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar records saved: {saved}")

ログや例外は logger により出力されるので、実行環境で適宜 logging.basicConfig(...) を設定してください。

---

注意点 / 補足
- 自動 .env ロードは config._find_project_root() により、ソースファイルの親階層で .git または pyproject.toml を探して行われます。テストで自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants クライアントはレート制限（120 req/min）とリトライ戦略、401 の自動リフレッシュに対応しています。
- news_collector は SSRF、gzip bomb、XML Bomb 対策を組み込んでいます（defusedxml を使用）。
- DuckDB 初期化時に親ディレクトリが存在しない場合、自動で作成します。
- 実際の発注（broker 連携）部分は本リポジトリの実装方針に沿って発注層を分離しており、kabu ステーション等の連携は別途実装する必要があります。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント + 保存関数
    - schema.py                # DuckDB スキーマ定義 & init_schema
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - news_collector.py        # RSS 取得・前処理・保存
    - calendar_management.py   # カレンダー管理 / 営業日判定
    - audit.py                 # 監査ログスキーマ
    - features.py              # zscore の re-export
    - stats.py                 # 統計ユーティリティ（zscore_normalize）
    - quality.py (参照実装想定) # 品質チェック（pipeline から参照）
  - research/
    - __init__.py
    - factor_research.py       # Momentum/Volatility/Value の計算
    - feature_exploration.py   # IC/forward returns/summary
  - strategy/
    - __init__.py
    - feature_engineering.py   # build_features
    - signal_generator.py      # generate_signals
  - execution/                 # 発注関連（スケルトン）
  - monitoring/                # 監視・メトリクス（スケルトン / __all__ でエクスポート）
  - その他ユーティリティ

（README に載せた以外の内部関数や設計ドキュメント（StrategyModel.md、DataPlatform.md 等）を参照して詳細実装を確認してください）

---

貢献 / 開発メモ
- テストを記述する際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、環境依存を排除してください。
- jquants_client の HTTP 呼び出しはモックしやすい設計（id_token 注入・モジュールレベルのトークンキャッシュ）になっています。
- news_collector のネットワーク部分は _urlopen をモックすることで外部アクセスを防げます。

---

ライセンス・著者
- （ここにライセンス情報・著者情報を記載してください）

README は以上です。必要に応じて「使用例の拡張」「CI / デプロイ手順」「設定のテンプレート」などを追加できます。どの情報を詳しく書き加えたいか教えてください。