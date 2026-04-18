KabuSys
=======

日本株向けの自動売買 / リサーチ基盤ライブラリ（モジュール群）です。  
本リポジトリは発注エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ポートフォリオ構築、ファクター計算、AIベースのニュースセンチメント等を含みます。  
以下は開発者・運用者向けの使い方・セットアップ説明です。

概要
----
KabuSys は次の主要機能を持ちます。

- ExecutionEngine（run_execution）: ブローカーとの接続、注文管理、リスク制御を行う実行エンジン。  
  KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 用 DB に記録します（本番 DB と分離）。
- Monitoring（run_monitoring）: システムリソース、データ鮮度、注文ログ等を定期ポーリングしてログとアラート（Kill Switch）を管理します。  
  監視は常に本番用の sqlite_path を参照して永続化します。
- Portfolio construction: シグナルから候補選定、重み付け、株数算出（単元丸め・資金制約・リスク制限）までの純粋関数群を提供します。
- Research: DuckDB を使ったファクター計算、将来リターンや IC 計算、統計サマリ等の分析ユーティリティ。
- AI モジュール: OpenAI を使ったニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）。
- ユーティリティ: ロギング設定、プロセス優先度設定、.env ウィザード、設定検証ツールなど。
- 運用ツール: Paper Trading の検証レポート生成スクリプトなど。

主な機能一覧
--------------
- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動
  - python -m kabusys.run_monitoring : Monitoring のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 設定関連
  - python -m kabusys.config_setup : .env を対話式に生成/更新するウィザード
  - python -m kabusys.validate_config : .env / config/*.yaml の事前検証
- 運用ツール
  - python -m kabusys.tools.paper_verification_report : Paper Trading DB から検証レポートを生成
- ポートフォリオ関連（ライブラリ関数）
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（単元丸め・投下上限・スケールダウンロジック）
  - apply_sector_cap, calc_regime_multiplier
- Research（DuckDB 接続を受け取る純粋関数）
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary
- AI
  - news_nlp.score_news: raw_news → ai_scores（OpenAI API 必須）
  - regime_detector.score_regime: マクロ記事 + ETF MA を合成して market_regime を更新
- 監視 DB 層
  - monitoring_db.init_monitoring_db: 必要テーブルの作成と簡易マイグレーション
  - MonitoringDB クラス: system_status / trade_logs / positions / risk_logs / dashboard の読み書き

セットアップ手順
----------------

1. リポジトリをクローンし、Python 仮想環境を用意
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - duckdb, psutil, openai, PyYAML（validate_config の YAML 検証用）などが利用されます。
   - 例（pip）:
     - pip install duckdb psutil openai PyYAML

   ※ 実際の requirements.txt はリポジトリに合わせて用意してください。

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成（.env は絶対に Git にコミットしないでください）。

4. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
   - KABU_API_PASSWORD（kabuステーション API パスワード）
   - OPENAI_API_KEY（AI 機能を使う場合。news_nlp / regime_detector）
   - その他（任意・デフォルトあり）:
     - KABUSYS_ENV（development / paper_trading / live） — デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL（監視のポーリング間隔、秒、デフォルト 60）

5. データディレクトリ作成（必要に応じて）
   - data/ （DB、PID/flag ファイル用）
   - logs/ （ログ出力用。logging_setup が自動作成することもあります）

使い方（主要コマンド）
---------------------

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証（起動前に推奨）
  - python -m kabusys.validate_config
  - 警告を厳格に扱う場合は --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite に接続（PAPER_TRADING_SQLITE_PATH）
    - ブローカークライアント生成（Mock／実ブローカーは Settings に依存）
    - ExecutionEngine.run_session をデーモンスレッドで実行。data/stop_requested.flag を検知すると停止
    - 起動前に stop flag が立っている場合は起動せず終了

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 動作:
    - Settings に基づき監視用の SQLite（monitoring.db）と DuckDB に接続
    - SystemMonitor.check_once を定期的に呼ぶ（デフォルト 60 秒）
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（正の整数、デフォルト = 60）
    - 停止はプロジェクトルート/data/stop_requested.flag による

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で上書き可。

- AI モジュール（プログラム内から呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key を省略すると OPENAI_API_KEY を参照
    - DuckDB 接続（raw_news / news_symbols / ai_scores が前提）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に OpenAI を使う

設定（主な環境変数）
-------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- OPENAI_API_KEY: AI 機能利用時に必要
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- LOG_DIR: ログ格納ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等は Settings 経由で参照

停止・Kill Switch（運用メモ）
---------------------------
- 強制停止フラグ（Execution 停止トリガ）
  - KillSwitch はリスクアラート等の条件を満たすと data/kill.flag を書き込みます。ExecutionEngine 起動時にこのフラグを検知すると起動を阻止できます（設定により起動時に自動クリアすることも可能）。
- run_execution / run_monitoring の停止
  - 実行中スクリプトは data/stop_requested.flag を監視しており、ファイルの存在を検知するとループを抜けて安全終了します。
  - 手動で停止する場合は .pid ファイルを参照してプロセスにシグナル送付するか stop_requested.flag を作成してください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール一覧（抜粋）です。

- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring ポーリング起動スクリプト
- config.py                  — Settings と自動 .env ロード
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 起動前検証 CLI
- __init__.py

- utils/
  - logging_setup.py         — 統一ログ設定（stdout + 日次ファイルローテーション）
  - process_priority.py      — プロセス優先度・CPU affinity 設定

- monitoring/
  - monitoring_db.py         — SQLite 永続化層（テーブル作成・Migration・MonitoringDB）
  - system_monitor.py        — システム状態・データ鮮度チェック
  - trade_monitor.py         — （注文関連監視ロジック）
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — kill.flag 管理
  - monitoring_engine.py     — 複数モニタの束ね処理とアラート評価
  - alert_manager.py         — （アラート通知の統合、LINE 等の出力先）

- execution/
  - execution_engine.py      — ExecutionEngine（注文実行ロジック）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py

- ai/
  - news_nlp.py              — ニュースセンチメント取得（OpenAI）
  - regime_detector.py       — 市場レジーム判定（OpenAI + MA 指標）

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

運用上の注意
-------------
- .env は機密情報を含みます。Git 管理には絶対に含めないでください。config_setup で生成するファイルにも注意してください。
- KABUSYS_ENV=live の設定は本番稼働扱いです。validate_config で追加の警告チェックが入ります。
- OpenAI 関連は API 使用制限 / コストに注意のこと。エラー時はフェイルセーフで継続する設計です（多くの箇所で 0.0 等のフォールバックを採用）。
- monitoring はデフォルトで監視 DB（SQLITE_PATH）を使用します。paper_trading 環境でも監視は production sqlite_path を参照する点に注意してください（コード設計に基づく挙動）。

開発向けメモ
-------------
- DuckDB 接続を渡して純粋関数で解析を行う設計になっています。分析処理は副作用を持たないため単体テストが容易です。
- 各モジュールのエントリポイント（run_*.py）は setup_logging と set_process_priority を最初に呼び出します。ロギングを有効にして実行してください。
- monitoring_db.init_monitoring_db は既存 DB に対して簡易マイグレーション（列追加など）を行います。

問い合わせ / 貢献
------------------
- バグ報告・機能提案は issue を立ててください。開発ポリシーやテスト方針に従って PR を歓迎します。

以上が本プロジェクトの概要と運用手順です。必要であれば README にチュートリアル（起動例、環境変数テンプレート、よくあるトラブルシュート）を追加します。どの情報を優先して詳述したいか教えてください。