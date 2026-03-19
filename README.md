KabuSys — 日本株自動売買プラットフォーム (README)
=================================

概要
----
KabuSys は日本株向けのデータプラットフォームと戦略エンジンを備えた自動売買システムのコアライブラリです。  
主に以下機能を提供します。

- J-Quants API からの市場データ取得と DuckDB への永続化（冪等保存）
- 市場データの品質チェック・差分 ETL（バックフィル対応）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量の正規化・合成（features テーブル生成）
- シグナル生成（最終スコア計算、BUY/SELL 生成、エグジット判定）
- RSS によるニュース収集と銘柄紐付け（raw_news / news_symbols）
- マーケットカレンダー管理・営業日ユーティリティ
- 監査（audit）と実行レイヤー用のスキーマ定義（orders / executions / positions 等）

設計上の特徴
- API 呼び出しはレートリミット・リトライ・トークン自動更新に対応
- DB への保存は冪等（ON CONFLICT / upsert）で二重書き込みを防止
- ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ使用）
- RSS 収集は SSRF / XML Bomb 対策等の安全対策を実装

機能一覧
--------
主要な機能（モジュール）と役割の要約：

- kabusys.config: 環境変数管理（.env 自動読み込み、必須設定の検証）
- kabusys.data.jquants_client: J-Quants API クライアント（ページネーション、保存ユーティリティ）
- kabusys.data.schema: DuckDB のスキーマ定義と初期化
- kabusys.data.pipeline: 差分 ETL（prices / financials / calendar）と日次 ETL エントリ
- kabusys.data.news_collector: RSS 取得・正規化・DB 保存・銘柄抽出
- kabusys.data.calendar_management: 営業日判定・next/prev_trading_day 等ユーティリティ
- kabusys.data.audit: 発注〜約定の監査テーブル定義
- kabusys.data.stats: Z スコア正規化等の統計ユーティリティ
- kabusys.research: 研究用のファクター計算・特徴量解析ユーティリティ（IC, forward returns 等）
- kabusys.strategy.feature_engineering: 生ファクターの合成・正規化 → features テーブル生成
- kabusys.strategy.signal_generator: features / ai_scores を統合して BUY/SELL シグナル生成
- kabusys.execution: （発注層のプレースホルダー。実装は execution 層で行う想定）

セットアップ手順
----------------
前提
- Python 3.10 以上（コード中での型ヒントや | 型を使用しているため）
- DuckDB を使用（パッケージ duckdb が必要）
- defusedxml（RSS パースの安全化）など

インストール（開発環境）
1. 仮想環境作成（推奨）:
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2. 必要パッケージのインストール（例）:
   pip install duckdb defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を提供する想定です。
   pip install -e . でパッケージとしてインストールできるようにしておくと便利です。

環境変数
- .env 自動読み込み:
  プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある .env / .env.local が自動で読み込まれます（テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
- 必須環境変数（kabusys.config.Settings で参照）
  - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（必須）
  - KABU_API_PASSWORD — kabu ステーション API パスワード（発注実装時に使用）
  - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知を使う場合）
  - SLACK_CHANNEL_ID — Slack チャンネル ID（通知を使う場合）

- 任意・デフォルト
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

基本的な使い方（クイックスタート）
-------------------------------

1) スキーマ初期化（DuckDB を作成）
- Python REPL やスクリプトで：
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

  ":memory:" を渡すとインメモリ DB になります。

2) 日次 ETL 実行（市場データの差分取得と保存）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())  # ETL の結果サマリ

3) 特徴量構築（features テーブルの作成）
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date.today())
  print(f"features upserted: {n}")

4) シグナル生成（signals テーブルへ書き込み）
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, date.today())
  print(f"signals written: {total}")

  - 重みや閾値をカスタマイズする場合は generate_signals(..., threshold=0.65, weights={"momentum": 0.5, ...})

5) ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection
  # known_codes を渡すと記事と銘柄の紐付けを自動処理する
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)

主要な API（短い説明）
- init_schema(db_path) -> DuckDB 接続を返す（初期化済み）
- get_connection(db_path) -> 既存 DB へ接続（スキーマ初期化はしない）
- run_daily_etl(conn, target_date, ...) -> ETLResult（品質チェック含む）
- build_features(conn, target_date) -> upsert した銘柄数
- generate_signals(conn, target_date, threshold=None, weights=None) -> シグナル件数
- run_news_collection(conn, sources, known_codes) -> {source: saved_count}

ディレクトリ構成（要約）
----------------------
主要なソースは src/kabusys/ 以下に配置されています。重要モジュールを抜粋すると:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント / 保存ユーティリティ
    - news_collector.py           — RSS 収集・前処理・保存
    - schema.py                   — DuckDB スキーマ定義・init_schema
    - stats.py                    — zscore_normalize 等の統計ユーティリティ
    - pipeline.py                 — 差分 ETL / 日次 ETL パイプライン
    - calendar_management.py      — 営業日ロジック / カレンダー更新ジョブ
    - audit.py                    — 監査ログ用スキーマ
    - features.py                 — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py          — Momentum/Volatility/Value の計算
    - feature_exploration.py      — IC / forward returns / summary 等の研究用ユーティリティ
  - strategy/
    - __init__.py
    - feature_engineering.py      — ファクター正規化・features テーブル作成
    - signal_generator.py         — final_score 計算・BUY/SELL 生成
  - execution/                     — 発注・実行層（雛形）
  - monitoring/                    — 監視 / メトリクス（雛形）

注意事項・運用上のヒント
---------------------
- テスト時・CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを無効にできます。
- J-Quants API の呼び出しはレート制限（120 req/min）を守るためスロットリングされています。大量の銘柄フルバックフィルを行う場合は時間がかかります。
- features / signals の生成は target_date 時点のデータのみを使う設計です。将来データに依存する処理は避けてください（ルックアヘッドバイアス回避）。
- RSS 収集は外部 URL を扱うため SSRF 対策やレスポンスサイズ制限が組み込まれています。外部フィードを追加する際は信頼できるソースを指定してください。

貢献・ライセンス
----------------
このリポジトリの README にはライセンス情報が含まれていません。実際の利用・配布前にライセンスや運用ルールを必ず確認してください。バグ修正・機能提案は Pull Request / Issue を通じて行ってください（リポジトリ上の CONTRIBUTING.md がある場合はそちらに従ってください）。

付録: よく使うコードスニペット
---------------------------
DB 初期化 -> ETL -> 特徴量 -> シグナル生成の簡単な一連処理例:

from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

conn = init_schema("data/kabusys.duckdb")
etl_res = run_daily_etl(conn, target_date=date.today())
print(etl_res.to_dict())

build_count = build_features(conn, date.today())
print("features:", build_count)

signal_count = generate_signals(conn, date.today())
print("signals:", signal_count)

以上。README の内容や例について追加の要望（例: CI 用手順、運用マニュアル、docker 化など）があれば教えてください。