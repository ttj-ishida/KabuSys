KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買に関するコンポーネント群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助機能など）を集めたパッケージです。本リポジトリは純粋関数群や DB 永続層、外部 API（証券ブローカー・OpenAI など）呼び出しを組み合わせて、現物自動売買ワークフローを提供します。

主な設計方針
- DuckDB / SQLite をデータ層に利用（分析用と監視用を分離）
- 実行（Execution）と監視（Monitoring）は別プロセスとして動かす
- Paper Trading（検証）モードは本番 DB と分離して安全に検証可能
- OpenAI を用いたニュース NLP / レジーム判定は API キー必須、失敗時はフェイルセーフ動作

機能一覧
---------
- ExecutionEngine 起動スクリプト（run_execution）:
  - ブローカークライアント（実口座 or モック）を用いた注文発行・状態管理
  - リスク管理、オーダー管理、再コンシリエーション機能
- MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor:
  - システムリソース、データ鮮度、滞留注文、約定異常、ドローダウン等の監視
  - SQLite ベースの監視ログ（monitoring.db）保存
  - LINE への通知（AlertManager）
  - KillSwitch による Execution 停止シグナル生成（data/kill.flag）
- AI 機能:
  - news_nlp: raw_news を LLM（gpt-4o-mini など）でセンチメント評価し ai_scores に保存
  - regime_detector: ETF 乖離 + マクロニュースの LLM 評価を合成して市場レジーム判定
- 研究用モジュール:
  - factor_research, feature_exploration: ファクター計算・将来リターン / IC / 統計サマリ
- ポートフォリオ構築:
  - 候補選定・重み付け・セクター制約・ポジションサイジング（単元丸め等）
- ユーティリティ:
  - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml）
  - プロセス優先度・CPU アフィニティ設定
- ツール:
  - paper_verification_report: Paper Trading DB から検証レポート生成
  - streamlit_dashboard: 監視ダッシュボード（Streamlit）

セットアップ手順
----------------
1. リポジトリをクローンしてプロジェクトルートへ移動
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

2. Python 環境の作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主な依存例:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （本リポジトリに requirements.txt が無い場合は上記パッケージを個別にインストールしてください）

4. 環境変数 / .env の準備
   - プロジェクトルートの .env（および .env.local）が自動読み込みされます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API（必須箇所で必要）
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（注文実行時に必須）
     - OPENAI_API_KEY — OpenAI を使用する機能で必要
     - KABUSYS_ENV — 起動環境: development | paper_trading | live （デフォルト: development）
     - PAPER_FILL_MODE — paper_trading 時の成行/約定挙動（instant|partial|never|reject、デフォルト: instant）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB パス（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH — KillSwitch のフラグファイル（デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL — 監視ループの秒間隔（デフォルト: 60）
   - .env のパースは shell ライクな形式（export KEY=val, quoted values, コメント）に対応します。

5. データディレクトリの作成
   - デフォルトで data/ 以下を使用するため、必要に応じて data/ を作成してください。多くの起動処理で存在しない場合に自動作成されますが、権限等に注意してください。

使い方（コマンド例）
------------------

- 監視プロセス起動（Monitoring）
  - 環境変数：MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 実行:
    - python -m kabusys.run_monitoring
  - 動作:
    - PID/kill flag とは無関係に監視用に本番 sqlite_path を参照（監視ログは常に本番 DB に記録）

- 実行エンジン起動（Execution）
  - KABUSYS_ENV が paper_trading の場合はモックブローカーを使用し、paper_sqlite_path（data/paper_trading.db）へ記録します（本番 DB と完全分離）
  - 実行:
    - python -m kabusys.run_execution

- Paper Trading 検証レポート
  - sqlite (paper_trading) から各種指標を集計して判定を出力
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db で DB パスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- 監視ダッシュボード（Streamlit）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で SQLite を開き、Overview / Positions / Orders / System タブを表示します

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必要
  - 関数を直接呼び出して利用（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）
  - API 呼び出しに失敗してもフェイルセーフ（ゼロやスキップ）で継続する設計

重要な挙動・注意点
-----------------
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local をロードします。
  - OS 環境変数は保護され、.env.local は .env を上書きできます。
- Paper Trading と本番 DB は分離:
  - KABUSYS_ENV=paper_trading のとき、デフォルトで data/paper_trading.db を使用
- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔を秒で指定。0 以下や不正な値はデフォルト（60秒）にフォールバック。
- PID / Kill Flag:
  - ExecutionEngine は pid_file を生成（Settings.pid_file_path、デフォルト data/execution.pid）。SystemMonitor はこの PID を監視し、stale PID を検出すると削除してリスクログに記録します。
  - KillSwitch は data/kill.flag を作成して ExecutionEngine に停止指示を出す仕組み（KillSwitch.clear() によるクリアや起動時に Settings.kill_flag_clear_on_start を使ってクリアする挙動がある構成も想定）。
- OpenAI 呼び出し:
  - LLM 呼び出しはリトライ（指数バックオフ）あり。429・ネットワーク断・タイムアウト・5xx はリトライ対象。
  - 応答のバリデーションを厳格に行い、失敗時は安全側動作（スコア 0.0 / スキップ）で継続します。
- DB マイグレーション:
  - init_monitoring_db() は冪等で、既存テーブルにカラムがない場合は ALTER TABLE による簡単なマイグレーションを行います（例: trade_logs.latency_ms, dashboard.peak_value）。

ディレクトリ構成（主なファイル）
--------------------------------
以下は本コードベースでの主要なモジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py — Settings / .env 自動読み込みロジック
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - alert_manager.py — LINE 通知ユーティリティ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, ...（注文管理／リコン機能）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（単元丸め・集約 cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py — ETF MA 乖離 + マクロニュースでレジーム判定
  - utils/
    - process_priority.py — プロセス優先度 / CPU アフィニティ設定

サンプル .env（最小例）
----------------------
# KabuSys example .env
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb

開発・デバッグのヒント
---------------------
- run_monitoring は監視テーブルの初期化を行うため、初回起動で monitoring.db を作成します。
- Paper Trading の検証を行う場合は KABUSYS_ENV=paper_trading を設定すると、本番 DB を汚さずに data/paper_trading.db を利用できます。
- AI 機能や外部 API を利用しない単体テスト / 開発は環境変数 OPENAI_API_KEY を設定せず、該当機能を Mock して実行できます（news_nlp._call_openai_api 等をテスト時に差し替え可能）。
- process_priority は OS に依存するため、権限不足等で警告が出ることがあります（動作継続します）。

ライセンス・貢献
----------------
本ドキュメントはコードベースの README です。実装コードのライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

付記
----
この README は現在コードベースに含まれる主要機能・設定を要約したものです。各モジュールの詳細な挙動や API（引数・戻り値）については該当モジュールの docstring を参照してください。必要であれば運用手順（systemd ユニット例、監視ポリシー、バックアップ方針 等）を別途作成します。