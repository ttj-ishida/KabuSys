# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
主に以下を提供します。

- J‑Quants API からのデータ取得（OHLCV、財務、マーケットカレンダー）
- DuckDB を用いたデータスキーマと永続化（冪等保存）
- ETL パイプライン（差分取得・品質チェック）
- ニュース収集（RSS）と銘柄抽出
- 研究用ファクター計算／特徴量生成
- 戦略シグナル生成（BUY/SELL・エグジット判定）
- 監査（Audit）・実行レイヤー構想（テーブル定義）

バージョン: 0.1.0

---

## 特徴（機能一覧）

- data
  - J-Quants クライアント（リトライ、トークン自動リフレッシュ、レート制限対応）
  - DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ニュース収集（RSS 取得・前処理・DB保存・銘柄抽出、SSRF/サイズ制限対策）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - 統計ユーティリティ（Zスコア正規化 等）
- research
  - ファクター計算（momentum / volatility / value）
  - ファクター探索ユーティリティ（将来リターン算出、IC 計算、統計サマリー）
- strategy
  - 特徴量エンジニアリング（research の生データから features テーブルを構築）
  - シグナル生成（features + ai_scores を統合して final_score を計算、BUY/SELL 判定）
- execution（パッケージ化済、発注実装は別途）
- audit（監査用テーブル定義と初期化ロジック）
- 設定管理（.env 自動読み込み、環境変数の集中管理）

設計上のポイント
- ルックアヘッドバイアスを避けるため、各処理は target_date 時点のデータのみを参照
- DuckDB に対する INSERT は冪等になるように設計（ON CONFLICT など）
- 外部呼び出し時はリトライ・バックオフ・レート制限を考慮
- RSS の取り扱いは SSRF 対策・サイズ上限・XML 脆弱性対策を実施

---

## セットアップ手順

前提
- Python 3.10 以上（コードベースで | None 等の構文を使用しています）
- duckdb, defusedxml などの依存パッケージ

1. リポジトリをクローンしてパッケージをインストール（開発時）
   - 推奨: 仮想環境を作成する
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)
   - 開発インストール（プロジェクトルートに setup / pyproject がある想定）
     - pip install -e .

2. 必要なパッケージをインストール
   - 例:
     - pip install duckdb defusedxml

3. 環境変数を設定
   - プロジェクトルートの .env または .env.local に必要項目を設定してください。
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（注文機能を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack チャネルID
   - データベースパス（任意、デフォルトあり）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - その他
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...
   - 自動 .env 読み込み
     - ランタイムで .env を自動ロードします（プロジェクトルートに .git または pyproject.toml がある場合）。
     - テスト等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DuckDB スキーマ初期化
   - 実行例（後述の「使い方」参照）で init_schema を呼んでください。

---

## 使い方（簡単なクイックスタート）

以下は Python スクリプトでの基本的な流れ例です。

1. DuckDB スキーマを初期化して接続を得る
   - from kabusys.data.schema import init_schema
   - from kabusys.config import settings
   - conn = init_schema(settings.duckdb_path)

2. 日次 ETL を実行してデータを取得・保存する
   - from kabusys.data.pipeline import run_daily_etl
   - result = run_daily_etl(conn)  # target_date を省略すると今日を対象に実行
   - print(result.to_dict())

3. 特徴量の構築（features テーブルへ書き込み）
   - from kabusys.strategy import build_features
   - from datetime import date
   - n = build_features(conn, date.today())  # target_date を指定

4. シグナル生成
   - from kabusys.strategy import generate_signals
   - total = generate_signals(conn, date.today())
   - print("signals written:", total)

5. ニュース収集ジョブの実行例
   - from kabusys.data.news_collector import run_news_collection
   - known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
   - res = run_news_collection(conn, sources=None, known_codes=known_codes)
   - print(res)

注意点 / トラブルシューティング
- J-Quants の API 認証エラー (401) は自動でリフレッシュする設計ですが、refresh token が無効な場合は失敗します。JQUANTS_REFRESH_TOKEN を確認してください。
- DuckDB のファイル保存先ディレクトリ（例: data/）に書き込み権限があるか確認してください。
- .env の自動ロードはプロジェクトルート検出に .git または pyproject.toml を利用します。CI/テスト環境で意図的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

## ディレクトリ構成

主要なファイル／モジュール一覧（src/kabusys 配下）

- __init__.py
- config.py
  - 環境変数管理（settings オブジェクト）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py      — RSS 取得／前処理／DB 保存／銘柄抽出
  - schema.py              — DuckDB スキーマ定義・init_schema / get_connection
  - stats.py               — zscore_normalize 等の統計ユーティリティ
  - pipeline.py            — ETL パイプライン（run_daily_etl 他）
  - features.py            — data.stats の公開インターフェース
  - calendar_management.py — market_calendar 管理（営業日判定・更新ジョブ）
  - audit.py               — 監査ログ（signal_events, order_requests, executions 等）
- research/
  - __init__.py
  - factor_research.py     — momentum / volatility / value 計算
  - feature_exploration.py — 将来リターン / IC / summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py — features テーブル構築（研究ファクターの正規化・フィルタ）
  - signal_generator.py    — final_score 計算・BUY/SELL 生成・signals 書き込み
- execution/
  - __init__.py
  - （実行／発注層の実装は別途）
- monitoring/ (含まれる想定)
  - （監視／アラート用モジュール）
- その他
  - 各ドキュメント（DataPlatform.md、StrategyModel.md などの参照を想定）

注: 上記はコードベースの主要モジュールを抜粋したものです。実装の詳細は各モジュールの docstring を参照してください。

---

## 主要 API / 関数一覧（抜粋）

- config.settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live 等
- data.schema
  - init_schema(db_path) -> DuckDB 接続
  - get_connection(db_path)
- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)
- research
  - calc_momentum(conn, date), calc_volatility(...), calc_value(...)
  - calc_forward_returns, calc_ic, factor_summary, rank
- strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=0.6, weights=None)

---

## ロギング / モード

- KABUSYS_ENV により動作モードを切り替えられます（development / paper_trading / live）。
- LOG_LEVEL 環境変数でログレベル（DEBUG/INFO/...）を制御できます。

---

## 開発・拡張メモ

- strategy 層は発注（execution）層とは分離しており、シグナルは signals テーブルへ書き込まれます。発注ロジックを追加する場合は execution 層で signals → signal_queue → orders → trades のフローを実装してください。
- research 側の関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照する仕様です。外部 API 呼び出しは行いません。
- ニュース収集は既知銘柄コードセットを渡すことでニュースと銘柄の紐付けを行います。銘柄抽出は 4 桁数字の候補を検出後、known_codes によりフィルタします。
- DuckDB の互換性やバージョン依存（FOREIGN KEY の挙動や ON DELETE 制約等）に注意してください（コード内に注記あり）。

---

もし README に追加したい内容（例: 実行スクリプト例、CI 設定、ライセンス、コントリビュート手順、より詳しい環境変数の例など）があれば教えてください。必要に応じてサンプル .env.example も作成します。