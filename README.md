# KabuSys

日本株向けの自動売買・リサーチ・監視フレームワークの一部実装です。  
本リポジトリには発注エンジン、監視系、ポートフォリオ構築、リサーチ、AI 補助モジュールなどが含まれます。

## プロジェクト概要
- 目的：日本株向けの自動売買システム（KabuSys）のコア機能群を提供するライブラリ／実行可能スクリプト群。
- 主なコンポーネント：
  - ExecutionEngine（発注エンジン）および OrderManager / Reconciler（起動時リコンシリエーション）
  - Monitoring（システム監視、注文監視、リスク監視、アラート）
  - Portfolio（銘柄選定・配分・サイズ計算）
  - Research（ファクター計算・特徴量評価）
  - AI モジュール（ニュース NLP に基づくセンチメント、レジーム判定）
  - 各種ツール（Paper Trading 検証レポート等）

## 機能一覧
- 実行系
  - 発注管理（OrderManager）、ブローカ抽象化（BrokerClientFactory）
  - 再起動後の同期待機・照合（Reconciler）
  - Paper trading と Live の分離（paper_trading 環境用に専用 SQLite DB を使用）
- 監視
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度を監視してログ化
  - TradeMonitor：滞留注文・約定異常価格を検出
  - RiskMonitor：ドローダウン・ポジション上限の評価、ダッシュボード更新、リスクログ記録
  - KillSwitch：致命的リスク発生時にフラグファイルを書き込み ExecutionEngine 停止指示
  - AlertManager：LINE Messaging API での一方向通知（クールダウン管理あり）
  - Streamlit ダッシュボードでの可視化（read-only で監視 DB を参照）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み、リスクベースの位置決め、セクター制約、レジーム乗数
- リサーチ
  - ファクター（Momentum / Volatility / Value）計算（DuckDB を使用）
  - 将来リターン、IC 計算、統計サマリー
- AI
  - ニュース記事のセンチメント評価（OpenAI API）
  - マクロ＋ETF ma200 による市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定で検証指標を出力）

## 要件
- Python 3.10+
- 必須パッケージ（代表）
  - duckdb, psutil, requests, streamlit, openai
- （使う機能に応じて）sqlite3、標準ライブラリ

インストール例（仮の venv を作る例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil requests streamlit openai
```

## セットアップ手順
1. リポジトリルートを取得し、PYTHONPATH に src を含める（またはパッケージをインストール）。
   - 開発時はルート直下に `src/` がある構成を想定しています。
2. 必要な環境変数を `.env` または `.env.local` に設定（自動ロード機能あり）。
   - 自動ロードはデフォルトで有効。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
3. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...  （AI 機能を使う場合必須）
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant|partial|never|reject  （paper_trading 用）
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - MONITOR_POLL_INTERVAL=60  （run_monitoring のポーリング間隔、秒）
4. data ディレクトリ
   - stop_requested.flag（監視/実行の外部停止用フラグ）
   - kill.flag（KillSwitch が書き込む停止理由）
   - execution.pid（ExecutionEngine の PID 保存に使用）
   必要に応じて `data/` を作成しておいてください。プログラムは必要時に親ディレクトリを作成します。

サンプル .env:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

## 使い方

基本的に src を PYTHONPATH に含めてモジュールとして実行します（開発時の例）。

- 監視（Monitoring）を起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は監視用 SQLite DB（Settings.sqlite_path）を使用。Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を参照します。
  - 実行例:
    ```bash
    PYTHONPATH=src python -m kabusys.run_monitoring
    ```
  - 監視を終了させたい場合はプロセスに Ctrl+C、またはプロジェクトルートの `data/stop_requested.flag` を作成します。

- 発注エンジン（ExecutionEngine）を起動
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離します。
  - 実行例:
    ```bash
    PYTHONPATH=src python -m kabusys.run_execution
    ```
  - 起動時に `data/stop_requested.flag` が存在すると起動を行わず終了します。実行中にフラグが立つと安全に停止します。
  - ExecutionEngine は起動時にプロセス優先度を "high" に設定します（可能な場合のみ）。

- Streamlit ダッシュボード
  - 監視用 DB を読み取り専用で参照して可視化します。
  - 実行例:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- Paper Trading 検証レポート
  - data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）から検証指標を算出して標準出力へ表示します。
  - 実行例:
    ```bash
    PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - `--db` オプションで DB パスを指定できます。

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または関数引数で指定）。
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を使って DuckDB 内の raw_news を解析し、ai_scores / market_regime に書き込みます。
  - これらはライブラリ関数として呼び出すことを想定しています。

注意点:
- .env の読み込みはプロジェクトルート（.git または pyproject.toml を起点）から行われます。OS 環境変数が優先されます。
- Settings クラスで環境変数の妥当性チェックを行っています（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
- MonitoringDB は起動時に必要なテーブルの作成・簡易マイグレーションを行います（冪等）。

## 主要ファイル／ディレクトリ構成
（抜粋・要点を表示）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - data/ (runtime)
    - stop_requested.flag
    - kill.flag
    - execution.pid
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (DB 周り)
    - execution_engine.py (Engine 本体)
    - broker_factory.py
    - broker_api.py
  - monitoring/
    - monitoring_db.py           — SQLite ベースの監視ログ層（テーブル初期化含む）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記以外にもログ・ユーティリティ等の補助モジュールが含まれます）

## 運用上のポイント・注意
- Paper Trading と Live 環境は DB を分離する設計です（Settings.is_paper に基づく）。
- AI の呼び出し（OpenAI）はリトライ・バックオフやレスポンス検証を含む実装ですが、API キー漏洩やコスト管理には注意してください。
- kill.flag / stop_requested.flag を用いた外部制御により、安全にプロセスを停止できます。KillSwitch は条件に合致すると `data/kill.flag` を書き込みます（冪等動作）。
- process priority / cpu affinity の設定はプラットフォーム依存です。権限不足時は警告を出してスキップします。
- DuckDB のスキーマ（prices_daily, raw_financials, raw_news など）はリサーチ・AI モジュールで参照されます。事前にデータをロードしてください。

---

不明点や README に追加してほしい項目（例：実行時ログ例、詳細な環境変数説明、CI/テスト手順など）があれば教えてください。必要に応じて追記・整備します。