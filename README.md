# KabuSys

日本株向けの自動売買システム用ライブラリ。データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等のユーティリティを提供します。主に DuckDB をデータストアとして利用する設計です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの基盤を構成するモジュール群を提供します。主な責務は以下の通りです。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を用いたスキーマ定義／初期化／永続化（raw → processed → feature → execution の多層構造）
- ETL パイプライン（差分取得、バックフィル、品質チェックフック）
- 研究用途のファクター計算（momentum/volatility/value）および特徴量正規化
- 戦略シグナル生成（複数コンポーネントスコアの統合、BUY/SELL 判定）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策、トラッキングパラメータ除去、前処理）
- マーケットカレンダー管理（営業日判定、next/prev などのユーティリティ）
- 監査ログ（シグナル→発注→約定までのトレーサビリティ）設計

設計上の共通方針として、ルックアヘッドバイアスの排除（target_date 時点のデータのみ参照）、冪等性（ON CONFLICT を用いた保存）、外部 API への依存を最小化することが挙げられます。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants との通信、ページネーション対応、トークン自動リフレッシュ、レート制御、保存ユーティリティ（save_daily_quotes 等）
- data/schema.py
  - DuckDB 用スキーマ定義と init_schema/get_connection
- data/pipeline.py
  - 日次 ETL（run_daily_etl）・個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
- data/news_collector.py
  - RSS 取得、記事正規化、raw_news 保存、news_symbols 紐付け、SSRF 対策
- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- data/stats.py, data/features.py
  - Z スコア正規化などの統計ユーティリティ
- research/factor_research.py, research/feature_exploration.py
  - momentum/volatility/value のファクター計算、将来リターン・IC 計算・統計サマリ
- strategy/feature_engineering.py
  - features テーブル構築（ファクター合成・ユニバースフィルタ・正規化・クリップ）
- strategy/signal_generator.py
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成・signals テーブルへの保存
- execution/
  - 発注周りのモジュール（スケルトン／分離）
- config.py
  - 環境変数管理（.env 自動読み込みの仕組み、必須変数チェック）

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10 以上（型アノテーションに `X | Y` を使用）
- DuckDB を使うためネイティブ環境に合わせたインストールが必要です

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 以下はコード内で想定される主要依存（プロジェクトに requirements.txt があればそれを利用してください）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （将来 HTTP クライアントやログ出力の補助等で追加依存が必要になる可能性があります）

4. 環境変数設定
   - ルートに `.env` を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須環境変数（config.Settings の require を参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション（デフォルトがあるもの）:
     - KABUSYS_ENV (development|paper_trading|live) — default: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db

   例 .env（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（DuckDB）
   - Python から呼ぶ例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - メモリ DB を使う場合:
     ```python
     conn = init_schema(":memory:")
     ```

---

## 使い方（主要ユースケース）

以下はライブラリを利用する際の典型的なワークフロー例（Python スクリプト / REPL から）です。

1. DB の初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL（J-Quants からの差分取得＋品質チェック）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

3. 特徴量（features）構築
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   n = build_features(conn, target_date=date.today())
   print(f"{n} 銘柄の features を upsert しました")
   ```

4. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"{total} 件のシグナルを書き込みました")
   ```

5. ニュース収集（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コード集合
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

6. マーケットカレンダー更新（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"saved: {saved}")
   ```

備考:
- run_daily_etl 等は内部で例外を捕捉して各ステップごとに継続する設計です。戻り値（ETLResult）で品質問題やエラーの有無を確認してください。
- .env 自動読み込みを行うため、テストなどで自動ロードを抑えたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と設定管理（.env 自動読み込み、必須変数の検証）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py
      - DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - news_collector.py
      - RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py
      - 市場カレンダー管理（営業日判定・更新ジョブ）
    - features.py
      - zscore_normalize の再エクスポート
    - stats.py
      - 汎用統計ユーティリティ（z-score 正規化等）
    - audit.py
      - 監査ログ関連 DDL（signal_events, order_requests, executions など）
    - pipeline.py (上記)
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value ファクター計算
    - feature_exploration.py
      - 将来リターン計算 / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル作成ロジック
    - signal_generator.py
      - シグナル生成ロジック
  - execution/
    - __init__.py
    - （発注実行に関する実装を置く場所）

---

## 注意事項 / 運用上のポイント

- 環境変数に API トークン等の機密情報を含めるため、`.env` を誤ってコミットしないでください（.gitignore に追加してください）。
- J-Quants API のレート制限（120 req/min）を _RateLimiter により守る実装がありますが、実運用時は更に運用ポリシーを定めてください。
- DuckDB スキーマは冪等に作成されます。既存の DB を使う場合は init_schema の呼出しを検討してください（初回のみ）。
- 本コードベースは「ルックアヘッドバイアス防止」を意識しており、各処理は target_date 時点でアクセス可能なデータのみを参照する設計です。戦略実装やバックテスト時はこの前提を守ってください。
- KABUSYS_ENV により環境（development / paper_trading / live）を切替可能。live 環境では発注周りの取り扱いに注意してください。

---

## 貢献 / 開発フロー（簡易）

- Issue や Pull Request を通じて変更を提案してください。
- 重要機能追加やスキーマ変更は互換性とデータ移行を考慮してください（DDL の変更は既存データに影響します）。
- テストはユニットレベルで DuckDB のインメモリ DB（":memory:"）を使うと簡単に実行できます。

---

必要であれば README にコマンド例（systemd/cron 用の実行スクリプト、CI 設定、requirements.txt、LICENSE）や、各モジュールのより詳細な API リファレンスを追記します。どの情報を優先して追記しますか？