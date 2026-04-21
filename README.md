KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装したコードベースです。  
主な機能はシグナル生成・ポートフォリオ構築・ポジションサイジング・発注エンジン（ExecutionEngine）、監視（Monitoring）および各種ツール（Paper Trading 検証、AI ベースのニュース NLP / レジーム判定など）です。

主な設計方針
- 本番（live）・ペーパートレード（paper_trading）・開発（development）を環境変数 KABUSYS_ENV で切り替え
- 設定は .env/.env.local または環境変数で管理（自動ロードあり）
- SQLite（監視・発注ログ等）と DuckDB（分析用）を併用
- OpenAI を使った NLP モジュールは外部 API キーで動作（フォールバック・フェイルセーフあり）
- Logging とプロセス優先度設定を統一的に管理

機能一覧
--------
- 実行（Execution）
  - ExecutionEngine（発注エンジン）起動スクリプト: run_execution.py
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使い data/paper_trading.db を使用
  - 発注・オーダー管理、リスク管理、照合（reconciler）などのコンポーネントを組み立てて稼働

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 定期ポーリングでシステム健全性・データ鮮度・滞留注文・ドローダウン等を検出
  - KillSwitch により重大アラートで ExecutionEngine を停止可能

- ポートフォリオ構築・位置決め
  - 候補選定、等配分/スコア配分、リスクベースのポジションサイズ算出
  - セクター上限やレジームによる乗数調整

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いた処理）
  - 将来リターン・IC 計算・ファクター統計サマリ等

- AI（OpenAI）
  - ニュースから銘柄別センチメントを算出して ai_scores に書き込む（news_nlp）
  - マクロニュース + ETF MA を用いた市場レジーム判定（regime_detector）

- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）

セットアップ手順
----------------
前提
- Python 3.10+（typing の | 演算子等を利用）
- システムにより一部機能で psutil の権限が必要（プロセス優先度設定など）

1) ソース取得
   - git clone してローカルに展開

2) 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3) 必要な Python パッケージをインストール
   - requirements.txt があれば:
     pip install -r requirements.txt
   - なければ主に以下を入れる:
     pip install duckdb psutil openai pyyaml

   注意: PyYAML は config/*.yaml の内容検証（validate_config）で必要です。OpenAI モジュールは AI 機能使用時のみ必須です。

4) .env の準備
   - 推奨: 対話式ウィザードを使う
     python -m kabusys.config_setup
   - 手動の場合は .env.example（存在する場合）を参考に .env を作成
   - 自動ロードの挙動:
     - プロジェクトルート（.git か pyproject.toml があるディレクトリ）を探索して .env/.env.local を読みます
     - OS 環境変数が優先され、.env.local は .env を上書き可能
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5) 設定検証
   - python -m kabusys.validate_config
   - 問題があれば出力に従って修正（--strict を付けると警告も失敗扱い）

主要な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- PAPER_FILL_MODE: instant | partial | never | reject（paper トレードの約定振る舞い）
- LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START: 0|1（本番で 1 は危険）

使い方（起動・運用）
--------------------

ログの初期化
- すべての起動スクリプトは内部で logging を統一設定しています（kabusys.utils.logging_setup.setup_logging）。
- 標準出力（stdout）と日次ローテーションで file ハンドラ（logs/<app>.log）を設定します。

ExecutionEngine（発注エンジン）
- 起動:
  python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
  - 実行中に data/stop_requested.flag を作成するとエンジンに停止シグナルを送ります（または監視が kill.flag を作成して停止させる）

Monitoring（監視）
- 起動:
  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
  python -m kabusys.run_monitoring
- 動作:
  - 監視は Settings.sqlite_path（production 用 sqlite）を使用して監視テーブルを初期化 / 更新します（環境に依らず本番 sqlite_path を使用）
  - 各モニタが実行結果に応じて risk_logs / trade_logs / dashboard 等を書き込み、必要に応じて KillSwitch により data/kill.flag を作成して ExecutionEngine 停止を要求します
  - 監視プロセスの停止: data/stop_requested.flag を作成すると監視ループは終了します

Kill Switch / Stop フロー
- kill.flag (Settings.kill_flag_path、デフォルト data/kill.flag)
  - Monitoring 側の KillSwitch が危険条件を検出した際に書き込む
  - ExecutionEngine は起動時や実行中に kill.flag の有無を監視し、存在すれば停止する（実装により若干の差）
- stop_requested.flag (data/stop_requested.flag)
  - 明示的にプロセスを止めたい場合に作成するファイル。run_execution / run_monitoring はこのファイルを検出して終了します

Paper Trading 検証レポート
- 期間指定などでペーパートレードログを集計して PASS/FAIL 判定を行う CLI
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db で DB パスを指定可能、環境変数 PAPER_TRADING_SQLITE_PATH でも指定可

AI モジュール（news_nlp / regime_detector）
- OpenAI API キーが必要（OPENAI_API_KEY）
- ニューススコア / レジーム判定は外部 API に依存するため API エラー時はフェイルセーフ（スコア 0 等）で継続する実装
- 大量リクエストに対してはバッチ処理・リトライ（指数バックオフ）を行う

開発者向け（プログラム的利用）
- 研究・解析関数は kabusys.research 経由でインポート可能（例: kabusys.research.calc_momentum）
- ポートフォリオ/ポジション計算関数は kabusys.portfolio 経由で利用可

ディレクトリ構成（抜粋）
-----------------------
（プロジェクトルート）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理（自動 .env ロード）
    - config_setup.py          — 対話式 .env 作成ウィザード
    - validate_config.py       — 起動前設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
    - execution/               — Execution に関する実装（broker, engine, order_manager 等）
    - monitoring/
      - monitoring_db.py       — SQLite persistence layer（テーブル作成・読み書き）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/               — 監視関連（DB・ロジック）
- data/                        — デフォルトの DB / フラグファイル置き場（作成される）
- logs/                        — ログ出力先（デフォルト）

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では設定とアクセス権を十分に確認してください（validate_config の警告を要確認）。
- .env は機密情報を含むため絶対にリポジトリにコミットしないこと。
- Kill Switch や Stop Flag の扱いには注意（KILL_FLAG_CLEAR_ON_START は本番では 0 推奨）。
- Logging のファイル出力に失敗した場合、コンソール出力のみで継続します（警告が出ます）。
- プロセス優先度設定は psutil を使っています。権限不足で設定できない場合はログに警告が出ますが動作自体は継続します。

追加情報・トラブルシューティング
---------------------------------
- DuckDB / SQLite のファイルパスは Settings で指定されています。デフォルトは data/kabusys.duckdb / data/monitoring.db。config_setup や環境変数で変更可。
- validate_config は必要な環境変数や config/*.yaml の存在をチェックします。PyYAML がない場合は YAML 検証をスキップします。
- OpenAI 関連は API レート制限やネットワークエラーを考慮してリトライを行いますが、長時間失敗すると該当処理はスキップされます。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

最後に
------
まずは .env を作成し（python -m kabusys.config_setup）、設定検証（python -m kabusys.validate_config）を行ってから、ローカルでは paper_trading モードで run_execution と run_monitoring を起動して挙動を観察することをおすすめします。質問や補足があれば教えてください。