# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」の実装コード群です。以下はプロジェクト概要、主要機能、セットアップ手順、使い方、ディレクトリ構成の簡潔な説明です。

注意: 本 README はソースコード（src/kabusys 以下）に基づいて作成しています。詳細や追加の運用ルールはソース内の docstring/コメントを参照してください。

---

## プロジェクト概要
KabuSys は次の主要機能を持つ日本株向け自動売買基盤です。

- 注文の発行・管理（ExecutionEngine / OrderManager）
- 監視・アラート（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- リコンシリエーション（再起動時の注文同期）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター調整）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- ニュースを用いた LLM ベースのセンチメント評価（OpenAI API 経由）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

設計方針の一部:
- DuckDB / SQLite を分析・監視用 DB に使用（本番監視は sqlite）
- LLM 呼び出しや日時の取得はルックアヘッドバイアスを避ける実装
- フェイルセーフ（API 失敗時のフォールバック、部分失敗時の DB 保護等）

---

## 機能一覧
主なモジュールと機能（抜粋）:

- kabusys.config
  - 環境変数/.env 読み込み、Settings クラス（必要な環境変数検証を含む）
- kabusys.execution
  - ExecutionEngine（起動・セッション管理）
  - OrderManager、OrderRepository、Reconciler（注文管理・復旧）
- kabusys.monitoring
  - SystemMonitor（CPU/Mem/Disk、プロセス・データ鮮度チェック）
  - TradeMonitor（滞留注文・約定異常確認）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（kill.flag によるエンジン停止）
  - AlertManager（LINE Push による通知）
  - MonitoringEngine（複数モニタの定期実行）
  - streamlit_dashboard（監視用 UI）
- kabusys.portfolio
  - ポートフォリオ候補選定・重み計算（等分・スコア重み）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、資金キャップ）
- kabusys.research
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- kabusys.ai
  - news_nlp: ニュース記事を LLM でセンチメント付与して ai_scores に書き込み
  - regime_detector: ETF MA とマクロニュースで市場レジーム判定
- kabusys.tools
  - paper_verification_report: Paper Trading データの検証レポート生成

運用に関わるファイル／フラグ（デフォルト場所）
- data/monitoring.db（監視ログ）
- data/paper_trading.db（Paper Trading 用 sqlite）
- data/kabusys.duckdb（DuckDB）
- data/execution.pid（ExecutionEngine の PID）
- data/kill.flag（KillSwitch が書く停止フラグ）
- data/stop_requested.flag（run_* スクリプトの外部停止フラグ）

---

## セットアップ手順（開発 / 運用向け）

前提: Python 3.8+（具体的なバージョンはプロジェクト要件に合わせてください）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 要件（主に使用されているパッケージ例）
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   （requirements.txt がない場合は上記パッケージを個別にインストールしてください）

3. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（既存 OS 環境変数は保護されます）。
   - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主な必須 / 推奨環境変数:
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - OpenAI を使う機能: OPENAI_API_KEY
     - オプション:
       - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
       - LOG_LEVEL (DEBUG|INFO|...)
       - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
       - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
       - PID_FILE_PATH, KILL_FLAG_PATH, PAPER_FILL_MODE（instant|partial|never|reject）
       - MONITOR_POLL_INTERVAL（run_monitoring 用、秒数、デフォルト 60）
   - .env の例（最小）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development

4. データディレクトリの作成
   - mkdir -p data
   - 実行時に DB やフラグファイルが作成されます。

5. 初期 DB スキーマ作成
   - 監視スクリプトや実行スクリプトは起動時に init_monitoring_db を呼びます。手動で作成する必要は通常ありません。

注意: 一部の機能は外部 API（kabuステーション、J-Quants、OpenAI）や OS 権限（プロセス優先度設定）に依存します。実行環境でこれらが利用可能か確認してください。

---

## 使い方

主要な起動方法とコマンド例:

1. 監視ループを起動（SystemMonitor のポーリング）
   - 簡単な起動:
     - python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数でオーバーライド:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視 DB を開きます。
   - 停止: data/stop_requested.flag ファイルを作成するとループは安全に終了します（外部から停止する用途）。

2. ExecutionEngine（注文実行エンジン）を起動
   - 通常起動:
     - python -m kabusys.run_execution
   - Paper Trading モード（モックブローカー・専用 DB を使用）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 停止: data/stop_requested.flag を作成するとエンジンが検知して停止します。
   - ExecutionEngine は起動時に data/execution.pid を書きます。run_execution は起動前に kill flag を検知した場合は起動を中止します。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定（デフォルト: data/paper_trading.db）:
     - python -m kabusys.tools.paper_verification_report --db path/to/db

4. ニュース NLP / レジーム判定（API キー必要）
   - kabusys.ai.score_news または kabusys.ai.regime_detector.score_regime をプログラムから呼び出す。OpenAI API キーが必要です。
   - コマンドラインエントリポイントは用意されていません（関数呼び出しを想定）。

5. Streamlit ダッシュボード（監視用 UI）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - DB は read-only で開かれます。MonitoringEngine がデータを埋めている必要があります。

6. kill.flag（緊急停止）の扱い
   - KillSwitch は条件が成立した場合（例: ドローダウン閾値超過）に data/kill.flag を書き込み、ExecutionEngine に停止を促します。
   - kill.flag を手動でクリアする（ExecutionEngine 起動前に）にはファイル削除または KillSwitch.clear() を使用してください。
   - デフォルトパスは Settings.kill_flag_path（デフォルト: data/kill.flag）。

ログ・デバッグ:
- LOG_LEVEL 環境変数でログ出力レベルを調整できます（INFO デフォルト）。
- 各モジュールは logging を使用しており、標準出力に情報・エラーを出力します。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なディレクトリ/ファイル（src/kabusys 下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・Settings 管理（.env 自動読み込み）
  - run_monitoring.py             — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - utils/
    - process_priority.py         — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py            — SQLite スキーマ・監視ログ CRUD
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ...（broker_factory, execution_engine, order_repository 等）
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
  - data/ (実行時に利用される、リポジトリルートの data ディレクトリ)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper trading 用)
    - kabusys.duckdb (DuckDB)

この README は主要モジュールの概観を示すための要約です。より詳細な挙動・パラメータ・設計上の注意点は各モジュールの docstring（ソースコード内コメント）を参照してください。

---

## 開発・運用上の補足メモ

- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。
  - OS 環境変数は保護され .env.local の override は可能ですが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます（テスト用途等）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 sqlite にデータを保存して本番 DB と完全分離します。
- OpenAI 呼び出し:
  - news_nlp / regime_detector は OpenAI API を利用します。API 呼び出しにはリトライ・バックオフ・レスポンス検証・スコアのクリップなど安全策が実装されていますが、API キーは必須です。
- 権限関連:
  - set_process_priority はプラットフォームと権限に依存します。psutil で権限不足時は警告を出して処理をスキップします。
- フラグファイル:
  - 運用上、stop_requested.flag（外部停止）・kill.flag（KillSwitch）・execution.pid（実行中 PID）などのフラグを利用しています。これらのファイルの取り扱いに注意してください。

---

必要であれば、この README をベースにインストール手順（OS 固有の注意点）、CI / テストの説明、より詳細な運用手順（データバックアップ、DB マイグレーション、ログローテーション）を追加できます。どの情報を拡張したいか教えてください。