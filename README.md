# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買／リサーチ／監視を目的とした軽量な Python プロジェクトです。本リポジトリは以下の主要コンポーネントを含みます: 実取引・ペーパートレーディング用の Execution Engine、監視（Monitoring）、ポートフォリオ構築ロジック、ファクター計算・リサーチ用モジュール、LLM を使ったニュース NLP / レジーム判定機能など。

---

## 主な特徴（機能一覧）

- Execution
  - ブローカー抽象化（BrokerClientFactory）を介した実発注／モック発注（paper_trading）
  - OrderManager による注文ライフサイクル管理（作成→送信→同期）
  - Reconciler による起動時の自動リコンシリエーション（注文状態・ポジションの突合）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視（kill.flag 発行）
  - AlertManager: LINE Push による通知（クールダウン付き）
  - Streamlit ダッシュボード（読み取り専用）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等重／スコア重み付け、ポジションサイズ計算、セクター制約、レジーム乗数

- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計要約

- AI（LLM 統合）
  - news_nlp: OpenAI（gpt-4o-mini）でニュースを銘柄別にセンチメント評価し ai_scores に保存
  - regime_detector: ETF MA200 とマクロニュースによる市場レジーム判定

- ユーティリティ
  - process_priority: OS に依存しないプロセス優先度 / CPU affinity の設定
  - 環境変数読み込み（.env / .env.local の自動ロード、プロジェクトルート検出）

---

## セットアップ手順

1. Python と仮想環境
   - Python 3.9+ を推奨。仮想環境を作成してアクティベートしてください。
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate      # Windows
     ```

2. 依存パッケージのインストール
   - requirements.txt はリポジトリにないため、主要依存を手動でインストールしてください（例）:
     ```
     pip install duckdb psutil requests openai streamlit
     ```
   - 実運用では各モジュールに対応する追加パッケージが必要となる場合があります。

3. データディレクトリ作成
   ```
   mkdir -p data
   ```

4. 環境変数 / .env
   - プロジェクトルートの `.env`（または `.env.local`）に必要な環境変数を設定します。自動読み込み機能が有効（デフォルト）です。
   - 主要な環境変数例:
     ```
     KABUSYS_ENV=development          # development | paper_trading | live
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     PAPER_FILL_MODE=instant         # instant | partial | never | reject
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PID_FILE_PATH=data/execution.pid
     KILL_FLAG_PATH=data/kill.flag
     LOG_LEVEL=INFO
     ```
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. データベース初期化
   - 実行スクリプトは内部で必要テーブルを作成するため、基本的に手動マイグレーションは不要です。`data/monitoring.db` がない場合は自動作成されます。

---

## 使い方（主要スクリプト）

- ExecutionEngine（実行エンジン）起動
  - 本番／ペーパーは KABUSYS_ENV に依存:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB に書き込み。
  - 起動:
    ```
    python -m kabusys.run_execution
    ```

- Monitoring（SystemMonitor 単独ポーリング）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可。デフォルト 60 秒。
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- Streamlit ダッシュボード（監視 UI）
  - 読み取り専用で monitoring DB を参照します。起動例:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- Paper Trading 検証レポート生成
  - 過去期間のパフォーマンス指標を出力します:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB パスを指定する場合:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- AI 機能を呼ぶ
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date、API キーを渡して呼び出します（コード内 API を参照）。

---

## 実行時の注意点

- KABUSYS_ENV:
  - 利用可能な値: development, paper_trading, live
  - paper_trading は本番 DB と分離された paper_trading DB を使用します（PAPER_TRADING_SQLITE_PATH）。

- PAPER_FILL_MODE:
  - instant | partial | never | reject
  - paper_trading 時のモック約定挙動を制御します。

- kill.flag（停止シグナル）:
  - RiskMonitor が条件を満たすと設定され、ExecutionEngine 起動時に検出して安全停止できます。Settings.kill_flag_clear_on_start を有効にすると起動時に自動クリアします。

- プロセス優先度:
  - 実行スクリプトは起動直後に set_process_priority("high") を試みます。OS により動作や権限が異なります。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン）
  - config.py — 環境変数・設定読み込みロジック（.env 自動読み込み含む）、Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- src/kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py など
  - 注文管理、ブローカー抽象、リコンシリエーション等の実装

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
  - monitoring_engine.py — 複数監視を束ねるエンジン
  - alert_manager.py — LINE 通知
  - kill_switch.py — kill.flag 管理
  - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 候補選定・重み付け・株数計算・セクター制約等

- src/kabusys/research/
  - factor_research.py, feature_exploration.py — ファクター計算・IC 計算・統計サマリ

- src/kabusys/ai/
  - news_nlp.py — ニュース NLP（OpenAI）による銘柄別センチメント
  - regime_detector.py — MA200 + マクロニュースで市場レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- src/kabusys/utils/
  - process_priority.py — プロセス優先度／CPU affinity ユーティリティ

---

## ライセンス・貢献

- 本 README ではライセンス情報は含まれていません。実際に公開する場合は LICENSE ファイルを追加してください。
- コードに修正や機能追加を行う場合は、テストを追加し、.env の取り扱いや API キーの安全管理に注意してください。

---

必要であれば、README に「環境変数一覧（詳しい説明）」「起動例の systemd / Dockerfile サンプル」「ユニットテストの実行方法」等を追加で作成します。どの情報を優先して補足しますか？