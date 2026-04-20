KabuSys — README
=================

概要
----
KabuSys は日本株自動売買システムのライブラリ兼起動スクリプト群です。本プロジェクトは以下の主要機能を持ちます。

- 自動発注エンジン（ExecutionEngine） — 実口座／ペーパートレード双方に対応  
- 監視（Monitoring） — システム稼働状況・データ鮮度・注文挙動・リスク監視と Kill Switch  
- ポートフォリオ構築（Portfolio） — 候補選定、重み計算、ポジションサイジング、セクター制限などの純粋関数群  
- リサーチ（Research） — DuckDB を用いたファクター計算・特徴量解析  
- AI モジュール — ニュース NLP によるセンチメントスコアリング、レジーム検出（OpenAI 利用）  
- 運用用ツール群 — 設定ウィザード、設定検証、ペーパートレード検証レポートなど

機能一覧
--------
主なモジュールと役割（抜粋）：

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db を使用）
  - run_monitoring.py — SystemMonitor（および MonitoringEngine）用のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔を指定可能
- 設定・ユーティリティ
  - config.py — 環境変数とデフォルトの取り扱い、Settings クラス
  - config_setup.py — 対話式 .env 生成・更新ウィザード
  - validate_config.py — 起動前の設定チェック CLI（--strict オプションあり）
  - utils.logging_setup — 統一的なログ設定（stdout + 日次ローテートファイル）
  - utils.process_priority — プロセス優先度 / CPU affinity 設定ヘルパ
- 監視（monitoring）
  - monitoring_db.py — SQLite ベースの永続化層（テーブル作成・マイグレーション含む）
  - monitoring_engine.py — 各種 Monitor を束ねるポーリングエンジン
  - system_monitor.py / risk_monitor.py / kill_switch.py / … — システム稼働・リスク監視・Kill Switch 実装
- 実行（execution）
  - ExecutionEngine、OrderManager、RiskManager、Reconciler 等（発注ロジック・リスク制御）
  - broker_factory — 本番ブローカー / MockBroker の切り替え
- ポートフォリオ（portfolio）
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 候補選定・重み付け・株数算出・セクター制限等
- 研究（research）
  - factor_research.py, feature_exploration.py — ファクター計算、将来リターン、IC、統計サマリー
- AI（ai）
  - news_nlp.py — ニュース記事を OpenAI に送信して銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector.py — MA とマクロセンチメントを合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレードの検証レポート生成

セットアップ手順
----------------

1. Python 環境の準備
   - 推奨: Python 3.10+ の仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール
   - 必要なパッケージ（例）
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証を利用する場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実際の requirements.txt がある場合はそれに従ってください。パッケージ名やバージョンは運用環境やパッケージ管理に合わせて調整してください。

3. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは手動でルートに .env を作成してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨（よく使われる）環境変数（デフォルトがあるものも含む）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db (paper_trading 時)
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能を使う場合必須
     - PAPER_FILL_MODE — instant | partial | never | reject （paper_trading の約定挙動）

4. 設定検証（起動前必須推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリとログディレクトリの作成（必要に応じて）
   - デフォルトでは data/ と logs/ を使用します。起動時に自動作成されることもありますが、権限等に注意してください。

使い方
-----

基本的な起動例（ローカルで手動起動する想定）:

- ExecutionEngine（発注エンジン）を起動
  - KABUSYS_ENV の挙動:
    - paper_trading: MockBroker を使用し data/paper_trading.db に記録（本番 DB と完全分離）
    - live: 本番ブローカーで実行（設定の確認を厳重に）
  - コマンド:
    - python -m kabusys.run_execution

- Monitoring（監視プロセス）を起動
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は Settings に基づき sqlite_path（monitoring DB）および duckdb を使用します。
  - 監視中に data/stop_requested.flag が存在するとループが終了します。

- 設定ウィザード（.env の生成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成
  - 指定期間のレポートを標準出力に出す:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュール（ニューススコアリング / レジーム検出）
  - ai.news_nlp.score_news / ai.regime_detector.score_regime を DuckDB 接続とターゲット日付、OPENAI_API_KEY を指定して呼び出します。
  - 例（ライブラリ利用）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=os.environ["OPENAI_API_KEY"])

Kill Switch / 停止フロー
- ExecutionEngine を停止させるには data/kill.flag を作成して Kill Switch を発動させる運用を想定しています。
- run_monitoring/run_execution はそれぞれ data/stop_requested.flag を監視し、存在すると終了します。
- Settings.kill_flag_clear_on_start が 1 のときは起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。
- デフォルトログディレクトリ: logs/
- 各アプリケーションごとに logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）へ日次ローテートで保存されます。

ディレクトリ構成
----------------
（主要ファイル・ディレクトリのツリー概要）

- .env (プロジェクトルートに置く環境変数ファイル、.git にコミットしないこと)
- data/
  - monitoring.db (デフォルト: SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kill.flag, stop_requested.flag, execution.pid など（運用フラグ / PID）
- logs/
  - execution.log, monitoring.log, ...（日次ローテーション）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - (trade_monitor.py など監視関連モジュール)
    - execution/
      - (ExecutionEngine, OrderManager, RiskManager, broker_factory など)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/ (DB スキーマ/パイプライン関連モジュールがここにある想定)
    - その他モジュール（data.stats 等）

補足・運用上の注意
-----------------
- KABUSYS_ENV を live に設定すると本番動作になります。LINE 通知等の設定が未完のまま本番に入らないよう validate_config で確認してください。特に OPENAI_API_KEY / KABU_API_PASSWORD / JQUANTS_REFRESH_TOKEN 等必須値が設定されていることを確認してください。
- run_execution / run_monitoring はそれぞれプロセス優先度（high）を設定しようとします。実行環境で権限がない場合は警告が出て続行します。
- DuckDB/SQLite のパスは Settings によりデフォルトが設定されています。運用時は適切な場所・永続領域を指定してください。
- AI（OpenAI）関連は API 利用料が発生します。API キーと使用ポリシーに注意して運用してください。
- .env は機密情報を含むため絶対にバージョン管理にコミットしないでください（config_setup もその旨を警告します）。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報やコントリビュート方法はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合は管理者に確認してください）。

問い合わせ
--------
- 実装の詳細や運用についてはコード内の docstring / コメントを参照してください。特に各モジュールには設計方針と注意点が明記されています。
- 起動や設定についてのトラブルは validate_config の出力と logs/ のログを確認のうえお問い合わせください。

以上。必要であれば README に含める実例コマンドや .env のサンプルテンプレート（プレースホルダ）を追記します。どの情報を追加したいか教えてください。