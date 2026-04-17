KabuSys — 日本株自動売買システム
=============================

本ドキュメントはリポジトリ内の主要スクリプト・モジュールの使い方とセットアップ手順をまとめた README です。  
（技術ドキュメント／オンボーディング用途向け）

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主に次の用途を提供します。

- 注文実行エンジン（ExecutionEngine 起動スクリプト）  
- システム監視・アラート（Monitoring）  
- ポートフォリオ構築（候補選定・重み付け・ポジション決定）  
- リサーチ（ファクター計算・IC 計算・特徴量探索）  
- ニュース NLP（OpenAI を用いたセンチメントスコアリング）および市場レジーム判定  
- Paper Trading 用の検証レポート生成ツール

主な特徴
--------
- 環境変数 / .env による設定（Settings クラス）と対話式ウィザード（config_setup）
- 本番・ペーパートレードの DB 分離（paper_trading モードでは data/paper_trading.db を使用）
- DuckDB（分析用）と SQLite（監視・発注ログ）の併用
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロセンチメント評価（任意）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）による自動アラート・Kill Switch
- ポートフォリオ構築関数群（等重配分、スコア重み、リスクベースのポジションサイズ計算）
- Paper Trading 検証レポート生成ツール

セットアップ手順
----------------

1. Python 環境
   - Python 3.10+ を推奨（typing 機能や一部記法に依存）
   - 仮想環境を利用してください（venv / pyenv 等）

2. 依存ライブラリのインストール（例）
   - 必須ライブラリ（主要なもの）:
     - duckdb
     - psutil
     - openai
     - pyyaml（config 検証時にあると YAML の検査を行います）
   - インストール例:
     - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt がない場合は上記を参考にしてください）

3. .env の初期作成
   - 対話式ウィザードで .env を作成できます:
     - python -m kabusys.config_setup
   - 生成後、.env を Git にコミットしないでください（機密情報含む）。

4. 設定検証
   - 作成した設定を検証:
     - python -m kabusys.validate_config
   - 警告も失敗扱いにする厳格モード:
     - python -m kabusys.validate_config --strict

5. データディレクトリ
   - デフォルトでは data/ 以下に DB 等を配置します。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。
   - 監視用 stop/kill フラグや pid ファイルも data/ に保存されます。

重要な環境変数（主なもの）
-------------------------
以下は Settings クラスに定義された主要な環境変数（デフォルト値や用途を併記）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI 呼び出しに必要（ニュース NLP / レジーム判定）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（任意）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（INFO 等）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH — 実行エンジン制御用のパス
- PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant|partial|never|reject）

使い方（コマンド例）
------------------

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告を FAIL とする）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にログを保存します。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中に同ファイルが作成されるとエンジンに停止シグナルが送られます。

- 監視ループ起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（監視 DB）を使用します：監視は常にプロダクションの sqlite_path を参照します（環境に依らず）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数、または関数引数で渡す）
  - ニュース NLP: kabusys.ai.news_nlp.score_news（プログラムから呼び出して利用）
  - レジーム判定: kabusys.ai.regime_detector.score_regime
  - 使用モデル: gpt-4o-mini（コード内定義）

停止制御（Kill Switch / stop flag / pid）
-----------------------------------------
- 停止フラグ:
  - run_execution/run_monitoring のスクリプトは data/stop_requested.flag をチェックします。これを作成すると起動中ループが終了します（daemon スレッド停止等のトリガー）。
- Kill Switch:
  - monitoring の KillSwitch は data/kill.flag（デフォルト）を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアします（本番環境では 0 を推奨）。
- PID ファイル:
  - ExecutionEngine は pid ファイル（デフォルト data/execution.pid）を作成し、SystemMonitor はその PID 存在チェックによりプロセス稼働判定を行います。stale PID は監視側で削除されイベントログに記録されます。

ディレクトリ構成（主要ファイル）
--------------------------------

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py — 環境変数 / .env 自動ロード・Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — マクロ + ETF MA200 を用いた市場レジーム判定

  - monitoring/
    - monitoring_db.py — SQLite 用永続化層（テーブル初期化 + MonitoringDB クラス）
    - system_monitor.py — CPU / メモリ / ディスク / データ鮮度 / プロセス監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各モニタを束ねるループ
    - alert_manager.py — （アラート送信管理。未表示分あり）

  - execution/  (主要な実装ファイル群はここに配置される想定)
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, order_record.py など

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定（lot 単位丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

運用上の注意
------------
- .env に API キー等の機密情報が含まれるため、決して Git にコミットしないでください。
- run_monitoring は監視 DB（sqlite）を参照しますが、Monitoring は本来どの環境でも production の sqlite_path を使用する仕様になっています（監視と実行ログの分離を遵守）。
- OpenAI を使う機能は API 費用が発生します。利用時はコストとレート制限に注意してください。
- psutil によりプロセス優先度・CPU affinity を設定しますが、権限不足で失敗する可能性があるため warning を出してスキップします。

拡張 / 開発メモ
----------------
- DuckDB を使ったファクター計算・リサーチ機能は外部 API への依存がなく、分析用途で再利用しやすい設計です。
- ニュース NLP とレジーム検出は JSON モードを使用し、レスポンスのバリデーションやリトライロジックを備えています。
- ポートフォリオ構築ロジックは純粋関数群（副作用なし）で設計されており、単体テストが容易です。

参考コマンドまとめ
------------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

必要な追加情報や README の追補があれば、どの点を補足したいか教えてください。README の英語版や運用手順書（systemd ユニットやコンテナ化手順など）も必要であれば作成できます。