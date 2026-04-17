# KabuSys — README

このリポジトリは日本株自動売買プラットフォーム「KabuSys」の一部実装です。主にポートフォリオ構築、発注実行、監視、研究（ファクター計算）および AI ベースのニュース処理を含むモジュール群で構成されています。本 README はローカルでのセットアップ・起動方法、主要機能、ディレクトリ構成を日本語でまとめたものです。

重要: この README はコードベース（src/kabusys 以下）に基づくもので、実行には外部 API キー（OpenAI 等）や適切な環境変数の設定、必要なパッケージのインストールが必要です。

## プロジェクト概要
KabuSys は以下を目的としたモジュール群を提供します。

- シグナルに基づくポートフォリオ構築（候補選定・重み付け・ポジションサイズ決定）
- 発注の実行管理（OrderManager / ExecutionEngine）とブローカー抽象化
- 実行・注文の再同期間合（Reconciler）
- 監視コンポーネント（System / Trade / Risk Monitor）、アラート配信（LINE）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- ニュースの NLP スコアリング（OpenAI を利用）
- 市場レジーム判定（MA と LLM ベースのハイブリッド）
- 研究用途のファクター計算・特徴量評価ユーティリティ（DuckDB ベース）

設計上のポイント:
- Paper Trading は本番 DB と分離（data/paper_trading.db 等）。
- 監視ログは SQLite（デフォルト: data/monitoring.db）で永続化。
- DuckDB をデータ分析・ファクター計算に利用。
- .env / .env.local を自動読み込み（プロジェクトルートが検出できる場合）。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

## 機能一覧
主な機能（モジュールと役割）

- kabusys.config
  - 環境変数の読み込み/管理。KABUSYS_ENV（development/paper_trading/live）や DB パス等を提供。
- kabusys.portfolio
  - 銘柄選定: select_candidates
  - 重み算出: calc_equal_weights / calc_score_weights
  - リスク調整: apply_sector_cap / calc_regime_multiplier
  - 株数決定: calc_position_sizes（単元丸め・集約キャップ等）
- kabusys.execution
  - OrderManager / ExecutionEngine / Reconciler / OrderRepository 等（発注・状態管理）
- kabusys.monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - MonitoringEngine：各 Monitor を束ねるポーリングループ
  - monitoring_db：監視用 SQLite スキーマ/読み書きユーティリティ
  - streamlit_dashboard：監視ダッシュボード（Streamlit）
- kabusys.ai
  - news_nlp.score_news：ニュースを LLM でスコアリングして ai_scores に書き込み
  - regime_detector.score_regime：市場レジーム判定（MA + LLM）を market_regime に保存
- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary
- ユーティリティ
  - process_priority（プロセス優先度設定 / CPU affinity）
- ツール
  - tools.paper_verification_report：Paper Trading DB から検証レポートを生成

## セットアップ手順（ローカル）
1. Python 環境
   - 推奨: Python 3.9+（コード中での型注釈等に合わせる）
   - 仮想環境の作成（例）:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（最低限）
   - 本リポジトリに requirements.txt がない場合は次のパッケージを手動で入れる必要があります:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit (ダッシュボード利用時)
   - 例: pip install duckdb psutil openai requests streamlit

3. プロジェクトルートに .env を配置（任意）
   - .env.example があれば参照して作成してください（本リポジトリには example がない場合があります）。
   - 自動読み込み: プロジェクトルートが .git または pyproject.toml を含むと自動で .env / .env.local を読み込みます。
   - 自動読み込みを無効にするには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必要な環境変数（主要）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - PAPER_FILL_MODE: paper trading の fill 動作（instant|partial|never|reject、デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定（任意）
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）

5. データディレクトリ
   - data/ ディレクトリを作成しておく（PID ファイルや DB の出力先）。多くのコードは data/ 以下を想定しています。
     - mkdir -p data

## 使い方（起動・実行例）
以下は代表的な起動方法です。必要な環境変数を設定してから実行してください。

