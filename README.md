# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
DuckDB をデータストアとして用い、J-Quants API や RSS ニュースなどからデータを収集・整形し、特徴量計算・シグナル生成を行うためのモジュール群を提供します。

---

## プロジェクト概要

KabuSys は次の機能群を持つモジュール群で構成されています。

- データ取得・ETL（J-Quants からの株価・財務・市場カレンダー等）
- 生データ / 加工データ / 特徴量 / 実行（発注・約定）を分離した DuckDB スキーマ管理
- 研究用途のファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量正規化・特徴量テーブルの生成（戦略用）
- シグナル生成（最終スコア算出、BUY/SELL 判定、エグジット判定）
- RSS ニュース収集と銘柄紐付け
- カレンダー管理（営業日判定・前後営業日の計算）
- 監査ログ（発注→約定のトレーサビリティ）

設計上の特徴：
- ルックアヘッドバイアスを防ぐため「target_date 時点のデータのみ」を用いる実装
- DuckDB を用いた冪等な保存（ON CONFLICT / トランザクション利用）
- J-Quants API に対するレート制御・リトライ・自動トークンリフレッシュ
- 外部依存を最小化（標準ライブラリ中心、ただし DuckDB / defusedxml 等が必要）

---

## 機能一覧（主要機能）

- data
  - jquants_client: J-Quants API クライアント + 保存ユーティリティ（raw_prices / raw_financials / market_calendar 等）
  - schema: DuckDB スキーマ定義・初期化（raw/processed/feature/execution 層）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - news_collector: RSS フィード収集・正規化・DB 保存・銘柄関連付け
  - calendar_management: 営業日判定・次/前営業日・カレンダーバッチ更新
  - stats: Z スコア正規化など統計ユーティリティ
- research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリ
- strategy
  - feature_engineering: ファクターの正規化・features テーブルへの書き込み（日次置換）
  - signal_generator: features / ai_scores を統合して final_score を計算し signals テーブルへ登録
- config: 環境変数管理（.env 自動読み込み・必須キー検査）
- audit / execution / monitoring（監査ログ・実行関連テーブル等の定義）

---

## 前提・依存

- Python 3.10 以上（型注記に | None 等を使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセスが必要（J-Quants API、RSS ソース）
- J-Quants のリフレッシュトークンおよび各種外部サービスの認証情報

（プロジェクト配布に requirements.txt がある場合はそちらを使用してください）

---

## 環境変数（必須 / 主要）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 BOT トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

注意: Settings 内の _require 関数は未設定だと ValueError を投げます。`.env.example` を参照して `.env` を準備してください（プロジェクトに例ファイルがない場合は上記の必須変数を設定してください）。

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトをパッケージとして扱う場合）pip install -e .

3. 環境変数を準備
   - プロジェクトルートに `.env` または `.env.local` を作成し、必須キーを設定。
     例:
       JQUANTS_REFRESH_TOKEN=your_refresh_token
       KABU_API_PASSWORD=your_kabu_password
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567

   - 自動読み込みを無効化したい場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化
   - Python スクリプト/REPL で:
     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)

   - これにより `data/kabusys.duckdb`（デフォルト）が作成され、必要なテーブルがすべて作成されます。

---

## 使い方（主要な操作例）

以下は最小限の Python サンプルです。目的に応じてコマンドラインスクリプトやジョブ化してください。

1) DuckDB の初期化
   from kabusys.config import settings
   from kabusys.data.schema import init_schema
   conn = init_schema(settings.duckdb_path)

2) 日次 ETL（市場カレンダー・株価・財務の差分取得）
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())

   - id_token を直接渡して検証したい場合は get_id_token で取得して渡せます:
     from kabusys.data.jquants_client import get_id_token
     token = get_id_token()
     run_daily_etl(conn, id_token=token)

3) 特徴量のビルド（features テーブルへ日付単位で書き込み）
   from datetime import date
   from kabusys.strategy import build_features
   cnt = build_features(conn, date(2024, 1, 31))
   print(f"upserted features: {cnt}")

4) シグナル生成（signals テーブルへ日付単位で書き込み）
   from kabusys.strategy import generate_signals
   num = generate_signals(conn, date(2024, 1, 31))
   print(f"signals written: {num}")

   - 重みや閾値を変更することも可能:
     weights = {"momentum": 0.5, "value": 0.2, "volatility": 0.15, "liquidity": 0.1, "news": 0.05}
     generate_signals(conn, date(2024,1,31), threshold=0.65, weights=weights)

5) RSS ニュース収集（news → raw_news / news_symbols）
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   # known_codes: 銘柄抽出に使う有効な銘柄コードセット（例: {"7203","6758",...}）
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
   print(res)

6) 研究用途（forward returns / IC / summary）
   from kabusys.research import calc_forward_returns, calc_ic, factor_summary
   fwd = calc_forward_returns(conn, date(2024,1,31))
   # factor_records は factor_research.calc_momentum 等から得る
   # ic = calc_ic(factor_records, fwd, "mom_1m", "fwd_1d")

---

## 主要モジュール説明（抜粋）

- kabusys.config
  - .env 自動読み込みロジック、必須キー検査、環境判定（development / paper_trading / live）を提供します。

- kabusys.data.schema
  - DuckDB のテーブル定義（raw, processed, feature, execution 層）をまとめて作成する init_schema() を提供。

- kabusys.data.jquants_client
  - J-Quants API へのリクエスト、ページネーション、リトライ、トークン取得、DuckDB への保存ユーティリティ（save_daily_quotes 等）。

- kabusys.data.pipeline
  - run_daily_etl() をはじめとする ETL ジョブ群（差分取得・保存・品質チェック）。

- kabusys.data.news_collector
  - RSS 収集・前処理・正規化・DB 保存・銘柄抽出の実装。SSRF/サイズ上限/XML 攻撃対策済み。

- kabusys.research.factor_research
  - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を参照）。

- kabusys.strategy.feature_engineering
  - research 側の raw factor を統合・正規化し features テーブルへ UPSERT（Zスコア正規化・ユニバースフィルタ）。

- kabusys.strategy.signal_generator
  - features と ai_scores を統合して最終スコアを算出、BUY/SELL シグナルを signals テーブルへ書き込む。Bear レジーム判定やエグジット（ストップロス等）を含む。

---

## ディレクトリ構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      stats.py
      features.py
      calendar_management.py
      audit.py
      (その他 data 関連モジュール)
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    strategy/
      __init__.py
      feature_engineering.py
      signal_generator.py
    execution/
      __init__.py
    monitoring/
      (モニタリング関連モジュール)

（上記は主要ファイルの抜粋です。プロジェクト全体はさらに細分化されたファイルを含みます。）

---

## 運用上の注意

- J-Quants API のレート制限（120 req/min）に従う必要があります。本クライアントは固定間隔スロットリングとリトライ実装を備えていますが、大量バッチ実行時は並列化に注意してください。
- DuckDB ファイルのバックアップを定期的に行ってください（特に本番環境）。
- .env に機密情報を置く場合はアクセス制御を厳密にしてください。
- KABUSYS_ENV によって挙動（実際の発注実行フローなど）を分離する想定があります。live 環境では十分な安全対策（手動確認・上限設定）を行ってください。
- テスト時に自動 `.env` 読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

必要であれば README に含める具体的なコマンド例（systemd / cron ジョブ、コンテナ化手順、requirements.txt の候補など）や、よく使うユースケースのワークフロー（ETL → build_features → generate_signals → execution）について追記します。どの用途を優先して追加しますか？