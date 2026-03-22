# KabuSys — 日本株自動売買システム

バージョン: 0.1.0

概要
----
KabuSys は日本株のデータ取得・特徴量生成・シグナル生成・バックテストまでを一貫して扱うライブラリ/フレームワークです。  
主に以下のレイヤーを含みます：

- Data（J-Quants などからのデータ取得、DuckDB スキーマ）
- Research（ファクター計算・特徴量解析）
- Strategy（特徴量正規化・シグナル生成）
- Backtest（シミュレーション、評価指標）
- Execution / Monitoring（発注や監視のためのインターフェース群）

設計方針のポイント：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ使用）
- DuckDB を中心とした単一 DB スキーマ（冪等な INSERT/UPSERT）
- 外部 API 呼び出しは data 層に限定、strategy 層は発注層に直接依存しない
- テスト容易性を考慮した設計（id_token 注入や自動 env ロードの無効化等）

主な機能
--------
- J-Quants API クライアント（fetch/save + レート制御・再試行・トークン自動リフレッシュ）
- DuckDB スキーマ定義・初期化（init_schema）
- ETL パイプライン（差分取得・品質チェック）
- ニュース収集（RSS → raw_news 保存、銘柄抽出）
- ファクター計算（モメンタム / ボラティリティ / バリュー等）
- 特徴量エンジニアリング（Zスコア正規化・ユニバースフィルタ）
- シグナル生成（コンポーネントスコア結合・BUY/SELL 判定・冪等保存）
- バックテストエンジン（シミュレータ、CAGR/Sharpe/MaxDD 等の計算）
- CLI バックテスト実行エントリポイント（python -m kabusys.backtest.run）

セットアップ手順
----------------

前提
- Python 3.9+（typing の一部機能を利用）
- DuckDB を利用可能な環境

1. リポジトリをクローンし、仮想環境を準備（例）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存関係をインストール
   - pip install duckdb defusedxml
   - （プロジェクトとして配布される requirements.txt/pyproject があればそちらを使用してください）
   - 開発中であれば editable install:
     - pip install -e .

3. 環境変数を設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu API パスワード（execution 層利用時）
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python REPL あるいはスクリプトで:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - ":memory:" を指定するとインメモリ DB が作成されます（バックテストの内部で使用）。

基本的な使い方
--------------

以下は主要なユースケース（コード呼び出し例と CLI）の概要です。

1. スキーマ初期化（上記参照）
   - init_schema() で必要なテーブルを作成します。

2. データ取得・保存（J-Quants）
   - jquants_client.get_id_token() / fetch_daily_quotes() / save_daily_quotes() を使用してデータ取得 → 保存します。
   - ETL ヘルパー: data.pipeline.run_prices_etl() など（ETLResult を返す）。

3. ニュース収集
   - data.news_collector.run_news_collection(conn, sources, known_codes)
   - fetch_rss() と save_raw_news() / save_news_symbols() を内部で利用します。

4. ファクター計算・特徴量構築
   - research.* の関数で生ファクターを計算できます（calc_momentum, calc_volatility, calc_value）。
   - 戦略用途の特徴量を DB の features テーブルに書き込むには:
     ```
     from kabusys.strategy import build_features
     build_features(conn, target_date)
     ```

5. シグナル生成
   - features / ai_scores / positions を参照して signals テーブルを更新:
     ```
     from kabusys.strategy import generate_signals
     generate_signals(conn, target_date)
     ```

6. バックテスト実行（プログラムから）
   - run_backtest(conn, start_date, end_date, initial_cash=..., ...)
   - 例:
     ```
     from kabusys.data.schema import init_schema
     from kabusys.backtest.engine import run_backtest
     conn = init_schema("data/kabusys.duckdb")
     result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
     conn.close()
     ```
   - 結果は BacktestResult(history, trades, metrics)。

7. バックテスト CLI
   - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
   - オプション: --cash, --slippage, --commission, --max-position-pct

注意点・運用メモ
----------------
- J-Quants API のレート制限 (120 req/min) に対応した内部 RateLimiter が組み込まれています。API 呼び出しは遅延する可能性があります。
- jquants_client._request は 401 を検知すると token を自動更新して 1 回だけ再試行します。
- News Collector は RSS の SSRF や XML 攻撃対策（リダイレクト検査・プライベート IP 検出・defusedxml 使用・応答サイズ制限）を組み込んでいます。
- ETL は差分更新と backfill をサポートし、品質チェック（quality モジュール）を実行して問題を収集します（致命的エラーを必ず中断するわけではありません）。
- 自動環境ロードを無効にしたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

ディレクトリ構成
----------------

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数/設定管理
    - data/
      - __init__.py
      - jquants_client.py       — J-Quants API クライアント / 保存ロジック
      - news_collector.py       — RSS 収集・前処理・保存
      - pipeline.py            — ETL パイプライン
      - schema.py              — DuckDB スキーマ定義・初期化
      - stats.py               — Z スコア等統計ユーティリティ
    - research/
      - __init__.py
      - factor_research.py     — モメンタム/ボラ/バリュー計算
      - feature_exploration.py — 将来リターン/IC/統計サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py — features 作成（正規化・フィルタ）
      - signal_generator.py    — final_score 計算・BUY/SELL 生成
    - backtest/
      - __init__.py
      - engine.py              — バックテスト全体ループ
      - simulator.py           — ポートフォリオシミュレータ（約定モデル）
      - metrics.py             — 成績指標算出（CAGR, Sharpe 等）
      - run.py                 — CLI エントリポイント
      - clock.py               — 将来拡張用の模擬時計
    - execution/                — 発注層（未詳細実装ファイル群）
    - monitoring/               — 監視/通知（未詳細実装ファイル群）

開発・貢献
----------
- コードはドキュメント文字列と設計メモに従って記述されています。関数は副作用を明示し、DuckDB 接続を引数に取ることでテスト可能性を高めています。
- 新しい ETL ジョブやデータソース追加時は raw layer → processed → feature の流れ（および schema の更新）を意識してください。
- ユニットテスト、統合テストの追加を歓迎します。特に API クライアントや RSS 取得部はネットワークをモックしてテストすることを推奨します。

ライセンス
---------
プロジェクトのライセンス情報はリポジトリの LICENSE ファイルを参照してください。

問い合わせ
----------
実行時の問題や設計に関する質問はプロジェクトの issue tracker を使用してください。README に書かれている環境変数等の設定を添えて報告いただくと対応が早くなります。

以上。必要であれば README に含めるサンプル .env.example、より詳細な CLI/スクリプト例、あるいは運用手順（データバックフィル手順や定期ジョブ化例）を追加します。どれを追加しますか？