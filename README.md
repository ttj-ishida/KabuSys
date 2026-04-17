# KabuSys

日本株向け自動売買システム（ライブラリ / 実行コンポーネント群）のサンプル実装。  
このリポジトリは、注文実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、AI を使ったニュースセンチメント評価などの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は次のような関心事を分離した設計になっています。

- Execution: ブローカーとの発注・注文状態管理・再同期（Reconciler）を行う実行エンジン
- Monitoring: システム状態・注文滞留・リスク（ドローダウン・ポジション上限）を定期チェックし、ログ/アラート/キルスイッチを提供
- Portfolio: 候補選定、重み計算、ポジションサイズ決定、セクター制約適用などのポートフォリオ構築ロジック（純粋関数）
- Research: DuckDB を用いたファクター計算・将来リターン・IC/統計サマリ
- AI: OpenAI（gpt-4o-mini など）を用いたニュースセンチメント評価・市場レジーム判定
- Tools: Paper Trading の検証レポート生成や監視ダッシュボード（Streamlit）など

設計上のポイント:
- 環境ごと（development / paper_trading / live）で挙動や DB を分離
- Paper Trading は本番 DB と完全分離（デフォルト: data/paper_trading.db）
- .env 自動読み込みを行う（プロジェクトルートが検出可能な場合）。無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 主な機能一覧

- Execution
  - ブローカー抽象化（BrokerClientFactory）
  - OrderManager: 発注フロー / 重複防止 / 状態同期
  - Reconciler: 再起動後の注文・ポジション同期
  - RiskManager（制限・レート制御など）
- Monitoring
  - SystemMonitor: CPU/MEM/DISK、プロセス監視、データ鮮度判定
  - TradeMonitor: 注文滞留・約定異常検知
  - RiskMonitor: ドローダウン・ポジション数監視
  - KillSwitch: 条件で ExecutionEngine 停止フラグを書き込み
  - AlertManager: LINE Push 通知（クールダウン管理）
  - MonitoringEngine: 各 Monitor を束ねるポーリングループ
  - Streamlit ダッシュボード（読み取り専用）
- Portfolio
  - 候補選定（スコア順）
  - 等分配 / スコア重み付け
  - ポジションサイズ計算（単元丸め・aggregate cap・risk_based 配分）
  - セクターキャップ / レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン、IC（Spearman）、統計サマリ
- AI
  - ニュースを銘柄ごとに集約して OpenAI に送信、センチメントスコアを ai_scores に書き込み
  - 市場レジーム判定（ETF MA + マクロセンチメント合成）
- Tools
  - Paper Trading 検証レポート（tools.paper_verification_report）
  - Streamlit 監視ダッシュボード

---

## セットアップ手順

前提:
- Python 3.9+（ソースは型アノテーションと最近の構文を使用）
- システムに SQLite3 が利用可能
- DuckDB を使うため duckdb パッケージが必要
- psutil, requests, openai, streamlit などの追加依存

推奨の手順（仮想環境を利用）:

1. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   ※実際のプロジェクトでは requirements.txt を用意してください。上記は主要依存の例です。

3. データディレクトリ作成
   ```
   mkdir -p data
   ```
   デフォルト DB/ファイル:
   - SQLite (monitoring): data/monitoring.db
   - DuckDB: data/kabusys.duckdb
   - Paper trading SQLite: data/paper_trading.db
   - PID/flag ファイル: data/execution.pid, data/kill.flag, data/stop_requested.flag

4. 環境変数設定（最低限）
   - 必須（プロダクト的に参照されるが用途による）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY
   - 監視・通知:
     - LINE_CHANNEL_ACCESS_TOKEN（Alert を利用する場合）
     - LINE_USER_ID
   - 環境選択:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - 例: .env をプロジェクトルートに置くと自動読み込みされます（.env.local で上書き可能）。
   - 自動読み込みを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. （Paper Trading 用オプション）
   - PAPER_TRADING_SQLITE_PATH を設定すると paper_trading 用 DB を指定できます（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

