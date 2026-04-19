KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python ベースのシステムです。  
このリポジトリは注文実行エンジン、監視コンポーネント、ポートフォリオ構築・リスク管理ロジック、研究用ファクター計算、および OpenAI を利用したニュース NLP / レジーム判定のユーティリティを含みます。

主な設計指針
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）を切替可能
- DB は DuckDB（分析用） と SQLite（監視・履歴用）を併用
- .env による環境変数管理（config_setup による対話式ウィザードあり）
- 監視側からの Kill Switch による安全停止
- OpenAI を使ったニュースセンチメント / レジーム判定（任意・APIキー必須）

機能一覧
---------
- execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - paper_trading モードでは MockBroker を使用し、本番 DB と分離された data/paper_trading.db を利用
  - リスク制御（RiskManager）、注文管理、リコンサイル機能
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor をまとめて定期実行する監視ループ（run_monitoring.py）
  - 監視ログの永続化（monitoring_db.py）
  - Kill Switch（リスク閾値超過時に data/kill.flag を作成して Execution を停止）
  - AlertManager を通した通知（実装に応じて LINE など）
- portfolio
  - 候補選定、重み計算、ポジションサイズ算出、セクターキャップ・レジーム乗数
- research
  - DuckDB を用いたファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）等の統計ツール
- ai
  - news_nlp: ニュース記事の LLM によるセンチメント評価・ai_scores への書き込み
  - regime_detector: MA とマクロニュースを組合せた市場レジーム判定
- tools
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定するレポート生成スクリプト
- utils
  - logging_setup: 統一ログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- 設定支援
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI

前提（推奨）
-----------
- Python 3.10+
  - (コード中に PEP 604 の型合併（|）が使われているため)
- 必要ライブラリ（例）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - pyyaml（設定ファイルの検証に利用）
- SQLite は標準ライブラリに同梱
- ネットワーク接続（kabuステーション API / J-Quants / OpenAI を利用する場合）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境の作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（最低限の例）
   - pip install duckdb psutil openai pyyaml
   - 実際のプロジェクトでは requirements.txt を用意している場合はそれを使ってください。

4. 環境変数 (.env) の初期作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（後述の必須変数を参照）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

6. DB 初期化
   - run_execution / run_monitoring 起動時に必要テーブルは自動で作成されます（monitoring 用テーブル等）。

主要な環境変数（重要）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用関連:
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使い paper_sqlite_path を使用します
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で必要
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring で上書き可能、デフォルト 60）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant | partial | never | reject

ログ / PID / フラグファイル
-------------------------
- ログ: logs/<app_name>.log （logging_setup による日次ローテーション）
- PID ファイル: data/execution.pid（ExecutionEngine が起動中の PID を保持）
- 停止要求フラグ（プロセス内部停止）:
  - data/stop_requested.flag — run_monitoring / run_execution のループ停止シグナルに使用
- Kill Switch:
  - data/kill.flag — KillSwitch が書き込むことで ExecutionEngine を停止させる（監視→書き込み）
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアするオプションあり（本番では非推奨）

使い方（主要コマンド）
--------------------
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB を使い MockBroker を利用します

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変えたい場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（例: ニューススコア付与 / レジーム判定）
  - これらはライブラリ API として利用できます（OpenAI APIキー必須）。
  - 例:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")

注意点・運用上のヒント
--------------------
- .env は機密情報を含むため Git にコミットしないでください（config_setup は冒頭に注意書きを出力します）。
- KABUSYS_ENV=live の場合は特に LINE 通知設定や Kill Switch の設定等を慎重に確認してください（validate_config が警告を出します）。
- paper_trading は発注ロジックの検証に便利ですが、設定ミスで本番 DB を汚さないよう PAPER_TRADING_SQLITE_PATH の確認を推奨します。
- OpenAI 呼び出しはレート制限や API 失敗に備えたリトライ実装がありますが、API キーの取り扱い・コスト管理を行ってください。
- ロギングは stdout とファイルの両方に出力されます（logs/<app>.log）。ログディレクトリ作成に失敗した場合はコンソールのみになります。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ宣言、バージョン
- config.py — 環境変数/.env ロードと Settings クラス
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）と ai_scores 書き込み
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 監視 DB 層
  - system_monitor.py — システム状態 / データ鮮度監視
  - trade_monitor.py — （発注取引監視）※（実装ファイルが存在する想定）
  - risk_monitor.py — ドローダウン / ポジション数監視
  - kill_switch.py — kill.flag 管理
  - monitoring_engine.py — 各モニタ統合ループ
  - alert_manager.py — （通知管理、実装に応じて）
- portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 発注株数算出
  - risk_adjustment.py — セクター上限、レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — 優先度 / CPU affinity 設定ユーティリティ

（補足）
- data/ ディレクトリ (実行時に作成)
  - data/monitoring.db（デフォルトの監視 SQLite）
  - data/paper_trading.db（paper_trading 用）
  - data/kabusys.duckdb（DuckDB デフォルト）
  - data/execution.pid, data/kill.flag, data/stop_requested.flag などの制御ファイル

ライセンス・貢献
----------------
- 本 README ではライセンス情報は含めていません。プロジェクトのルートに LICENSE ファイルを置いて管理してください。
- バグ報告や機能追加は issue / PR を通じて受け付けてください。

よくある質問（FAQ）
------------------
Q: paper_trading と live の DB は分離されていますか？  
A: はい。KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 SQLite と分離します。

Q: 監視ループの間隔は変更できますか？  
A: MONITOR_POLL_INTERVAL 環境変数で秒数を上書きできます（整数、1 以上）。デフォルトは 60 秒です。

Q: OpenAI を使いたくない場合は？  
A: OPENAI_API_KEY を設定しなければ AI 機能は使用されません。AI 機能を呼ぶコードを実行すると例外が出るため、その呼び出しを行わないでください。

最後に
-------
まずは python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で検証してから各コンポーネントを起動してください。運用時は logs を監視し、kill.flag / stop_requested.flag を使って安全にプロセスを停止できます。

必要であれば、この README をベースに「運用手順書」や「デプロイ手順（systemd / Docker / Supervisor）」のテンプレートも作成します。希望があれば教えてください。