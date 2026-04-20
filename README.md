README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。戦略のリサーチ（ファクター計算）、ポートフォリオ構築、注文実行、監視、Paper Trading 用検証ツール、そしてニュースを用いた AI スコアリング等の機能を含みます。設計方針として「本番 DB と Paper Trading の分離」「ルックアヘッドバイアス回避」「外部 API 呼び出しは明示的に制御」等を採用しています。

主な特徴
--------
- 環境変数ベースの設定管理（.env 自動読み込み、対話式ウィザードあり）
- ExecutionEngine（発注エンジン）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し paper_trading.db に記録
  - リスク管理、発注管理、再整合化（reconciler）を組み込む
- Monitoring（監視）
  - システム状態、注文状況、ドローダウン・ポジション上限を定期チェック
  - Kill Switch（条件を満たすと data/kill.flag を書いて Execution を停止）
  - ロギングと監視 DB（SQLite）への永続化
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）などの統計処理
- ポートフォリオ（portfolio）
  - 候補選定、重み付け（等重/スコア加重）、ポジションサイズ計算、セクターキャップ・レジーム乗数
- AI モジュール（ai）
  - ニュース記事を LLM（OpenAI）でスコア化し ai_scores に格納（batch、retry、検証を実装）
  - 市場レジーム判定（ETF の MA200 とマクロニュースの LLM スコアの合成）
- ユーティリティ
  - ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定
- ツール
  - Paper Trading の検証レポート生成スクリプト（期間指定可）
  - 設定検証 CLI（validate_config）

セットアップ
------------
1. Python
   - Python 3.10+ を推奨（typing の union 型等を使用）。
2. 依存パッケージ（最低限）
   - duckdb
   - psutil
   - openai
   - PyYAML（config/*.yaml の内容検証を行いたい場合）
   例:
     pip install duckdb psutil openai PyYAML
   （プロジェクトに requirements.txt がある場合はそちらを使用してください）
3. リポジトリの配置
   - プロジェクトルートに `data/`、`logs/` 等が自動作成されますが、config によっては事前に作る必要はありません。
4. 環境変数設定
   - 対話式ウィザードで .env を作成:
       python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）。
   - 自動ロードはデフォルトで有効（プロジェクトルートに .env があれば kabusys.config が起動時に読み込みます）。
   - 自動ロードを無効化する場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数（概要とデフォルト）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（monitoring） デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（paper_trading 時に使用） デフォルト: data/paper_trading.db
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） デフォルト: INFO
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject） デフォルト: instant
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒） デフォルト: 60
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1） デフォルト: 0
- PID ファイル / フラグファイル:
  - data/execution.pid（Execution の PID）
  - data/stop_requested.flag（run_* スクリプト側の停止フラグ）
  - data/kill.flag（KillSwitch による Execution 停止フラグ）

設定検証
--------
起動前に設定を検証できます:
  python -m kabusys.validate_config
厳格モード（警告も失敗扱い）:
  python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------
- ExecutionEngine 起動（デーモン/フォアグラウンドいずれも可）
  - 本番/開発/ペーパートレードは KABUSYS_ENV に依存
  - 実行:
      python -m kabusys.run_execution
  - ペーパートレード:
      export KABUSYS_ENV=paper_trading
      python -m kabusys.run_execution
    ペーパートレード時は専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。

- Monitoring 起動（ポーリングループ）
  - ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）。
  - 実行:
      python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - デフォルト DB は data/paper_trading.db（環境変数や --db で指定可）
  - 実行:
      python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または:
      python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- .env 設定ウィザード（対話式）
      python -m kabusys.config_setup

- AI モジュール（プログラムから直接呼び出す）
  - ニューススコアリング:
      from kabusys.ai.news_nlp import score_news
      score_news(conn, target_date, api_key=...)
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date, api_key=...)

運用上の注意
------------
- KABUSYS_ENV=live の場合は設定を慎重に確認してください（validate_config が警告を出します）。
- run_monitoring は監視用 sqlite_path を環境にかかわらず本番 sqlite_path（Settings.sqlite_path）で使用します（monitoring の観測対象は本番 DB を想定）。
- Paper Trading は本番 DB と完全に分離するため、PAPER_TRADING_SQLITE_PATH を明示的に設定すると安全です。
- Kill Switch（data/kill.flag）関連:
  - KillSwitch は RiskMonitor 等の判定で flag を書き込むことで ExecutionEngine 停止を誘発します。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険（自動クリアされるため）なので注意してください。
- OpenAI を使う機能を本番で運用する場合、API レート・課金・失敗時の挙動（フォールバックやリトライ）が考慮されていますが、適切なキー管理と monitoring を行ってください。

主要ディレクトリ構成
-------------------
（プロジェクトルートの src/kabusys 以下を抜粋）
- __init__.py
  - パッケージ情報（バージョン等）
- config.py
  - 環境変数・設定管理（.env 自動読み込み、Settings クラス）
- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 起動前設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - Monitoring ポーリングループ起動スクリプト
- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・永続化層
  - system_monitor.py: システム状態・データ鮮度チェック
  - trade_monitor.py: （発注/約定の監視）※本コードベースでは trade_monitor 実装が含まれます
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: Kill Switch の判定/書き込み
  - monitoring_engine.py: 各モニターの統合ループ
  - alert_manager.py: （アラート送信管理）
- execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager など（発注ロジック）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構築）
- research/
  - factor_research.py, feature_exploration.py（ファクター計算・検証）
- ai/
  - news_nlp.py: ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py: 市場レジーム判定
- utils/
  - logging_setup.py: 共通ログ初期化
  - process_priority.py: プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py: Paper Trading 検証レポート
- data/
  - 実行時に使用される SQLite / DuckDB / PID / flag ファイルが置かれる（デフォルトパス）

開発者向け補足
--------------
- DuckDB 接続を渡してファクター計算等を行う設計です（研究機能は DB の prices_daily, raw_financials 等を参照します）。
- ログは stdout とファイル（logs/<app_name>.log、日次ローテーション）に出力されます。ログディレクトリが作成できない場合はコンソールのみで継続します。
- process_priority.set_process_priority("high") により実行スクリプトは起動時に優先度を上げようとします（権限不足時は警告でスキップされます）。
- tests（ユニットテスト）がある場合は、Settings の自動 .env ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化するとテストが安定します。

問い合わせ / 追加ドキュメント
---------------------------
- 各モジュールの docstring に設計意図や詳細を記載しています。さらに細かな実装や運用手順が必要であれば、特定のモジュール名を指定してドキュメント（例: ExecutionEngine の起動フロー）を生成します。