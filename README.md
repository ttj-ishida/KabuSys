# KabuSys

日本株向け自動売買・リサーチ基盤のサンプル実装ドキュメント（README.md）です。  
このドキュメントはリポジトリに含まれるコード群（src/kabusys 以下）を元に、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめています。

注意：このリポジトリは本番・検証ロジックの雛形を含みます。実運用時はブローカー接続・資金管理・エラーハンドリング等を十分に検証してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ用モジュール群を提供するプロジェクトです。主な目的は以下です。

- 株価データを用いたファクター計算・特徴量探索（research）
- ポートフォリオ構築（候補選定／重み算出／ポジション決定）
- 発注フロー（OrderManager、ExecutionEngine）とリコンシリエーション
- 監視（System / Trade / Risk）とアラート（LINE）・停止フラグ（kill.flag）
- Paper Trading 用の分離された SQLite DB と検証ツール
- AI（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定
- DuckDB を使った分析向けデータ処理

主要な設計方針として「外部副作用を最小化した純粋関数」「ルックアヘッドバイアスの抑制」「フェイルセーフ（API障害時の保守的フォールバック）」が採用されています。

---

## 主な機能一覧

- research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー
- portfolio
  - 候補選定（スコア順）、等分/スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - ポジション決定（単元丸め、リスクベース、aggregate cap）
- execution
  - OrderManager（ステートマシン、重複防止、クラッシュ耐性）
  - Reconciler（起動時の自動復旧／ブローカー突合）
  - BrokerClientFactory を通じた実環境 / モック切替（paper_trading モード）
- monitoring
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine
  - MonitoringDB（SQLite）による永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - AlertManager（LINE push）、KillSwitch（フラグファイルを使った停止）
  - Streamlit ベースの監視ダッシュボード
- ai
  - news_nlp: OpenAI を用いたニュースごとのセンチメント評価（ai_scores への書き込み）
  - regime_detector: ETF の MA200 とマクロニュースの LLM 評価を合成して日次でレジーム判定
- tools
  - paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・レイテンシ等の検証レポート生成

---

## セットアップ手順

以下はローカルで開発・実行する際の一般的な手順例です。環境や要件によって適宜変更してください。

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存ライブラリをインストール  
   （requirements.txt はプロジェクトに含めてください。最低限想定されるパッケージ例）
   ```bash
   pip install -r requirements.txt
   ```
   必要なライブラリ例:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

4. 環境変数 / .env の準備  
   プロジェクトルートに `.env` / `.env.local` を置くことで自動的に読み込まれます（OS 環境変数 > .env.local > .env の優先度）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   代表的な環境変数:
   - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH: ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill flag（デフォルト: data/kill.flag）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必須）
   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等（外部 API を使う場合に必須）

---

## 使い方（主要な実行方法）

各スクリプトはパッケージモジュールとして起動できます。以下は代表的な実行例です。

1. 監視プロセス（MonitoringEngine の単純ポーリングループ）
   - 説明: SystemMonitor を定期実行して monitoring DB を維持・リスクログや kill.flag を操作します。
   - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
   - 実行例:
     ```bash
     python -m kabusys.run_monitoring
     ```
   - 特記事項:
     - run_monitoring はプロセス優先度を "high" に設定し、Settings から本番 sqlite_path を使用して monitoring DB を開きます（KABUSYS_ENV にかかわらず本番 DB を使用する設計）。

2. ExecutionEngine（取引エンジン）起動
   - 説明: ブローカークライアントを生成して注文フローを実行します。`KABUSYS_ENV=paper_trading` の場合、モックブローカーを使用して `data/paper_trading.db` に記録します（本番 DB と完全分離）。
   - 実行例:
     ```bash
     # Paper trading モード
     export KABUSYS_ENV=paper_trading
     python -m kabusys.run_execution

     # Live モード（例）
     export KABUSYS_ENV=live
     python -m kabusys.run_execution
     ```
   - 特記事項:
     - 起動時に実行中の PID を書き込み、KillSwitch / Monitoring の連携で停止指示を受け取れる設計です。

3. Paper Trading 検証レポート
   - 説明: `data/paper_trading.db` を解析して稼働率・注文成功率・レイテンシ等のレポートを出力します。
   - 実行例:
     ```bash
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
     ```

4. Streamlit 監視ダッシュボード
   - 説明: Monitoring DB を読み取り専用で可視化します（streamlit）。
   - 実行例:
     ```bash
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     ```

5. AI 関連
   - news_nlp.score_news: OpenAI API（OPENAI_API_KEY）を使ってニュース記事の銘柄別センチメントを ai_scores テーブルに書き込みます。
   - regime_detector.score_regime: ETF(ma200) とマクロニュースで市場レジームを判定し market_regime テーブルへ書き込みます。
   - これらはライブラリ関数として呼び出せます。API キーが未設定の場合は ValueError を送出します。

---

## 主要な設定とデフォルトパス

- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID ファイル: data/execution.pid
- Kill flag: data/kill.flag
- 環境モード: KABUSYS_ENV ∈ {development, paper_trading, live}（Settings クラスで検証）

.env 読み込み挙動:
- プロジェクトルート（.git または pyproject.toml が基準）を探索し `.env` と `.env.local` をロードします。
- OS 環境変数が優先されます。`.env.local` は `.env` を上書きできます。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 注意点 / 運用上のヒント

- Paper Trading は本番データベースと分離されるよう設計されています（settings.is_paper を使用）。検証時は KABUSYS_ENV を忘れずに設定してください。
- run_monitoring は監視 DB を「本番 sqlite_path」で開きます（環境にかかわらず）。開発環境で別 DB を使いたい場合は Settings を調整してください。
- OpenAI を使う機能（news_nlp / regime_detector）は API キーと通信コストが必要です。レスポンスの検証とリトライロジックは実装されていますが、料金・レート制限には注意してください。
- process priority / CPU affinity 設定は psutil を用いて行います。権限不足時は警告ログを出してスキップします。
- MonitoringDB はスキーマを起動時に冪等的に作成・マイグレーションします（例: trade_logs に latency_ms を追加する処理など）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・ディレクトリの概観です（本README 作成時点の抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - (order_manager.py, reconciler.py, execution_engine.py, broker_factory 等)
    - portfolio/
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/ (想定されるデータ配置場所: ローカルで作成)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb

（上記は主要ファイルの一覧であり、実際のリポジトリにはさらに多くのモジュールやテストが含まれる場合があります）

---

## よく使うコマンド（まとめ）

- 依存インストール
  ```bash
  pip install -r requirements.txt
  ```

- 監視の開始
  ```bash
  python -m kabusys.run_monitoring
  # MONITOR_POLL_INTERVAL を変更する例:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ExecutionEngine 起動（paper_trading）
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

## 最後に

この README はリポジトリ内のコードに基づく概要と利用手順をまとめたものです。実際の導入や運用に際しては、環境変数の設定、外部 API（kabuステーション、J-Quants、OpenAI 等）への接続情報の管理、バックテスト・リスク検証を十分に行ってください。

必要であれば、各モジュール（実装関数や設定項目）に対するより細かなドキュメント（API 仕様、設定例、シーケンス図など）も作成できます。どの部分を詳細化したいか教えてください。