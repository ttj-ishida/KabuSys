# KabuSys

日本株自動売買システムのミニマル実装。戦略・ポートフォリオ構築、発注実行、監視・アラート、リサーチ／ファクター計算、AI を使ったニュースセンチメントなどのコンポーネントを含むモジュール群です。

主に学習・検証 / Paper Trading / 本番（Live）を念頭に設計されています。

## 概要

- モジュール化された自動売買プラットフォーム（戦略・実行・監視・リサーチ・AI）
- DuckDB を用いた時系列データ処理、SQLite による監視ログ・発注ログ保存
- Paper Trading 用に本番 DB と分離された専用 DB をサポート
- OpenAI（gpt-4o-mini 等）を利用したニュース NLP / 市場レジーム判定機能
- LINE による監視アラート送信、Streamlit ダッシュボードによる可視化

## 主な機能一覧

- portfolio
  - 銘柄候補選定（スコア・等分配）
  - セクター集中ルール適用、レジームに応じた乗数
  - 発注株数（lot 単位）計算（リスクベース / 等分配 / スコア加重）
- execution
  - ExecutionEngine 起動スクリプト（run_execution）
  - Broker クライアントの抽象化（Paper Trading 用 Mock 対応）
  - 注文管理（OrderManager）、再同期（Reconciler）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor（ポーリングによる監視）
  - MonitoringDB：監視ログ永続化（SQLite）
  - KillSwitch：フラグファイルで ExecutionEngine 停止シグナル発行
  - AlertManager：LINE push 通知
  - Streamlit ダッシュボード（read-only）
- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、統計サマリ
- ai
  - news_nlp: ニュースを LLM でセンチメント評価して ai_scores に書き込み
  - regime_detector: MA200 とマクロセンチメントを合成して市場レジーム判定
- tools
  - paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順（ローカル開発向け）

1. Python（3.9+ 推奨）をインストールし、仮想環境を作成・有効化します。

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストールします（必要に応じてバージョンを固定してください）。

   必要パッケージ（主なもの）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

   例（pip）:

   ```
   pip install duckdb psutil requests openai streamlit
   ```

   ※ プロジェクトに requirements.txt がある場合はそちらを使ってください。

3. プロジェクトルートに `.env` を作成して環境変数を設定します。`kabusys.config` は自動で `.env` / `.env.local` を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   代表的な環境変数例（.env）:

   ```
   KABUSYS_ENV=development              # development | paper_trading | live
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   LINE_CHANNEL_ACCESS_TOKEN=...       # 通知を使う場合
   LINE_USER_ID=...                    # 通知を使う場合
   PAPER_FILL_MODE=instant             # instant|partial|never|reject
   SQLITE_PATH=data/monitoring.db      # 監視 DB（デフォルト）
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

   注意:
   - `JQUANTS_REFRESH_TOKEN` / `KABU_API_PASSWORD` 等は必須のプロパティがあるため、該当機能を使う場合は設定してください。
   - Paper Trading 時は KABUSYS_ENV=paper_trading に設定すると発注は MockBrokerClient を使用し、Paper 用 DB（デフォルト: data/paper_trading.db）に記録されます。

4. data ディレクトリを作成しておくと便利です。

   ```
   mkdir -p data
   ```

---

## 使い方（主要スクリプト）

- 監視（SystemMonitor のポーリングを単独で起動）

  ```
  python -m kabusys.run_monitoring
  ```

  オプション・挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60 秒）。
  - run_monitoring は Monitoring 用の SQLite（Settings.sqlite_path）を使用します（監視は環境にかかわらず本番 sqlite_path を参照します）。
  - 停止: プロジェクトルート下の data/stop_requested.flag を作成するとループを抜けます。

- 実行エンジン（ExecutionEngine）起動

  ```
  python -m kabusys.run_execution
  ```

  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に全て記録されます（本番 DB と分離）。
  - 起動前に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag 作成で検出・停止します。
  - Execution 側の停止要求（ポジション過大・ドローダウン超過など）は monitoring の KillSwitch により data/kill.flag を書き込んで指示します。

- Streamlit ダッシュボード（監視データを可視化）

  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

  - read-only モードで監視 DB を開きます。DB が存在しない場合は警告が表示されます。

- Paper Trading 検証レポート生成

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  - デフォルト DB: data/paper_trading.db。`--db` オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で変更できます。
  - 稼働率、注文成功率、レイテンシ（P95）等を評価して PASS/FAIL 判定を出力します。

- AI（ニューススコア / レジーム判定）

  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)
  - 両機能とも OPENAI_API_KEY（または引数での api_key 指定）が必須です。APIのエラー時は安全側のフォールバックロジックが有効化されます（例: macro_sentiment=0.0）。

---

## 制御・フラグについて

- 停止フラグ
  - data/stop_requested.flag — run_monitoring / run_execution が監視している停止フラグ（存在するとループを抜ける）。
  - data/kill.flag — KillSwitch が作成し、ExecutionEngine に停止を促すためのフラグ。既存なら再書き込みしない（冪等）。

- PID
  - data/execution.pid — ExecutionEngine の PID。SystemMonitor はこの PID を見てプロセス存在確認を行う（stale PID の検出・削除機能あり）。

---

## 設定（Settings / .env の自動読み込み）

- kabusys.config.Settings が環境変数をラップします。主なプロパティはコード中に注釈があります（duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode, env, log_level など）。
- 自動 .env ロードはデフォルトで有効：プロジェクトルート（.git または pyproject.toml が見つかる場所）から `.env` を読み込みます。
- 自動ロードを無効にするには環境変数を設定します:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソース構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py
  - run_execution.py
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他発注関連モジュール：broker_factory, execution_engine, order_repository 等)
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (実行時に生成されることが多い)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)

（上記は抜粋です。実際のリポジトリではさらに細かいモジュールが存在します）

---

## 注意事項 / 動作上のポイント

- 監視（Monitoring）は監視用 SQLite（Settings.sqlite_path）に書き込みます。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計です（監視データは一元管理する想定）。
- Paper Trading モードは Execution 側で専用 DB に記録するため本番 DB と混在しません（設定により上書き可能）。
- AI 関連機能は外部 API（OpenAI）に依存します。API キーの管理・料金に注意してください。
- プロセス優先度 / CPU affinity 設定は utils/process_priority.py にてラップされています。権限不足等で設定に失敗してもログに警告を出してスキップします。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くことを想定しています（URI の mode=ro を使用）。

---

## 開発・貢献

- コードはモジュール単位で分割されているため、ユニットテストや差し替え（モック）しやすく設計されています。外部 API 呼び出し部分はテスト時にパッチする想定のインターフェース設計です（例: OpenAI 呼び出し関数の差し替え）。
- Pull Request の際は機能ごとに小さく切って、ドキュメント（docstring）を充実させてください。

---

必要があれば README に「実際の起動例」「.env.example」「依存関係の固定済み requirements.txt 例」などを追加します。どの情報を優先して追加しますか？