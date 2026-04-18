README
======

概要
----
KabuSys は日本株の自動売買および運用支援を目的としたモジュール群です。本リポジトリは以下の主要機能を含みます。

- ExecutionEngine 起動スクリプト（実際の発注処理／ペーパートレード両対応）
- 監視／モニタリング（System / Trade / Risk の定期チェック、Kill Switch）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- リサーチ（ファクター計算 / 特徴量分析）
- AI 補助（ニュース NLP によるセンチメントスコア、レジーム判定）
- 各種ユーティリティ（設定ウィザード・設定検証・ログ設定など）
- ペーパートレード検証レポート生成ツール

注意: この README は src/kabusys 配下の実装に基づき作成されています。実運用の前に .env の設定と validate_config による検証を必ず行ってください。

主な機能一覧
------------
- 実行環境スイッチ (KABUSYS_ENV): development / paper_trading / live
  - paper_trading では MockBrokerClient を使用し、ペーパートレード用 DB に分離して記録します
- ExecutionEngine 起動 (run_execution.py)
  - 起動時にプロセス優先度を "high" に設定
  - 停止は data/stop_requested.flag / data/kill.flag による制御
- Monitoring (run_monitoring.py / monitoring_engine)
  - CPU / メモリ / ディスク / プロセスの監視
  - データ鮮度チェック（DuckDB の prices_daily 参照）
  - Kill Switch（ドローダウンやポジション上限で外部停止フラグを書込）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- RiskMonitor / TradeMonitor
  - ドローダウン通知、ポジション上限、滞留注文や異常約定検知
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定（スコア順）、等分重み・スコア重み、リスクベースのポジション決定、セクター制限など
- リサーチ（research パッケージ）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - forward returns、IC（Information Coefficient）など統計的評価
- AI（ai パッケージ）
  - news_nlp: OpenAI を用いたニュースセンチメント集約・ai_scores への書込み
  - regime_detector: ETF（1321）長期移動平均とマクロニュースから市場レジーム判定
  - API 呼び出しは安全策（再試行・フェイルセーフ）を備えています
- ツール
  - 環境設定ウィザード: kabusys.config_setup（.env の対話式作成）
  - 設定検証: kabusys.validate_config（.env / config/*.yaml のチェック）
  - ペーパートレード検証レポート: kabusys.tools.paper_verification_report

セットアップ手順
----------------
1. Python 環境準備
   - 推奨: Python 3.10+
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - 必須パッケージ（例）:
     - duckdb, psutil, openai
     - validate_config の YAML 検証を行う場合は PyYAML
   - pip インストール例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. 環境変数（.env）を用意
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
     - オプション: python -m kabusys.config_setup --env-file path/to/.env
   - 主要環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=sk-...
     - LOG_LEVEL=INFO
   - 自動ロード:
     - コードはプロジェクトルートの .env/.env.local を自動的に読み込みます（OS 環境変数が優先）。
     - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定検証（起動前に必ず実行推奨）
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗）:
     - python -m kabusys.validate_config --strict

5. 必要ディレクトリ作成
   - data/ ログ・DB 用ディレクトリが必要です（logging_setup が logs/ を作成します）。
   - run スクリプトは data/ 以下の stop_requested.flag, kill.flag, execution.pid などを使用します。

使い方（実行例）
----------------

1. ExecutionEngine を起動
   - 通常（環境が .env に設定済み）:
     - python -m kabusys.run_execution
   - paper_trading モードで動かすには KABUSYS_ENV を設定:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成すると起動中の run_execution が検知して終了します。
     - Kill Switch（監視が判定し data/kill.flag を書いた場合）も停止トリガーになります。

2. Monitoring を起動
   - python -m kabusys.run_monitoring
   - ポーリング間隔の変更:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は本番 sqlite_path（.env の SQLITE_PATH）を使用します（環境に依らず本番 DB パスを参照）。

3. 設定ウィザード / 検証
   - ウィザード:
     - python -m kabusys.config_setup
   - 設定検証:
     - python -m kabusys.validate_config
     - python -m kabusys.validate_config --strict

4. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5. AI モジュールの呼び出し（プログラム的利用）
   - ニュース NLP（ai_scores へ書き込む）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="sk-...")
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="sk-...")

注意点・運用上のポイント
-----------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup もその旨を注意喚起します）。
- KABUSYS_ENV の値は development / paper_trading / live のいずれかにしてください。live は本番設定であるため特に注意が必要です。
- PAPER_FILL_MODE（ペーパートレードの約定挙動）有効値:
  - instant | partial | never | reject
- Kill Switch / Stop Flag:
  - monitoring が条件を満たすと data/kill.flag を書き込み、ExecutionEngine は起動時設定や定期チェックでこれを検知して停止します。
  - run_execution/run_monitoring は data/stop_requested.flag を見て自己終了できます。管理用に stop_requested.flag を作成すると安全に停止可能です。
- ログ:
  - デフォルトは logs/<app_name>.log（日次ローテーション、30日保持）
  - 標準出力も併用されます。ログディレクトリが作れない場合はファイル出力をスキップして stdout のみで継続します。
- DB:
  - DuckDB は分析向けの大容量データ格納に使用（デフォルト data/kabusys.duckdb）
  - SQLite は監視・トレードログ用（デフォルト data/monitoring.db）
  - paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を別途使用
- 自動ロード順序:
  - OS 環境変数 > .env.local > .env
  - テスト等で自動ロードを抑制する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ディレクトリ構成（抜粋）
-----------------------
プロジェクトの主要ファイル・ディレクトリ（src/kabusys 配下を中心に抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 # Settings クラス・自動 .env ロード
    - config_setup.py           # .env 対話式ウィザード（CLI）
    - validate_config.py        # 設定検証 CLI
    - run_execution.py          # ExecutionEngine 起動スクリプト（エントリ）
    - run_monitoring.py         # Monitoring 起動スクリプト（エントリ）
    - utils/
      - logging_setup.py        # ログ設定ユーティリティ
      - process_priority.py     # プロセス優先度設定ユーティリティ
    - monitoring/
      - monitoring_db.py        # SQLite 永続化層（system_status, trade_logs, ...）
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - (alert_manager.py, trade_monitor.py 等が存在)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py             # OpenAI を使ったニューススコアリング
      - regime_detector.py      # レジーム判定
    - tools/
      - paper_verification_report.py
    - execution/                 # ExecutionEngine と関連クラス群（OrderManager 等）
    - data/                      # 実行時に作成される想定のディレクトリ（DB, flag, pid 等）
  - config/                      # 設定テンプレート YAML（system_config.yaml 等）

- logs/                          # デフォルトのログ出力先（実行時に作成）
- data/
  - monitoring.db                # デフォルトの監視 SQLite（設定で変更可）
  - paper_trading.db             # ペーパートレード用 DB（paper_trading モード）
  - kill.flag / stop_requested.flag / execution.pid

補足（開発者向け）
-----------------
- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env 自動ロードを抑制できます。
- OpenAI 呼び出し周りは再試行・フェイルセーフ設計になっています。ユニットテストでは外部呼び出しをモックすることを推奨します（コード中に unittest.mock 用の差替えポイントが明記されています）。
- validate_config の YAML 検証は PyYAML がインストールされている場合にのみ実施されます。

ライセンス・バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンスはリポジトリのルートにある LICENSE ファイル（存在する場合）を参照してください。

問い合わせ
----------
実装に関する質問や改善提案はプロジェクトの ISSUE または PR で行ってください。README にない疑問点があればお知らせください。

以上。