# KabuSys

日本株向け自動売買システムの一部モジュール群（ポートフォリオ構築、バックテスト/リサーチ補助、実行エンジンの補助、監視・運用ツールなど）。

以下はこのコードベースの README です。

---

## プロジェクト概要

KabuSys は日本株の自動売買運用を支援するライブラリ兼運用ツール群です。本リポジトリには以下の主要機能を提供するモジュールが含まれます。

- 実行エンジン起動スクリプト（ExecutionEngine の起動/リコンシリエーション）
- 監視（System / Trade / Risk モニタ）とアラート送信（LINE）
- ポートフォリオ構築（候補選定、重み計算、ポジション決定）
- 研究・ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI モジュール（ニュース NLP によるセンチメントスコア、レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計方針として、Lookup-ahead バイアス防止やフェイルセーフ（API 失敗時のフォールバック）、DB（SQLite / DuckDB）を用いた永続化/集計、テストしやすい純粋関数分離が採用されています。

---

## 主な機能一覧

- execution
  - 起動時リコンシリエーション（Reconciler）
  - OrderManager / OrderRepository による注文管理
  - BrokerClientFactory による本番 / Paper Trading 切替
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス死活・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログ記録
  - AlertManager: LINE Push による一方向通知（クールダウン制御あり）
  - KillSwitch: フラグファイルによる ExecutionEngine 停止トリガ
  - Streamlit ダッシュボード（監視情報可視化）
- portfolio
  - 候補選定（score 降順）
  - 重み算出（等金額 / スコア加重）
  - ポジションサイズ計算（risk-based / equal / score）
  - セクター上限適用、レジーム乗数
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（情報係数）、統計サマリー
- ai
  - ニュースを OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores 保存
  - レジーム判定（ETF MA200 とマクロセンチメントの合成）
- tools
  - Paper Trading 検証レポート生成（過去期間の稼働率 / 注文成功率 / レイテンシ等を集計）

---

## セットアップ手順

※ ここでは基本的な手順を示します。プロジェクトの要求に合わせて適宜調整してください。

1. リポジトリをクローンし、作業ディレクトリに移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   - 必要に応じて他パッケージ（依存関係）を追加してください。
   - 実際のプロジェクトでは requirements.txt を用意している場合があります。

4. 環境変数設定
   - .env または .env.local に必要な設定を記載できます（config モジュールが自動ロードします）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - OPENAI_API_KEY (AI モジュールを使う場合必須)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (監視アラートを LINE に送る場合)
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - SQLITE_PATH (監視 DB) デフォルト: data/monitoring.db
   - DUCKDB_PATH (分析 DB) デフォルト: data/kabusys.duckdb
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）デフォルト: data/paper_trading.db
   - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒。デフォルト 60）

   例 .env（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABUSYS_ENV=development
   ```

---

## 使い方

以下は主要スクリプトや操作の実行方法例です。パッケージのルートが PYTHONPATH にある（通常はプロジェクトルート）ことを前提に `python -m` でモジュールを実行できます。

1. ExecutionEngine を起動（本番 / paper_trading を env で切替）
   ```
   # 本番/開発（デフォルト）
   python -m kabusys.run_execution

   # Paper Trading モード
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution
   ```
   - Paper Trading の場合、専用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に取引ログを記録し、本番 DB と分離します。
   - 実行時にプロセス優先度が「high」に設定されます（psutil を使用）。

2. 監視ポーリングを起動
   ```
   # デフォルトポーリング間隔 60 秒
   python -m kabusys.run_monitoring

   # ポーリング間隔上書き（例: 30秒）
   export MONITOR_POLL_INTERVAL=30
   python -m kabusys.run_monitoring
   ```
   - 監視は設定に関係なく本番 sqlite_path を使用して監視用テーブルを生成/更新します（init_monitoring_db を呼ぶため）。
   - MONITOR_POLL_INTERVAL は正の整数で指定。無効値だと 60 秒にフォールバックします。

3. Streamlit で監視ダッシュボードを表示
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - DB を読み取り専用で開きます。MonitoringEngine が先に監視 DB を生成していることが必要です。

4. Paper Trading 検証レポート生成
   ```
   # 指定期間のレポート
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

   # DB パス指定
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```
   - 指標: 稼働率・注文成功率・送信率・レイテンシ（P95）などを出力。基準値に達しないと FAIL 表示になります。

5. AI モジュール（ニューススコア / レジーム判定）
   - OpenAI API キーを `OPENAI_API_KEY` に設定してから以下を呼び出す（プログラム内から呼ぶ想定）。
   - 例: kabusys.ai.score_news(conn, target_date, api_key=None)
   - 失敗時はフォールバックやスキップの挙動が組み込まれています（安全策）。

---

## 主要ファイル / ディレクトリ構成

（主要モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / .env ロード / Settings クラス
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート生成
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (存在する想定)
    - broker_factory.py (存在する想定)
    - ...                           — 実行フロー関連（OrderRecord 等）
  - monitoring/
    - monitoring_db.py              — SQLite スキーマ初期化・CRUD ユーティリティ（MonitoringDB）
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
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/ (想定)
    - prices_daily / raw_financials / raw_news 等を格納・参照（DuckDB）
  - utils/
    - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ

---

## 設定（Settings クラス）概略

Settings クラス（kabusys.config.Settings）はアプリケーション設定を環境変数から読みます。主なプロパティとデフォルト値:

- jquants_refresh_token (必須)
- kabu_api_password (必須)
- kabu_api_base_url (default: http://localhost:18080/kabusapi)
- line_channel_access_token / line_user_id
- duckdb_path (default: data/kabusys.duckdb)
- sqlite_path (default: data/monitoring.db)
- paper_sqlite_path (default: data/paper_trading.db)
- pid_file_path (default: data/execution.pid)
- kill_flag_path (default: data/kill.flag)
- kill_flag_clear_on_start (env var = "1" で True)
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct
- env: KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- log_level: LOG_LEVEL (INFO など)

詳細は src/kabusys/config.py を参照してください。

---

## 注意事項 / 運用上のポイント

- Paper Trading 用 DB は本番 DB と分離されています（settings.is_paper により切替）。
- OpenAI API を用いる処理（ニュース NLP、レジーム判定）は API キーが必須で、API コールに失敗した場合はフォールバック（0.0 など）して継続するよう設計されています。ただし生成モデルの挙動に依存するため運用時はログ監視が必要です。
- MonitoringDB のスキーママイグレーション（カラム追加）処理が含まれています（冪等）。
- プロセス優先度・CPU affinity の変更は psutil を使用します。権限不足や未対応 OS の場合は警告が出てスキップされます。
- kill.flag を用いた停止シグナル機構により、監視側から ExecutionEngine を安全に停止できます（フラグファイルの存在を ExecutionEngine が定期チェックする想定）。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine が起動していることを確認してください。

---

README は以上です。詳細な API 仕様や ExecutionEngine の内部動作、Broker API の実装・設定方法については該当ソース（execution ディレクトリ、broker_factory 等）や設計ドキュメント（Project 内の Markdown）を参照してください。必要なら README に含めるサンプル .env、systemd / supervisor 用の起動ユニット例、デバッグ方法などを追記します。どの情報を追記しますか？