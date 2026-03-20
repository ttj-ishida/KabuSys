# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants API からのデータ取得、DuckDB ベースのデータスキーマ、ETL パイプライン、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理などを提供します。

---

## プロジェクト概要

KabuSys は以下のレイヤーを想定したモジュール群を提供するパッケージです。

- Data layer (DuckDB)：生データ / 処理済みデータ / 特徴量 / 実行ログを格納するスキーマ定義とIO
- ETL：J-Quants API からの差分取得・保存を行う日次 ETL パイプライン
- Data processing：特徴量計算（momentum / volatility / value 等）、Z スコア正規化等
- Strategy：特徴量と AI スコアを統合してシグナル（BUY/SELL）を生成
- News：RSS 収集・前処理・記事→銘柄紐付け
- Calendar：JPX のマーケットカレンダー管理（営業日判定 / next/prev 等）
- Audit / Execution（監査・発注ログのスキーマ）
- Utilities（設定管理・統計ユーティリティなど）

設計方針としては、ルックアヘッドバイアスの回避、冪等性（DB 保存の ON CONFLICT を使用）、シンプルでテストしやすいインターフェースを重視しています。

---

## 機能一覧

主な機能（抜粋）:

- DuckDB スキーマ定義と初期化（kabusys.data.schema.init_schema）
- J-Quants API クライアント（レートリミット・リトライ・トークン自動更新対応）
  - 日足 (daily quotes)、財務データ、マーケットカレンダー等の取得
  - DuckDB への冪等保存関数
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS 取得、XML 安全パース、トラッキングパラメータ除去、記事保存）
- 特徴量計算（momentum / volatility / value 等）および Z スコア正規化
- 特徴量テーブルの構築（strategy.feature_engineering.build_features）
- シグナル生成（strategy.signal_generator.generate_signals）
  - コンポーネントスコア、重み付け、Bear レジーム抑制、エグジット判断（ストップロス等）
- マーケットカレンダー管理（営業日判定・次/前営業日の取得・夜間更新ジョブ）
- 監査ログ（signal_events, order_requests, executions などのスキーマ）
- ユーティリティ：環境変数管理（.env 自動読み込み）、統計ユーティリティ（zscore_normalize）など

---

## 要件

- Python 3.10 以上（型ヒントに `X | None` などを使用しているため）
- 依存ライブラリ（最低限）:
  - duckdb
  - defusedxml
- （ネットワークアクセスが必要な機能を使う場合）J-Quants API のリフレッシュトークン等

依存関係はプロジェクトの packaging によりますが、開発環境で最小限動かすには上記をインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を用意（例）:

   bash:
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip

2. 必要パッケージのインストール（例）:

   bash:
   pip install duckdb defusedxml

   ※ プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください。
   開発インストール（プロジェクトルートに pyproject.toml がある想定）:

   bash:
   pip install -e .

3. データベースの初期化（DuckDB）:

   Python:
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

   - ":memory:" を渡すとインメモリ DB を使用できます。
   - 指定パスの親ディレクトリが存在しない場合、自動で作成されます。

---

## 環境変数（.env）

パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動的に読み込みます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

必須環境変数（Settings より）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID

オプション / デフォルト値:

- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

例（.env）:

KABUSYS .env:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡単な例）

以下は代表的なワークフローのコード例です。

1) DB 初期化

Python:
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

2) 日次 ETL 実行（J-Quants から市場カレンダー・株価・財務を取得）

Python:
from kabusys.data.pipeline import run_daily_etl
from datetime import date
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())

3) 特徴量の構築（target_date に対して features テーブルを作成）

Python:
from kabusys.strategy import build_features
from datetime import date
n = build_features(conn, target_date=date.today())
print(f"features written: {n}")

4) シグナル生成（features + ai_scores をもとに signals を作る）

Python:
from kabusys.strategy import generate_signals
from datetime import date
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")

5) ニュース収集（RSS → raw_news、news_symbols への紐付け）

Python:
from kabusys.data.news_collector import run_news_collection
# known_codes は既知の銘柄コード集合（例: データベースから取得）
known_codes = {"7203", "6758", "8306", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)

補足:
- J-Quants API を使う関数は内部でトークンを自動取得/リフレッシュします（get_id_token）。
- ETL / ニュース収集 / カレンダー更新は例外を局所的に処理するため、ログを確認してください。
- 実運用時は cron / ジョブスケジューラで上記処理を定期実行してください。

---

## ディレクトリ構成

src 配下の主要モジュール一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存ロジック
    - news_collector.py       — RSS 取得・前処理・DB 保存
    - schema.py               — DuckDB スキーマ定義と初期化
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — マーケットカレンダー管理
    - audit.py                — 監査ログ用スキーマ
    - features.py             — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/volatility/value）
    - feature_exploration.py  — リサーチ用ユーティリティ（IC, forward returns, summary）
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル構築（正規化・フィルタ）
    - signal_generator.py     — シグナル生成ロジック（BUY/SELL）
  - execution/                — (発注/実行層の実装場所)
  - monitoring/               — (監視・アラート等の実装場所)

主要な DB テーブル（schema.py に定義）:
- raw_prices, raw_financials, raw_news, raw_executions
- prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- features, ai_scores
- signals, signal_queue, orders, trades, positions, portfolio_performance
- audit 用テーブル: signal_events, order_requests, executions

---

## 開発・テスト（簡易ガイド）

- ローカルでの検証には DuckDB のインメモリ DB を使うと便利:
  conn = schema.init_schema(":memory:")
- network 系の関数（J-Quants / RSS）をテストする際は、各モジュールの HTTP 呼び出し箇所（urllib）をモックしてください。
- news_collector._urlopen などはテスト用に差し替えやすい設計です。

---

## 参考・補足

- 環境変数の自動ロードはプロジェクトルートを探して `.env` / `.env.local` を読み込みます。テストや CI で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 各モジュールの docstring に設計方針・アルゴリズムの概要が記載されています。実装詳細は該当ファイル内のコメントをご参照ください。
- 本 README はコードベースから抽出した内容を要約しています。より詳細な仕様（StrategyModel.md / DataPlatform.md 等）がある想定です。

---

必要であれば、README に以下を追加できます:
- 具体的な .env.example ファイルのテンプレート
- より詳細な使用例（ワークフロー：ETL → build_features → generate_signals → execution 連携）
- CI / テストのセットアップ手順

追加希望があれば教えてください。