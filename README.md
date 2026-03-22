KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株を対象とした自動売買・研究プラットフォームのコアライブラリ群です。データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、バックテスト、ニュース収集、DuckDB スキーマ定義などの機能を含みます。

主な特徴
--------
- データ取得
  - J-Quants API クライアント（レート制御・リトライ・トークン自動更新対応）
  - 株価（OHLCV）、財務データ、JPX マーケットカレンダー取得・保存
- ETL / Data Pipeline
  - 差分取得、バックフィル、品質チェック（設計）
  - DuckDB への冪等保存（ON CONFLICT ベース）
- 研究・ファクター処理
  - Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials を参照）
  - Zスコア正規化、ファクター探索（IC、統計サマリー等）
- 戦略
  - 特徴量エンジニアリング（build_features）
  - シグナル生成（generate_signals）：複数コンポーネントの重み付け・Bear レジーム対応・BUY/SELL 生成
- バックテスト
  - 日次シミュレータ（擬似約定・スリッページ・手数料・ポジション管理）
  - バックテストエンジン（run_backtest）と CLI
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio）
- ニュース収集
  - RSS から記事収集・前処理・記事ID生成・銘柄抽出・DB保存（SSRF・Gzip/サイズ制限・トラッキング除去等の対策）

必要条件
--------
- Python 3.10 以上（型注釈で | 型などを使用）
- 必要なパッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS 等を利用する場合）
- 環境変数（後述）または .env ファイル

推奨の最小 requirements.txt（例）
- duckdb
- defusedxml

セットアップ手順
---------------
1. リポジトリをクローン（またはソースを取得）
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれを使用してください）
   - 例: pip install -r requirements.txt

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - これにより必要なテーブルとインデックスが作成されます。

5. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（Settings により参照・必須判定されます）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API のパスワード
     - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID : Slack の送信先チャンネル ID
   - 任意／デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG/INFO/...) — デフォルト INFO
     - KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

例: .env（サンプル）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

基本的な使い方
------------

- DuckDB スキーマ作成
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- J-Quants からデータ取得して保存（例）
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - records = fetch_daily_quotes(date_from=..., date_to=...)
  - saved = save_daily_quotes(conn, records)

- 特徴量構築（features テーブルへの一括書き込み）
  - from kabusys.strategy import build_features
  - build_features(conn, target_date=date(2024, 1, 31))

- シグナル生成（signals テーブルへの書き込み）
  - from kabusys.strategy import generate_signals
  - generate_signals(conn, target_date=date(2024, 1, 31))

- バックテスト（Python API）
  - from kabusys.backtest.engine import run_backtest
  - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  - metrics = result.metrics

- バックテスト CLI
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
  - オプション: --cash, --slippage, --commission, --max-position-pct

- ニュース収集ジョブ（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, sources=None, known_codes=set_of_codes)

注意事項・トラブルシューティング
--------------------------------
- 環境変数未設定時
  - Settings の必須プロパティは未設定だと ValueError を送出します。必須キーを .env に設定してください。
- Python バージョン
  - 型注釈に Python 3.10+ の構文（| を使った Union）を利用しているため Python 3.10 以上を使用してください。
- DuckDB バージョン差異
  - 一部の制約（外部キーの ON DELETE 等）は DuckDB のバージョン依存を踏まえコメントで設計方針を示しています。問題が出る場合は DuckDB のバージョンを確認してください。
- ネットワーク取得時
  - J-Quants の API レート制限や RSS の応答サイズ上限に注意してください。ライブラリ側で制御は行っていますが、過負荷となる呼び出しは控えてください。
- テスト・サンドボックス
  - 自動ロードされる .env を無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で有用）。

ディレクトリ構成（主要ファイル）
-----------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（.env 自動ロードを含む）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py     — RSS ニュース収集／前処理／保存
    - pipeline.py           — ETL パイプライン（差分取得、ETL 管理）
    - schema.py             — DuckDB スキーマ定義・初期化（init_schema）
    - stats.py              — Zスコア正規化など統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Volatility/Value ファクター計算
    - feature_exploration.py— 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py— features テーブル生成（build_features）
    - signal_generator.py   — final_score 計算、BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py             — バックテストの全体ループ（run_backtest）
    - simulator.py          — PortfolioSimulator（擬似約定）
    - metrics.py            — バックテスト評価指標計算
    - run.py                — CLI entrypoint for backtest
    - clock.py              — 将来拡張用の模擬時計
  - execution/               — 発注関連のモジュール（空の __init__ が含まれます）
  - monitoring/              — 監視・アラート用（将来的な実装）
  - backtest、research、data、strategy 配下にさらに細かい実装あり

開発のヒント
-------------
- 各モジュールは「DB（DuckDB）の接続」を引数で受け取る設計で副作用を抑えています。テスト時は ":memory:" の DuckDB を使うと便利です。
- データ取得〜保存は冪等（ON CONFLICT）実装が多いため、安全に再実行できます。
- ルックアヘッドバイアス回避が設計思想として徹底されているため、時間軸に関する実装方針（target_date 以前の最新データのみ参照）を守ってください。

ライセンス・貢献
----------------
- 本 README は実装に基づく簡易ドキュメントです。実際のライセンスやコントリビューション規約はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

サポート
-------
- 実装や利用方法について疑問があれば、コード内の docstring（各モジュール冒頭）を参照してください。関数単位で設計思想・引数・戻り値・例外挙動が詳述されています。

以上が KabuSys コードベースの概要と導入・利用方法です。必要であれば、README に含める具体的なコマンド例（ETL ジョブの実行フローや .env.example の完全なテンプレート）を追記します。どの部分を詳しく書きたいか教えてください。