1. 監視ループの起動（監視プロセス）
   - python -m kabusys.run_monitoring
   - 補足:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）。
     - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）の DB を使用します（KABUSYS_ENV に関係なく本番の sqlite_path を使用する点に注意）。
     - 停止するには project_root/data/stop_requested.flag を作成する（手動停止用）。run_monitoring はこのファイルの存在を監視し、検出するとループを終了します。

2. 実行エンジン（ExecutionEngine）の起動
   - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使って paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）に記録し、本番 DB と分離されます。
     - 実行中の PID は data/execution.pid（デフォルト）に書き込まれます。
     - 停止フラグ: project_root/data/stop_requested.flag を作成すると実行エンジンは安全に停止します。
     - 監視側の KillSwitch は条件により data/kill.flag を書き込むことがあり、ExecutionEngine は kill_flag を参照して停止する設計になっています（Settings.kill_flag_path のパスを使用）。

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を指定する場合:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - 目的: 稼働率、注文成功率、送信率、レイテンシ（P95）などを出力し PASS/FAIL 判定を行います。

4. 監視ダッシュボード（Streamlit）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは監視用 SQLite を読み取り専用で開きます（DB がない場合はエラー表示）。

5. AI 関連（プログラム呼び出し）
   - ニューススコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key=...)
   - レジームスコア:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=...)
   - いずれも OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）。

## 主要ファイル / ディレクトリ構成
（src/kabusys 以下を凝縮して記載）

- src/kabusys/
  - __init__.py (パッケージ情報)
  - config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py  — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリング（ai_scores 書込）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数決定・資金配分
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラ / バリューなどのファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等
  - execution/
    - order_manager.py, reconciler.py, ... — 発注管理・再同期間合ロジック（Broker インタフェースを介す）
  - monitoring/
    - monitoring_db.py — SQLite スキーマと永続化 API
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py — LINE push 通知ユーティリティ
    - kill_switch.py — 条件評価→ data/kill.flag 書込ロジック
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定

- data/ (想定出力ディレクトリ、手動で作成)
  - monitoring.db (監視ログ SQLite)
  - paper_trading.db (Paper Trading 用 SQLite)
  - kabusys.duckdb (DuckDB データ)
  - execution.pid, stop_requested.flag, kill.flag などのランタイム制御ファイル

## 主要環境変数（要約）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- SQLITE_PATH: 監視 SQLite（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の注文振る舞い）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 各外部 API の認証に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager での通知に必要

## 運用上の注意点 / 実装上の留意点
- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading の場合、run_execution は paper_sqlite_path を使用しますが、run_monitoring は常に Settings.sqlite_path（監視 DB）を使用します。
- 停止フラグ:
  - stop_requested.flag: 手動で作成すると run_monitoring / run_execution のループが終了します（両スクリプトが存在チェックを行う）。
  - kill.flag: Monitoring の KillSwitch が条件を満たすと書き込み、ExecutionEngine は設定された kill_flag_path（デフォルト data/kill.flag）を参照して停止する仕組みです。
- .env の自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml）。CI/テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- process priority 設定はプラットフォーム依存で失敗する場合があるため、失敗時は警告が出て処理は継続します（set_process_priority を呼び出しているスクリプトは例: run_monitoring / run_execution）。
- OpenAI など外部 API はレート制限や不安定性に備え、エクスポネンシャルバックオフやフォールバック（失敗時は安全側の値を使用）を実装しています。API キーの取り扱い（秘密管理）に注意してください。

## 開発・拡張のヒント
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）に適切なデータを用意することで、research および AI モジュールをローカルで検証できます。
- unit テストを書く場合、AI 呼び出し部分は _call_openai_api を patch（モック）して外部依存を排除できます（コード内にテスト用の patch 指示あり）。
- position sizing の lot_size や cost_buffer 等パラメータは Engine/戦略側から渡すことで柔軟に調整できます。

---

問題が発生したり追加のドキュメント（API 詳細、DB スキーマ、運用手順など）が必要な場合は、どの部分を深掘りしたいか教えてください。具体的なコマンド例や .env のテンプレート、運用フロー図なども作成できます。