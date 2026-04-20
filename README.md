KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤のモジュール群です。  
主に次の役割を持ちます:

- 発注エンジン (ExecutionEngine) と発注管理
- システム監視（SystemMonitor / MonitoringEngine）と Kill Switch
- ポートフォリオ構築（銘柄選定・重み計算・株数決定）
- リサーチ（ファクター計算・特徴量解析）
- AI を使ったニュース NLP（OpenAI を用いたセンチメント評価）
- ペーパートレード用の検証ツール（レポート生成 など）

特徴
----
- モジュール化された純粋関数群（portfolio, research 等）は DB 参照を最小化しテストしやすい設計
- 実行環境（KABUSYS_ENV）により本番 / ペーパートレードを分離
- Monitoring 系は SQLite に監視ログを永続化し、Kill Switch による安全停止をサポート
- OpenAI と連携する AI モジュール（news_nlp, regime_detector）を備え、外部 API 呼び出しはフェイルセーフ実装
- ロギングは共通ユーティリティでコンソール + 日次ローテーションログを出力

必須 / 主要機能一覧
------------------
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録
- 環境設定
  - config_setup.py: .env を対話式に生成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
- 監視（monitoring）
  - MonitoringDB: SQLite ベースの永続層（system_status, trade_logs, positions, risk_logs, dashboard）
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
- ポートフォリオ（portfolio）
  - 銘柄選定、等分・スコア加重重み、位置サイズ計算、セクターキャップ、レジーム乗数
- リサーチ（research）
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 接続で prices_daily 等を参照）
  - feature_exploration: 将来リターン・IC 計算・統計サマリ
- AI（ai）
  - news_nlp.score_news: ニュース記事を OpenAI に送って銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF MA とマクロセンチメントを合成して市場レジームを判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成

動作環境（推奨）
--------------
- Python 3.10 以上（型注釈の | 記法を使用）
- SQLite（標準ライブラリ）
- 必要パッケージ（概ね次をインストールしてください）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config の YAML 検証を行う場合、任意）
- （任意）cron / systemd などで run_monitoring / run_execution を運用

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - ※requirements.txt がない場合は上記パッケージを最低限用意してください

4. .env を作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードでは J-Quants トークンや kabu ステーションのパスワード等を入力します。
   - 生成された .env は絶対にリポジトリにコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. 必要ディレクトリ確認
   - data/ や logs/ は自動作成されますが、権限等に注意してください。

主要な環境変数（抜粋）
---------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 代表的な任意 / 推奨:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - OPENAI_API_KEY: OpenAI を使う場合に必要
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

起動・運用方法（簡単な使い方）
----------------------------
- 環境を paper_trading にして ExecutionEngine を起動（MockBroker を使い本番 DB と分離）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - paper_trading モードでは PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録されます。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）。例:
    - export MONITOR_POLL_INTERVAL=30

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を優先）

- AI モジュールの利用（例：ニューススコアリング）
  - score_news / score_regime は DuckDB 接続オブジェクトを受け取り、OpenAI API キー（OPENAI_API_KEY）を使用します。
  - 直接スクリプト化はしていませんが、運用スクリプトから呼び出して定期実行可能です。

停止 / Kill Switch
------------------
- monitoring は data/stop_requested.flag をチェックしてループ終了（run_monitoring で使用）
- ExecutionEngine 側は data/kill.flag（KillSwitch）によって安全に停止できます
  - KillSwitch は RiskMonitor の判定等に基づき kill.flag を書き込みます
- PID ファイル: data/execution.pid（run_execution が書きます）

ロギング
--------
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を使用
  - コンソール（stdout）出力 + 日次ローテーションファイル /logs/<app_name>.log
  - 環境変数 LOG_DIR / LOG_LEVEL で制御

ディレクトリ構成（主要ファイル）
------------------------------
（リポジトリルートの src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py (実装あり)
    - alert_manager.py (実装あり)
  - execution/               — ExecutionEngine, OrderManager, BrokerFactory 等
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
  - data/                    — runtime 用の SQLite / pid / flag 等（自動作成される）

注意事項 / 運用上のヒント
------------------------
- KABUSYS_ENV=live の場合は本番用ブローカーに接続されるため、設定や資金管理には十分注意してください。
- .env は機密情報（API トークン・パスワード）を含むため、絶対にバージョン管理にコミットしないでください。
- OpenAI を用いる機能は API キーと使用料が必要です。呼び出し回数を考慮したバッチ処理設計（news_nlp の _BATCH_SIZE 等）になっています。
- DuckDB / prices_daily 等のテーブルはリサーチ機能で参照されます。データ投入とスキーマ準備を事前に行ってください。
- PyYAML がインストールされていないと validate_config の YAML 検証がスキップされます（警告が出ます）。

貢献 / テスト
--------------
- モジュールは可能な限り純粋関数で設計されているためユニットテストが書きやすくなっています。テストを書く場合は DB 接続をモックするか一時 DB を使ってください。
- OpenAI 呼び出し部分は内部で切り出されているため、ユニットテスト時は該当関数を patch してスタブ化できます（news_nlp._call_openai_api など）。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE 等を参照してください（本リポジトリには含まれていない場合があります）。

お問い合わせ
------------
- ソースコード内のドキュメント文字列や各モジュールのコメントをまずご参照ください。運用に関する具体的な質問があれば、実装責任者やリポジトリ保守者にお問い合わせください。

以上がこのコードベースの概要と利用方法です。必要なら README に追記したいサンプル .env テンプレートや systemd ユニット例、運用チェックリスト等を作成します。どの情報を追加しますか？