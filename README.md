# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買を想定した小型フレームワークです。発注実行エンジン、監視・アラート、ポートフォリオ構築、ファクター研究、ニュースNLP（OpenAI）など複数のコンポーネントを含みます。設計方針として「本番と研究ロジックの分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時のフォールバック）」を重視しています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動・コマンド例）
- 主要環境変数
- 運用上の注意
- ディレクトリ構成（主要ファイル一覧）

---

プロジェクト概要
- ExecutionEngine（発注エンジン）：ブローカークライアント経由で注文を実行・管理するコンポーネント。KABUSYS_ENV により paper_trading（モック）と live（実取引）を切替可能。
- Monitoring：システム・発注・リスクの定期監視、Kill Switch（リスクトリガで実エンジン停止）やアラート送出支援。
- Portfolio：銘柄選定、重み付け、ポジションサイズ算出（純粋関数群）。
- Research：DuckDB 上でファクター計算、将来リターン、IC や統計サマリを生成。
- AI：ニュースを OpenAI で評価するニュースNLP、マクロニュースを用いた市場レジーム判定。
- Tools：ペーパートレードの検証レポート生成などユーティリティ。

---

主な機能一覧
- 起動スクリプト
  - run_execution.py：ExecutionEngine の起動（KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し data/paper_trading.db に記録）
  - run_monitoring.py：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で周期変更可）
- 環境管理
  - config_setup.py：対話式 .env 生成ウィザード
  - validate_config.py：起動前の環境設定検証 CLI（--strict オプションあり）
- 監視・安全機構
  - monitoring_engine.py、system_monitor.py、trade_monitor.py、risk_monitor.py、kill_switch.py、monitoring_db.py
- ポートフォリオ関連（純粋関数）
  - portfolio_builder.py、position_sizing.py、risk_adjustment.py
- 研究用モジュール（DuckDB 接続）
  - research/factor_research.py、research/feature_exploration.py
- AI
  - ai/news_nlp.py（ニュースセンチメントを OpenAI で評価し ai_scores に格納）
  - ai/regime_detector.py（ETF・マクロを合成してレジーム判定）
- ツール
  - tools/paper_verification_report.py：ペーパートレード検証レポート生成

---

セットアップ手順（開発・運用向け基本手順）
1. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成して有効化してください（venv / pyenv / conda 等）。

2. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成（対話式）
   - 初回は対話ウィザードを使うのが簡単です:
     - python -m kabusys.config_setup
   - 生成される .env は機密情報を含むため Git へはコミットしないでください。