---

## 使い方（実行例）

コードはモジュールとして実行可能です。プロジェクトルートから以下を呼び出します。

- 監視ループの起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
    または
    ```
    python src/kabusys/run_monitoring.py
    ```

  - 停止:
    - data/stop_requested.flag ファイルを作成するとループ検知で正常終了します（主にテスト用）。
    - KeyboardInterrupt (Ctrl+C) でも終了します。

- ExecutionEngine の起動（注文実行）
  - paper_trading モードの場合、MockBrokerClient を使用して paper_trading 用 DB に書き込まれます（本番 DB と分離）。
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
    または
    ```
    python src/kabusys/run_execution.py
    ```

  - 停止:
    - data/stop_requested.flag を作成すると実行中のエンジンに停止シグナルを送ります。
    - また、KillSwitch が条件を満たした場合は data/kill.flag が書き込まれ、起動時などに検出されます。

- Paper Trading 検証レポート生成
  - デフォルト DB: data/paper_trading.db
  - 期間指定可能:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB を指定:
    ```
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```

- Streamlit 監視ダッシュボード（読み取り専用）
  - 実行例:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - ダッシュボードは MonitoringDB の読み取り専用 URI で接続します。

- AI 関連（プログラムから呼び出す）
  - ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、結果を ai_scores テーブルへ書き込みます。
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要な環境変数（まとめ）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須プロパティ参照時にチェック）
- KABU_API_PASSWORD: kabu ステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の擬似約定モード）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（Settings 経由で取得）

注意: Settings モジュールは .env/.env.local を自動読込します（プロジェクトルートが検出された場合）。OS 環境変数は保護され、.env.local は上書きモードです。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py  — 環境変数 / Settings
- run_monitoring.py  — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py   — ExecutionEngine 起動スクリプト
- utils/
  - __init__.py
  - process_priority.py  — プロセス優先度 / CPU affinity
- monitoring/
  - __init__.py
  - monitoring_db.py     — SQLite テーブル初期化 / 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - order_repository.py
  - order_record.py
  - reconciler.py
  - execution_engine.py
  - broker_factory.py
  - (その他ブローカー抽象・実装)
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/ (想定)
  - monitoring.db (SQLite)
  - kabusys.duckdb
  - paper_trading.db
  - execution.pid / kill.flag / stop_requested.flag
- tools/
  - __init__.py
  - paper_verification_report.py

（上記は主要ファイルの抜粋です。細かいモジュールはソースツリーを参照してください。）

---

## 運用上の注意点

- Paper Trading と Live は DB を分離することで実動作と検証を混同しない設計です。KABUSYS_ENV を適切に設定してください。
- Monitoring は常に本番 sqlite_path を使う仕様の部分があります（run_monitoring のコメント参照）。運用時の DB パス設定に注意してください。
- OpenAI 呼び出しはネットワーク障害や 429/5xx を想定したリトライ実装がありますが、API キーやコスト管理に注意してください。
- PID / flag ファイルを使ってプロセスの生存確認や外部からの停止要求を扱っています（data/*.pid / data/*.flag）。運用スクリプトや supervisor/systemd と組み合わせる際はファイルパスに注意してください。
- AlertManager（LINE）ではトークン/ユーザーIDが未設定だと送信をスキップしログに残します。実運用ではクールダウンの設定や通知の冗長性を検討してください。

---

## 参考: よく使うコマンドの一覧

- 監視ループ（デフォルト間隔 60s）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジン（paper_trading で起動）
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード（読み取り専用）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

この README はコードベース（src/kabusys 以下）から生成した要点をまとめたものです。実際に導入・運用する際は各モジュールの docstring や設定（.env.example 等）を合わせて確認してください。必要であれば、インストール手順の requirements.txt、Dockerfile、systemd ユニット例や運用ガイド（バックアップ、DBマイグレーション、ログ管理など）も追加できます。