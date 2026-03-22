KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリです。
本リポジトリはデータ収集（J‑Quants / RSS 等）、データ整備（DuckDB スキーマ / ETL）、
特徴量計算・シグナル生成、バックテスト用シミュレータまでを含むモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアスを防ぐため、各処理は target_date 時点のデータのみを参照する
- DuckDB をデータストアとして採用し、冪等な保存（ON CONFLICT）を行う
- API 呼び出しはレート制御・リトライ・トークン自動更新などを備える
- 外部依存を最小化し、標準ライブラリで多くを実装（ただし duckdb, defusedxml 等は必要）

機能一覧
- データ取得 / 保存
  - J‑Quants API クライアント（株価・財務・マーケットカレンダー取得、保存）
  - RSS ベースのニュース収集（前処理・URL 正規化・銘柄抽出・DB 保存）
  - ETL パイプライン（差分取得、バックフィル、品質チェックフレームワーク）
- データスキーマ
  - DuckDB 用の包括的スキーマ定義と初期化（raw / processed / feature / execution レイヤ）
- 研究用ユーティリティ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン / IC 計算 / 統計サマリー
  - Z スコア正規化等の統計関数
- 戦略
  - 特徴量作成（features テーブルへの日次 UPSET）
  - シグナル生成（final_score 計算、BUY/SELL のロジック、Bear レジーム抑制）
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル、約定ロジック）
  - バックテストエンジン（本番 DB からインメモリ DuckDB へコピーして日次ループ実行）
  - 標準メトリクス（CAGR / Sharpe / MaxDrawdown / WinRate / PayoffRatio）
  - CLI エントリポイント: python -m kabusys.backtest.run

セットアップ手順（開発環境）
1. Python 環境
   - Python 3.10+ を推奨（typing 表記などを使用）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があれば pip install -e . を使用）
4. DuckDB 初期化
   - Python REPL やスクリプトでスキーマを初期化します:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
5. 環境変数の設定
   - プロジェクトルートに .env / .env.local を配置すると自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必要な主な環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL     : kabu API のベース URL（省略時は http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID（必須）
     - DUCKDB_PATH           : デフォルト DB パス（省略時 data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite パス（省略時 data/monitoring.db）
     - KABUSYS_ENV           : development | paper_trading | live（省略時 development）
     - LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL（省略時 INFO）

使い方（代表的な操作例）

- DuckDB スキーマの初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

- J‑Quants から株価を取得して保存（簡易例）
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)

- RSS ニュース収集ジョブ（既知銘柄セットを渡して銘柄紐付け）
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203","6758", ...}  # 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  conn.close()

- 特徴量作成（features テーブルへ書き込み）
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features
  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024,1,31))

- シグナル生成（signals テーブルへ書き込み）
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals
  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024,1,31))

- バックテスト実行（CLI）
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  上記は CSV 等を出力せず、標準出力に主要統計量を表示します。

- バックテストを Python API から呼ぶ
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()
  # result.history, result.trades, result.metrics を参照

主要モジュール / ディレクトリ構成
（src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py
      - J‑Quants API クライアント（レートリミット・リトライ・トークン自動更新）
    - news_collector.py
      - RSS 取得・記事前処理・raw_news / news_symbols 保存
    - schema.py
      - DuckDB のスキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL 周りの差分取得ヘルパーとジョブ（run_prices_etl など）
    - quality.py (参照のみ: 品質チェック用モジュール想定)
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value（prices_daily/raw_financials 参照）
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features（生ファクターの正規化・features への書込）
    - signal_generator.py
      - generate_signals（features + ai_scores → final_score → signals）
  - backtest/
    - __init__.py
    - engine.py
      - run_backtest（本番DBからインメモリへコピーして日次ループを実行）
    - simulator.py
      - PortfolioSimulator / 約定ロジック / mark_to_market 等
    - metrics.py
      - calc_metrics と各評価指標実装
    - run.py
      - CLI ランナー（python -m kabusys.backtest.run）
    - clock.py
      - SimulatedClock（将来的な時間拡張用）
  - execution/
    - __init__.py
    - （発注・接続・kabu API 連携等を配置する想定）
  - monitoring/
    - （監視・アラート関連モジュールを配置する想定）

実装に関する補足
- DB 初期化は init_schema() を使うことで安全に行えます（冪等）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。
  CWD に依存せず配布後も動作する設計です。
- ニュース収集では SSRF 対策・応答サイズ制限・gzip 解凍後のサイズチェック等のセーフガードを実装しています。
- J‑Quants クライアントは固定間隔のレートリミット、401 時のトークン自動リフレッシュ、リトライ（バックオフ）を備えます。

よくある操作まとめ
- スキーマ作成:
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
- ETL（手動で簡単に）:
  - prices: jquants_client.fetch_daily_quotes → jquants_client.save_daily_quotes
  - financials: jquants_client.fetch_financial_statements → save_financial_statements
  - calendar: fetch_market_calendar → save_market_calendar
- 研究/調査:
  - calc_forward_returns / calc_ic / factor_summary を用いてファクター検証
- バックテスト:
  - python -m kabusys.backtest.run --start ... --end ... --db data/kabusys.duckdb

注意事項
- 本ライブラリは実運用を想定したコンポーネントを含みますが、実際に発注を行う前に十分なテスト（paper_trading モード等）を行ってください。
- 環境変数や API トークンは安全に管理してください（コード内のハードコーディングは避ける）。
- DuckDB のファイルは適切にバックアップ・管理してください。":memory:" モードは一時的解析に便利です。

貢献・拡張
- execution 層での実際の発注ロジック（kabuステーション連携）の実装
- モデル・AI スコア連携（ai_scores を計算するパイプライン）
- 監視・アラート（Slack 通知など）の強化（monitoring モジュール）
- CI / テストケースの追加（ETL の品質チェックロジックのユニットテスト化）

お問い合わせ
- 実装に関する質問や提案があればリポジトリの Issue を作成してください。README の補足やサンプルスクリプト追加も歓迎します。