KabuSys
=======

日本株自動売買システム（KabuSys）のリポジトリ用 README。  
このドキュメントはリポジトリ内の主要スクリプト・モジュールから自動的に要点をまとめています。開発／ローカル実行に必要な手順、主要機能、ディレクトリ構成を日本語で説明します。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買プラットフォーム（研究・シグナル計算・ポートフォリオ設計・発注エンジン・監視・AI を使ったニュース解析など）を構成する Python パッケージです。DuckDB / SQLite をデータレイヤに使い、kabuステーション等のブローカ API またはペーパートレード向けのモックを通じて注文を実行します。OpenAI を用いたニュース NLP や市場レジーム判定を行う機能も含みます。

主な特徴（機能一覧）
------------------
- 環境設定ウィザード（.env の対話式作成）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の事前チェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（実発注 / ペーパートレード対応）: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - 起動時にプロセス優先度を上げる処理あり
- Monitoring（監視）: run_monitoring.py と監視コンポーネント群
  - システム状態・データ鮮度・注文状態・リスク監視（ドローダウン・ポジション数上限等）
  - Kill Switch（data/kill.flag）で ExecutionEngine を停止可能
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- ポートフォリオ構築ユーティリティ
  - 候補選定・等分配／スコア重み配分
  - セクター上限適用、レジーム乗数
  - 株数決定（単元株丸め、リスクベース配分、aggregate cap のスケーリング）
- リサーチ（DuckDB を用いたファクター計算）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI モジュール
  - ニュース記事のセンチメントスコア化（OpenAI を利用）: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（ma200 とマクロニュースの合成）: kabusys.ai.regime_detector.score_regime
  - API の呼び出しはリトライやフェイルセーフ機能を持つ
- ツール
  - Paper Trading 検証レポート生成スクリプト（orders / monitoring データを集計して PASS/FAIL 判定）: kabusys.tools.paper_verification_report

セットアップ手順
----------------

1. Python 環境
   - Python 3.9+ を推奨（環境に合わせて調整してください）。

2. 必要パッケージ（例）
   - pip でインストール（最低限）:
     - duckdb
     - psutil
     - openai
     - pyyaml（config YAML 検証に必要、任意）
   例:
     pip install duckdb psutil openai pyyaml

3. リポジトリルートに移動して .env を用意
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - 既存 .env を手動で作る場合は .env.example を参考にしてください（このリポジトリ内に例がある場合）。

4. 環境変数（重要なもの）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨／任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパー用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動で消すか、0/1）
     - PAPER_FILL_MODE（instant|partial|never|reject、ペーパートレードの約定動作）
     - LOG_DIR（ログ保存先、デフォルト logs/）
   - 注意: .env 自動読み込みはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. データディレクトリ
   - デフォルトでは data/ 以下に DB やフラグファイルが置かれます（例: data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db）。
   - logs/ にアプリログが日次ローテーションで出力されます。

使い方（主要コマンド例）
-----------------------

- 環境設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml をチェック）
  python -m kabusys.validate_config
  # 厳格モード（警告も失敗扱い）
  python -m kabusys.validate_config --strict

- ExecutionEngine を手動起動（本番／ペーパー設定に従う）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB に記録され、MockBrokerClient が使用されます。
  - 起動時に data/execution.pid が作成されます（PID 管理）。
  - 停止方法のひとつ: data/stop_requested.flag を作成すると安全にスレッドを停止します。
  - Kill Switch（data/kill.flag）が書き込まれるとエンジン停止を促す設計です。

- Monitoring を起動（監視ループ）
  python -m kabusys.run_monitoring
  - デフォルトポーリング間隔 60 秒。MONITOR_POLL_INTERVAL 環境変数で変更可（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（監視用 DB）を使用します（監視は環境に依らず本番 sqlite_path を参照）。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で別パス指定可。

- AI スコア生成（プログラムから呼ぶ例）
  from kabusys.ai.news_nlp import score_news
  score_news(duckdb_conn, target_date, api_key="...")

  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="...")

ログ
----
- 共通のログ初期化: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
- デフォルト: logs/<app_name>.log に日次ローテーション（30日分保持）
- コンソール出力は stdout に出ます

停止・Kill Switch・制御フラグ
-----------------------------
- data/stop_requested.flag: run_execution/run_monitoring が確認する停止フラグ（手動停止用）。
- data/kill.flag: KillSwitch が書き込むと ExecutionEngine 停止トリガーになる（本番では慎重に扱う）。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では推奨されません）。

開発・デバッグ向けメモ
---------------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定ファイル（config/*.yaml）は generate スクリプト等で生成する想定。PyYAML がないと YAML 内容検証はスキップされます。
- psutil を使ってプロセス優先度・CPU affinity を設定しています。プラットフォーム依存の挙動に注意してください（権限によっては設定に失敗することがあります）。

ディレクトリ構成（主なファイル/モジュール）
---------------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定管理
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring 起動スクリプト

subpackages:
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）を使ったセンチメントスコア処理
  - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py        — SQLite を使った監視ログ永続化層
  - monitoring_engine.py    — 複数モニタを束ねるエンジン
  - system_monitor.py       — システム状態・データ鮮度監視
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — Kill Switch（フラグファイル管理）
  - alert_manager.py        — （参照される）通知管理（LINE 等）
  - trade_monitor.py        — 注文関連の監視（滞留注文、約定異常等）
- execution/
  - execution_engine.py     — 実際の発注セッションを管理するエンジン
  - order_manager.py        — 注文管理ロジック
  - order_repository.py     — 発注ログ永続化
  - reconciler.py           — ブローカ状態と DB の整合器
  - risk_manager.py         — 発注前リスク判定
  - broker_factory.py       — 実ブローカ / モッククライアント選択
- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 株数計算（リスク・単元丸め・スケーリング）
  - risk_adjustment.py      — セクターキャップ・レジーム乗数
- research/
  - factor_research.py      — ファクター計算（momentum / volatility / value）
  - feature_exploration.py  — IC / forward return / 統計サマリ
- utils/
  - logging_setup.py        — 共通ログ設定
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート出力

補足（運用上の注意）
------------------
- 本番環境（KABUSYS_ENV=live）での実行は慎重に行ってください。validate_config により本番向けのガード（LINE 通知の有無や kill_flag_clear_on_start の設定）をチェックできます。
- OpenAI API を利用する機能は API キーとコスト管理に注意してください。API 呼び出しはリトライやフェイルセーフがありますが、失敗時はデフォルト値にフォールバックする設計です。
- Paper Trading モードは本番 DB と完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。

ライセンス・貢献
----------------
- 本リポジトリのライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問い合わせ
----------
- 実装・設計に関する質問はリポジトリ内のドキュメント（README, docs/, comments）またはプロジェクト管理者にお問い合わせください。

以上がこのコードベースの概要と運用ガイドです。必要があれば、「特定モジュールの API 使用例」や「デプロイ手順（systemd / cron / Docker）」などの追加ドキュメントを作成しますか？