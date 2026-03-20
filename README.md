# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（研究 / データ収集 / 特徴量生成 / シグナル生成 / ETL / 監査ログ）です。  
本リポジトリは以下のようなレイヤ構成で設計されています：生データ収集（Raw）、整形済み市場データ（Processed）、特徴量（Feature）、発注・約定・ポジション（Execution）および監査（Audit）。

バージョン: 0.1.0

---

## 概要（Project overview）

KabuSys は J-Quants 等の外部APIから市場データ・財務データ・カレンダー・ニュースを収集し、DuckDB に格納して、
研究用ファクター・特徴量の計算、戦略シグナル生成、ETL パイプラインやカレンダー管理、ニュース収集、監査ログを提供する Python モジュール群です。

設計上のポイント：
- DuckDB を中心に冪等性（ON CONFLICT）を保ったデータ保存
- ルックアヘッドバイアスを避けるため「target_date 時点の利用データのみ」を原則に実装
- J-Quants API のレート制御・リトライ・自動トークンリフレッシュ実装
- RSS ニュース収集での SSRF / XML 攻撃対策やトラッキングパラメータ除去
- ETL と品質チェックを分離し、個別に実行可能

---

## 主な機能一覧（Features）

- データ収集（J-Quants）
  - 日足（OHLCV）取得 / 保存（fetch_daily_quotes, save_daily_quotes）
  - 財務諸表取得 / 保存（fetch_financial_statements, save_financial_statements）
  - JPX カレンダー取得 / 保存（fetch_market_calendar, save_market_calendar）
  - レート制限・リトライ・トークン自動更新対応
- ETL パイプライン
  - run_daily_etl: 市場カレンダー・株価・財務の差分取得と品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別ジョブ
- スキーマ管理
  - init_schema(db_path) で DuckDB スキーマを初期化
- 研究・ファクター計算
  - calc_momentum / calc_volatility / calc_value（research/factor_research）
  - forward returns / IC / 統計サマリー（research/feature_exploration）
  - zscore_normalize（data.stats）
- 特徴量作成 & シグナル生成（strategy）
  - build_features(conn, target_date)：features テーブル構築
  - generate_signals(conn, target_date, ...)：signals テーブルに BUY/SELL を出力
- ニュース収集（RSS）
  - fetch_rss / save_raw_news / run_news_collection（news_collector）
  - URL 正規化、記事ID 作成、銘柄抽出（テキスト内の4桁コード）
- カレンダー管理（data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチ用）
- 監査ログ・トレーサビリティ（data.audit）
  - signal_events / order_requests / executions 等の監査テーブル

---

## セットアップ手順（Setup）

1. Python 環境を用意（推奨: venv / pyenv）
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要パッケージをインストール  
   このコードベースは標準ライブラリ中心ですが、動作に必要な主な外部依存は以下です。
   - duckdb
   - defusedxml

   例:
   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。）

3. 環境変数の設定（.env または OS 環境変数）
   - 自動ロード: パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（config.Settings で参照）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   任意/デフォルト値あり:
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

   .env 例:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

4. データベース初期化
   Python REPL またはスクリプトで DuckDB スキーマを初期化します:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   これにより必要なテーブル・インデックスが作成されます。

---

## 使い方（Usage）

以下は代表的な利用例です。各関数は DuckDB の接続（duckdb.DuckDBPyConnection）を受け取って動作します。

- スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日を対象に実行
  print(result.to_dict())

- 個別 ETL（株価のみ）
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())

- 特徴量構築（strategy 層）
  from datetime import date
  from kabusys.strategy import build_features
  n = build_features(conn, target_date=date(2025, 1, 15))
  print(f"features upserted: {n}")

- シグナル生成
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date(2025, 1, 15))
  print(f"signals written: {total}")

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, known_codes={"7203", "6758"})  # known_codes を渡すと銘柄紐付けを行う
  print(results)

- カレンダー更新バッチ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

ログレベルや環境モードは環境変数で切り替わります（KABUSYS_ENV / LOG_LEVEL）。settings.is_live / is_paper / is_dev プロパティで実行モード判定が可能です。

注意:
- generate_signals / build_features 等は DuckDB 内のテーブル（prices_daily, raw_financials, features, ai_scores, positions, など）に依存します。事前に ETL（run_daily_etl 等）でデータを用意してください。
- jquants_client の API 呼び出しは rate limit と retry を含むため、単発で多数のリクエストを投げないでください。

---

## ディレクトリ構成（Directory structure）

主要なファイル・モジュール一覧（抜粋）:

src/kabusys/
- __init__.py
- config.py                      - 環境変数 / 設定読み込み
- data/
  - __init__.py
  - jquants_client.py            - J-Quants API クライアント（取得・保存）
  - news_collector.py            - RSS ニュース収集・保存
  - schema.py                    - DuckDB スキーマ定義 / init_schema
  - stats.py                     - 統計ユーティリティ（zscore_normalize）
  - pipeline.py                  - ETL パイプライン（run_daily_etl 等）
  - calendar_management.py       - カレンダー管理（営業日計算 / 更新ジョブ）
  - audit.py                     - 監査ログスキーマ
  - features.py                  - features の公開インターフェース
- research/
  - __init__.py
  - factor_research.py           - ファクター計算（momentum/value/volatility）
  - feature_exploration.py       - 将来リターン, IC, 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py       - features テーブル構築
  - signal_generator.py          - シグナル生成ロジック
- execution/                      - 発注/実行層（サブモジュール）
- monitoring/                     - 監視・通知系（将来的に）

補足:
- ドキュメント内では DataPlatform.md, StrategyModel.md 等参照が記載されています（実務上の仕様書参照箇所）。

---

## 開発上の注意点 / 実運用メモ

- 環境変数は .env / .env.local で管理できます。自動読込の優先度は OS 環境変数 > .env.local > .env です。プロジェクトルートの自動検出は __file__ を起点に .git または pyproject.toml を探索します。
- J-Quants のトークンリフレッシュは自動で行われますが、refresh token が無効な場合は明示的に更新してください。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に保存されます。バックアップやファイルパス管理に注意してください。
- ニュース収集は RSS の構造差異や大きなフィードサイズに注意（MAX_RESPONSE_BYTES 制限あり）。外部からのフィードを追加する際はソース毎に検証してください。
- ETL の品質チェックは pipeline.quality モジュール（コードベースに含まれる想定）で検出した問題を結果として返します。品質エラーを検出しても ETL は可能な限り継続します（呼び出し元で対処を決定）。

---

## ライセンス / コントリビューション

（ここにライセンス情報・貢献ガイドを追加してください）

---

この README はコードベースの現状（src/kabusys 以下）を元にした概要です。実運用で使用する前に、API キー・環境変数・DB 設定・監視・バックアップについて十分に検討してください。質問や追加のドキュメントが必要であれば教えてください。