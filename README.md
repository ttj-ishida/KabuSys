# KabuSys

KabuSys は日本株の自動売買 / 研究 / 監視を目的とした小規模なワークスペースです。本リポジトリはトレード実行エンジン、監視基盤、リサーチ用ファクタ計算、AI を用いたニュースセンチメント評価などのコンポーネントで構成されています。

主な設計方針
- 本番 / paper_trading を切り替え可能（環境変数 KABUSYS_ENV）
- DuckDB をデータ分析用に使用、SQLite を監視・オーダー記録に使用
- LLM（OpenAI）との対話は明示的に API キーを渡すか環境変数で管理
- 自動ロードされる .env / .env.local をサポート（プロジェクトルート検出で .git / pyproject.toml を参照）

---

## 機能一覧

- Execution（発注エンジン）
  - Broker クライアントを透過的に切り替え（本番 / Mock for paper trading）
  - OrderManager / Reconciler による状態管理と再同期
  - RiskManager による発注制限（ポジション上限・ドローダウンなど）
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とアラート記録
  - MonitoringEngine: 各種モニタを束ねたポーリングループ
  - AlertManager: LINE Messaging API へのプッシュ通知
  - KillSwitch: 条件を満たすと `data/kill.flag` を書き込み ExecutionEngine を停止
  - Streamlit ダッシュボード（監視情報の可視化）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等重・スコア重み、リスク調整（セクター上限、レジーム係数）、発注株数計算（単元丸め 等）
- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（ニュース NLP / レジーム判定）
  - raw_news を LLM（gpt-4o-mini）で解析し銘柄毎にスコアを ai_scores に格納
  - ETF（1321）MA とマクロニュースを合成して市場レジーム（bull/neutral/bear）を判定
- Tools
  - paper_verification_report: Paper Trading の検証レポートを生成（稼働率・注文成功率・レイテンシ等）

---

## 前提（推奨環境）

- Python 3.10+
- 主な依存ライブラリ（抜粋）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード用)
- OS: Linux / macOS / Windows（プロセス優先度設定は OS により差分あり）

※ requirements.txt は含まれていないため、使用する環境に応じて上記パッケージをインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンしてソースコードルートへ移動
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

2. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

4. データディレクトリを作成
   - mkdir -p data

5. 環境変数 / .env の準備
   - プロジェクトルートに .env（必要な環境変数を記載）
   - 自動ロード順: OS 環境 > .env.local > .env
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（一部）
- JQUANTS_REFRESH_TOKEN — J-Quants 用（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 関連機能利用時）
- KABUSYS_ENV — environment：development / paper_trading / live（デフォルト: development）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH — 各種ファイルパス
- PAPER_FILL_MODE — paper_trading の約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

---

## 使い方（実行例）

- ExecutionEngine（発注エンジン）を起動
  - 本番モード:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（モックブローカー・分離DB）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行中の停止は data/stop_requested.flag を作成するとスレッドは検知してシャットダウンします（または KillSwitch により data/kill.flag が書き込まれます）。

- Monitoring（監視ループ）を起動
  - MONITOR_POLL_INTERVAL を指定してポーリング間隔を変更可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（監視用 DB）と DuckDB を使用します。Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を利用します。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を直接指定: --db data/paper_trading.db

- AI / レジーム判定（ライブラリ呼び出し）
  - Python から直接呼ぶ例:
    - from kabusys.ai import score_news
    - count = score_news(duckdb_conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- 開発用ユーティリティ
  - process priority 設定: run_* スクリプトは起動時にプロセス優先度を "high" に設定します（権限不足時は警告を出してスキップ）。

---

## 主要ファイルと説明

- src/kabusys/run_execution.py
  - ExecutionEngine を起動するエントリポイント。paper_trading 用 DB の切り替え、BrokerFactory によるクライアント生成、エンジンのスレッド実行を行います。

- src/kabusys/run_monitoring.py
  - SystemMonitor を定期実行する監視ループ。MONITOR_POLL_INTERVAL で間隔指定可能。

- src/kabusys/config.py
  - Settings クラス（環境変数 / .env 管理）。自動ロード、必須チェック、各種パス・閾値の取りまとめを行います。

- src/kabusys/monitoring/
  - monitoring_db.py: 監視用 SQLite スキーマと永続化 API（MonitoringDB）
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 各種モニタ
  - monitoring_engine.py: 複数モニタを統合するループ
  - alert_manager.py: LINE 通知
  - kill_switch.py: 停止フラグ管理
  - streamlit_dashboard.py: Streamlit ダッシュボード

- src/kabusys/execution/
  - execution_engine, order_manager, order_repository, reconciler 等：発注ロジックとリカバリ機構

- src/kabusys/portfolio/
  - 銘柄選定・重み計算・リスク調整・ポジションサイジングの純粋関数群

- src/kabusys/research/
  - factor_research.py, feature_exploration.py：ファクター計算、将来リターン、IC、統計サマリ

- src/kabusys/ai/
  - news_nlp.py：ニュースを LLM に投げて銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector.py：ETF MA とマクロニュースを組み合わせてレジーム判定

- src/kabusys/tools/paper_verification_report.py
  - Paper Trading の検証レポート出力スクリプト

---

## ディレクトリ構成（抜粋）

以下は主要なファイル／ディレクトリの概観（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - process_priority.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - ...
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/ (想定されるデータファイル)
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - execution.pid, kill.flag, stop_requested.flag

---

## 運用上の注意

- .env の取り扱い:
  - Settings はプロジェクトルートから .env / .env.local を自動読み込みします。CI やテストで自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用い、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と完全分離する設計です。
  - PAPER_FILL_MODE（instant/partial/never/reject）により模擬約定の振る舞いを変更できます。
- Kill / Stop フラグ:
  - data/kill.flag は KillSwitch による強制停止信号を表します。data/stop_requested.flag は run_* スクリプトの手動停止用フラグ（存在確認してループを抜けます）。
- OpenAI
  - API 呼び出しは rate limit や一時的な失敗に対してリトライを持ちますが、API キーは適切に管理してください。API コール失敗時は安全側の値（例: 0.0）でフォールバックする設計です。

---

## 開発・テスト

- 各モジュールは外部副作用を最小化した純粋関数（portfolio, research 等）と副作用を伴う I/O 層（monitoring_db, OrderRepository 等）に分離しています。ユニットテストは純粋関数や DB 層のモックを用いて実装しやすい設計です。
- OpenAI 呼び出し部分は内部で _call_openai_api を介しており、テスト時はこの関数を patch して挙動を制御できます。

---

必要であれば README に具体的なコマンド一覧（systemd ユニット例 / docker-compose 例 / requirements.txt の候補）や環境変数の雛形（.env.example）を追加します。どの情報を追記しますか？