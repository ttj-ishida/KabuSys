# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。注文本体（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI を用いたニュース分析などをモジュール化して提供します。

以下はこのコードベースの概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成です。

---

## プロジェクト概要

- 自動売買エンジン（ExecutionEngine）と監視サブシステム（MonitoringEngine）を中心に、実運用・検証・リサーチ用のツール群を含むモジュール群です。
- DuckDB を用いた価格・ファイナンスデータの分析、SQLite による監視ログ永続化、外部ブローカー API / OpenAI API 連携などを想定しています。
- 環境設定は環境変数（`.env` ファイル自動読み込み対応）で行います。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

---

## 主な機能一覧

- Execution（発注・注文管理）
  - 起動スクリプト: `kabusys.run_execution`
  - Reconciler による起動時の自動同期（復旧）
  - OrderManager / OrderRepository による注文状態管理、リスク制約（RiskManager）との連携
  - `KABUSYS_ENV=paper_trading` 時は MockBroker を使用し、paper_trading 用 DB（`data/paper_trading.db`）に記録して本番 DB と完全分離

- Monitoring（監視）
  - 起動スクリプト: `kabusys.run_monitoring`
  - SystemMonitor：CPU/メモリ/ディスク/プロセス存在確認、データ鮮度チェック
  - TradeMonitor：滞留注文監視 / 約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：閾値超過時にフラグファイル（`data/kill.flag`）を書き込み ExecutionEngine 停止シグナルを発行
  - AlertManager：LINE Push による一方向アラート（クールダウン管理）

- Portfolio（銘柄選定・配分・ポジションサイズ）
  - 候補選定、等金額／スコア重みの計算、セクターキャップ、レジーム乗数、株数算出（単元丸め、利用可能資金に合わせたスケーリング）

- Research（ファクター計算・特徴量探索）
  - momentum / volatility / value ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー

- AI（ニュースセンチメント・レジーム判定）
  - news_nlp.score_news: OpenAI を使ったニュースセンチメントスコアの取得と ai_scores テーブルへの書き込み
  - regime_detector.score_regime: ETF の MA200 乖離とマクロニュースセンチメントの合成による市場レジーム判定

- ツール
  - paper_verification_report：Paper Trading の検証レポート生成スクリプト（稼働率・注文成功率・レイテンシ等の集計）
  - streamlit_dashboard：監視ダッシュボードの簡易 UI（Streamlit）

---

## 必要条件（推奨）

- Python 3.9+
- pip
- OS: Linux / macOS / Windows（プロセス優先度設定等はプラットフォーム依存の挙動あり）
- 外部ライブラリ（主なもの）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）

インストール例（仮に requirements.txt がない場合）:
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install duckdb psutil requests openai streamlit
# 開発インストール（パッケージ化されている場合）
pip install -e .
```

---

## 環境変数（主なもの）

- KABUSYS_ENV: 起動環境。valid: `development`, `paper_trading`, `live`（デフォルト: development）
  - 注意: run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視は本番DB向け想定）。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な機能がある場合）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能に必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE通知）に使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: 実行プロセス PID 管理ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject）デフォルト "instant"
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で上書き、デフォルト 60 秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとプロジェクトルートからの `.env` 自動読み込みを無効化します。

Settings モジュール（kabusys.config）にプロパティで多くの項目が定義されています。自動でルートの `.env` / `.env.local` を読み込みます（見つからない場合はスキップ）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt    # もし用意されていれば
   # または個別インストール
   pip install duckdb psutil requests openai streamlit
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` を置くと自動的にロードされます（OS環境変数が優先）。
   - 例（.env）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     LOG_LEVEL=INFO
     ```

4. データディレクトリの作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（よく使うコマンド）

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  ```bash
  python -m kabusys.run_execution
  ```
  - このスクリプトはプロセス優先度を `high` に設定し、Settings に従って SQLite / DuckDB に接続します。
  - KABUSYS_ENV が `paper_trading` の場合、`PAPER_TRADING_SQLITE_PATH` を使い、MockBroker を利用します。

- Monitoring（ポーリングループ）を起動
  ```bash
  # デフォルト 60 秒間隔。環境変数で上書き可能:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に `SQLITE_PATH`（本番監視 DB）を使用します。
  - 起動時に `PID` の存在やデータ鮮度、リスクチェックなどを行います。

- Paper Trading 検証レポート（CLI）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB は data/paper_trading.db、--db で上書き可能
  ```

- Streamlit 監視ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 機能（インポートして利用）
  - ニューススコア付け:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 4, 11), api_key="YOUR_API_KEY")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,11), api_key="YOUR_API_KEY")
    ```

---

## 監視 / Kill Switch の挙動（補足）

- RiskMonitor がドローダウンやポジション上限アラートを検知すると、`MonitoringDB.log_risk_event` にログを残します。
- KillSwitch はリスク閾値超過時に `KILL_FLAG_PATH`（デフォルト: data/kill.flag）を書き込みます。ExecutionEngine は起動時やループ内でこのフラグを検知して安全停止を行う想定です。
- `Settings.kill_flag_clear_on_start` が `1` の場合、ExecutionEngine 起動時にフラグをクリアするためのオプションがあります（設定で制御）。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの `src/kabusys` 下を抜粋）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py (インターフェース)
    - ...（発注関連実装）
  - monitoring/
    - monitoring_db.py              — SQLite テーブル作成 / 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
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
  - data/
    - pipeline.py / stats.py         — DuckDB 関連ユーティリティ（prices_daily 等の取り扱い）
  - utils/
    - process_priority.py            — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記以外に補助モジュール・型定義などが含まれます）

---

## 実装上の注意点 / 動作上の考慮

- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（デフォルト 60 秒）。0 以下の設定は無効としてデフォルトにフォールバックします。
- run_execution は起動時にプロセス優先度を上げようとします（プラットフォーム依存で失敗する場合は警告に留めます）。
- monitoring_db.init_monitoring_db は既存 DB に対しても冪等にテーブル／インデックスを作成します。既存スキーマに不足列があれば簡易マイグレーション（ALTER TABLE ADD COLUMN）を行う処理があります。
- AI 関連は OpenAI API のレスポンスやレート制限に対して堅牢化（リトライ、バリデーション、部分失敗時の保護）されていますが、API キーの管理と利用には注意してください。
- Paper Trading モードは実運用 DB と完全に分離することを想定しています。`KABUSYS_ENV=paper_trading` を指定すると ExecutionEngine は `PAPER_TRADING_SQLITE_PATH` を使用しますが、Monitoring は常に監視用（production 想定）DB を使用します。

---

## 参考コマンドまとめ

- Execution 起動:
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring 起動（ポーリング間隔 30 秒に設定例）:
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- Paper 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

必要であれば README にサンプル .env.example、より詳細な起動オプション説明（ExecutionEngine の設定や RiskManager のパラメータ調整方法）、テスト・デバッグ手順などを追加できます。どの項目を拡張するか教えてください。