4. 設定の検証
   - python -m kabusys.validate_config
   - 問題があれば出力に従って .env や config/*.yaml を修正してください。
   - --strict を付けると警告もエラー扱いになります。

5. データベースファイル
   - デフォルト:
     - SQLite（監視用）: data/monitoring.db
     - DuckDB（分析用）: data/kabusys.duckdb
     - Paper Trading SQLite: data/paper_trading.db
   - ファイルは自動作成されますが、親ディレクトリは作成されない場合があるため validate_config でチェックしておくと安心です。

6. ログディレクトリ
   - デフォルト logs/ に日次ローテートでログが出力されます（logs/<app_name>.log）。

---

主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — 実行モード: development / paper_trading / live（デフォルト: development）
    - paper_trading: MockBroker を使用し data/paper_trading.db に記録
    - live: 実注文が行われます（取り扱い注意）
- データベース・ログ
  - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite 監視DB（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（default: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - LOG_DIR — ログ保存先ディレクトリ
- 監視・運用用
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト: 60）
  - PID_FILE_PATH — 実行エンジンの pid ファイルパス（default: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch のフラグパス（default: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1）
- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector の API キー（引数で上書き可）
- PAPER_FILL_MODE (paper_trading 時)
  - instant / partial / never / reject（デフォルト: instant）

詳しい説明は kabusys/config.py と config_setup.py のコメントを参照してください。

---

使い方（コマンド例）
- 環境準備（例）
  - export $(cat .env | xargs)  # 環境変数を読み込む方法の一例
- 対話式に .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は MockBrokerClient を使用し paper_trading.db にログを残します。
- Monitoring を起動（SystemMonitor のポーリング）:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数で:
    - export MONITOR_POLL_INTERVAL=30
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI 処理（ニュース評価 / レジーム判定）
  - これらはモジュール関数として提供されています。スクリプトの作成例:
    - python -c "from datetime import date; import duckdb; from kabusys.ai.news_nlp import score_news; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, date(2026,4,1), api_key='YOUR_KEY'))"
  - 実運用ではキーファイル・ジョブスケジューリング等で呼び出してください。

停止・制御
- 停止フラグ: data/stop_requested.flag（run_monitoring/run_execution はこのファイルの存在を監視して優雅に停止します）
- Kill Switch: data/kill.flag（KillSwitch が書き込み、ExecutionEngine に停止指示を出します）
- PID ファイル: data/execution.pid（ExecutionEngine が起動時に書き込むファイル）

---

運用上の注意
- KABUSYS_ENV=live の場合は本番環境です。OpenAI/API トークン、kill flag の取り扱い、LINE 通知設定などを必ず確認してください。
- .env は決してリポジトリにコミットしないでください（機密情報が含まれます）。
- run_execution は起動時にプロセス優先度を上げようとします（set_process_priority）。権限不足で失敗した場合は警告を出して継続します。
- Monitoring はデフォルトで監視 DB（SQLITE_PATH）に書き込みます。paper_trading では Execution 側が paper_sqlite_path を用いるため本番 DB とは分離されます。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
  - config.py                        — Settings クラス（環境変数読み込み・検証）
  - config_setup.py                  — .env 対話式ウィザード
  - validate_config.py               — 設定検証 CLI
  - utils/
    - logging_setup.py               — ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py               — 監視DB 初期化・読み書き
    - monitoring_engine.py           — 各 Monitor を束ねるエンジン
    - system_monitor.py              — システム・データ鮮度監視
    - risk_monitor.py                — ドローダウン / ポジション上限監視
    - trade_monitor.py               — （発注関連監視。詳細ファイル参照）
    - kill_switch.py                 — kill.flag 制御
    - alert_manager.py               — （アラート管理。詳細ファイル参照）
  - execution/
    - execution_engine.py            — 実行エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py               — ブローカークライアント生成（Mock / Live）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                     — ニュースNLP（OpenAI 呼び出し）
    - regime_detector.py              — マクロ + ETF でレジーム判定
  - tools/
    - paper_verification_report.py    — ペーパートレード検証レポート
  - data/（実行時に作成されることが多い）
    - monitoring.db (default SQLite)
    - paper_trading.db (paper_trading 用)
  - logs/（ログ出力先、日次ローテーション）

（上記は主要ファイルのみ抜粋。詳細はソースツリーを参照してください。）

---

開発者向けヒント
- DuckDB 接続を利用した研究コードは外部 API にアクセスしないよう設計されています（prices_daily / raw_financials などのテーブルのみ参照）。
- AI モジュールは API 失敗時やパースエラー時に堅牢なフォールバックを持ち、例外でプロセスを停止させないようになっています。テスト時は内部の API 呼び出し関数をモックする設計になっています（例: unittest.mock.patch）。
- validate_config.py と config.py のロジックにより、起動前に必須環境変数のチェック・警告が可能です。CI に組み込むと安全です。

---

サポート / 参照
- 詳細な実装やファンクションの使い方は各モジュールの docstring を参照してください（src/kabusys 以下）。
- .env.example がない場合は config_setup.py を使って初期設定を行ってください。

---

ライセンス / 責任
- 本コードはサンプル実装です。live 環境での使用は自己責任で行ってください。実資金を扱う場合は十分な検証と安全対策（Kill Switch、ログ、監視）を行ってください。

以上。README に不足する項目や、特定のコマンドの具体的な例（systemctl/supervisor でのデーモン化、Docker 化など）を追加したい場合は教えてください。