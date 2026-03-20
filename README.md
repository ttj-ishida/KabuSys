# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログ、マーケットカレンダー管理など、戦略検証〜運用のための主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を持つモジュール群から構成されています。

- J-Quants API クライアント（データ取得、トークンリフレッシュ、レート制御、リトライ）
- DuckDB ベースのデータスキーマ定義・初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算（Momentum / Volatility / Value）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（final_score 計算、BUY/SELL 判定、エグジット判定）
- ニュース収集（RSS → raw_news 保存、銘柄抽出）
- マーケットカレンダー管理（営業日判定 / next/prev / 範囲取得）
- 監査ログ（signal → order → execution のトレースを支援）
- 各種ユーティリティ（統計関数、ETL結果のデータクラス等）

設計方針としては「ルックアヘッドバイアス防止」「冪等性」「外部 API のレート・エラー対処」「ドメインロジックの分離（発注層とは独立）」を重視しています。

---

## 機能一覧

- データ取得
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - 保存用: save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
- データ基盤
  - schema.init_schema: DuckDB スキーマ作成（Raw / Processed / Feature / Execution 層）
  - get_connection: 既存 DB への接続
- ETL
  - data.pipeline.run_daily_etl: 日次 ETL（カレンダー・株価・財務・品質チェック）
  - 差分取得／バックフィル機能を備える
- 研究 / ファクター
  - research.factor_research: calc_momentum / calc_volatility / calc_value
  - research.feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 特徴量 / シグナル
  - strategy.feature_engineering.build_features: features テーブル作成（Z スコア正規化・ユニバースフィル）
  - strategy.signal_generator.generate_signals: features / ai_scores / positions を参照して signals を生成
- ニュース収集
  - data.news_collector.fetch_rss / save_raw_news / run_news_collection
  - 銘柄コード抽出、SSRF 対策、XML セーフパーサー、サイズ制限などの安全対策あり
- カレンダー管理
  - data.calendar_management: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 統計ユーティリティ
  - data.stats.zscore_normalize
- 監査ログ / 発注監査
  - data.audit: signal_events / order_requests / executions 等のテーブル定義

---

## 要件

主要な依存パッケージ（プロジェクトの pyproject.toml / setup.py を合わせて参照してください）:

- Python 3.8+
- duckdb
- defusedxml
- （標準ライブラリのみで実装された部分も多いです）

開発環境では pip 等でインストールしてください:

pip install duckdb defusedxml

（プロジェクトルートにパッケージ設定があることを前提に、editable インストールも可能）

pip install -e .

---

## セットアップ手順

1. リポジトリをクローン／展開し、必要な依存をインストールする。

2. 環境変数を設定する（.env をプロジェクトルートに置くことで自動ロードされます）。
   自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。

   推奨される .env の例:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   注意:
   - settings モジュールは上記環境変数を参照します。必須項目が未設定だと ValueError が発生します。
   - 自動読み込みは .git または pyproject.toml をプロジェクトルート判定に使用します。

3. DuckDB スキーマを初期化する:

   Python REPL / スクリプト例:

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # または :memory: でインメモリ DB
   # conn = schema.init_schema(":memory:")

   これで必要な全テーブル・インデックスが作成されます。

---

## 使い方（主要ユースケース）

以降は Python API を直接呼ぶことを想定した例です。

- 日次 ETL 実行（データ取得 → 保存 → 品質チェック）

  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュース収集ジョブ（RSS → raw_news）

  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # sources を指定するかデフォルトを使用
  saved_map = news_collector.run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
  print(saved_map)

- 特徴量構築（research 側で計算済みの raw factor を取り込み、features に保存）

  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  cnt = build_features(conn, target_date=date.today())
  print(f"built {cnt} features")

- シグナル生成（features + ai_scores + positions を参照し signals を更新）

  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"generated {total_signals} signals")

- J-Quants からのデータ取得例（低レベル）

  from kabusys.data import jquants_client as jq
  quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  # 保存
  from kabusys.data import schema
  conn = schema.get_connection("data/kabusys.duckdb")
  jq.save_daily_quotes(conn, quotes)

注意点:
- 各種関数はルックアヘッドバイアスを防ぐため target_date 時点のデータのみを使うよう設計されています。
- 多くの保存関数は冪等（ON CONFLICT/DO UPDATE）を前提としています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API 用パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: sqlite（監視向け）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## 開発者向けメモ

- 設定自動ロード:
  - パッケージ起動時にプロジェクトルートを .git または pyproject.toml で探索し、ルート直下の .env と .env.local を自動ロードします。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（ユニットテスト等で便利です）。

- テスト:
  - DuckDB の ":memory:" を使うとインメモリ DB で高速にテスト可能です。
  - jquants_client の HTTP 呼び出しや news_collector._urlopen などはテスト時にモックする設計になっています。

- ロギング:
  - settings.log_level を参照してログレベル管理ができます。

---

## ディレクトリ構成

以下は主要なソースツリー（src/kabusys/ 配下）の概観です。

- kabusys/
  - __init__.py
  - config.py                            # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                  # J-Quants API クライアント
    - news_collector.py                  # RSS ニュース収集
    - schema.py                          # DuckDB スキーマ定義・初期化
    - stats.py                           # 統計ユーティリティ (zscore_normalize)
    - features.py                        # features の公開ラッパー
    - pipeline.py                        # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py             # マーケットカレンダー管理
    - audit.py                           # 監査ログテーブル定義
    - execution/                          # 実行関連（発注等）用の空パッケージ（拡張余地）
  - research/
    - __init__.py
    - factor_research.py                 # Momentum/Value/Volatility の計算
    - feature_exploration.py             # IC/forward returns/summary
  - strategy/
    - __init__.py
    - feature_engineering.py             # features 作成（正規化・ユニバースフィル）
    - signal_generator.py                # final_score 計算 + signals 生成
  - execution/                            # 発注・監視用（実装は別途）
  - monitoring/                           # 監視関連（DB・Slack連携等、拡張）

（実際のリポジトリは src/ 以下に配置されます）

---

## よくある質問 / 注意事項

- データの整合性:
  - ETL は後続で DB の品質チェックを実行しますが、重大な問題があっても ETL は可能な限り継続し、問題は quality チェック結果として返されます。
- Bear レジーム判定:
  - signal_generator は ai_scores の regime_score を使って市場レジームを判定し、Bear の場合は BUY を抑制します。
- 冪等性:
  - raw データの保存関数は ON CONFLICT（UPSERT）を使って冪等に設計されています。繰り返し実行しても重複しません。
- セキュリティ:
  - news_collector は SSRF 対策、XML の安全なパース、レスポンスサイズの制限などを行っており、外部フィード取得の安全性に配慮しています。

---

必要があれば README に実行スクリプト例（cron / systemd / Docker による運用例）、CI テスト手順や .env.example のテンプレートを追加します。追加で記載したい内容を教えてください。