README
=====

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的としたライブラリ兼実行スクリプト群です。本リポジトリは以下の主要機能を備えています。

- 注文実行エンジン（ExecutionEngine）とペーパートレード分離
- 監視コンポーネント（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- リサーチ（ファクター計算、将来リターン、IC 計測など）
- ニュース NLP（OpenAI による銘柄別センチメント）
- 市場レジーム判定（MA とマクロセンチメントの合成）
- 設定ウィザード / 設定検証ツール
- ペーパートレード検証レポート生成ツール
- 共通ユーティリティ（ロギング設定、プロセス優先度制御など）

機能一覧
--------
主な機能（モジュール別）

- 実行 / 起動スクリプト
  - kabusys.run_execution: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使用）
  - kabusys.run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可能）
- 設定管理
  - kabusys.config: .env の自動読み込み／Settings クラス（環境変数アクセスのラッパ）
  - kabusys.config_setup: 対話式ウィザードで .env を生成/更新
  - kabusys.validate_config: 起動前チェック（必須環境変数や config/*.yaml の存在チェック等）
- 監視
  - kabusys.monitoring: system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db（SQLite）
  - KillSwitch: リスク条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
- ポートフォリオ
  - kabusys.portfolio: 候補選定、等重/スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算
- リサーチ
  - kabusys.research: ファクター計算（momentum/value/volatility 等）、将来リターン、IC、統計サマリー
- AI（OpenAI）
  - kabusys.ai.news_nlp: ニュース記事の銘柄別センチメント算出（OpenAI API を使用）
  - kabusys.ai.regime_detector: MA とマクロニュースセンチメントを合成して market_regime に書き込む
- ツール
  - kabusys.tools.paper_verification_report: ペーパートレード DB から検証レポートを生成
- ユーティリティ
  - kabusys.utils.logging_setup: 統一的なログ設定（stdout + 日次ローテートファイル）
  - kabusys.utils.process_priority: プロセス優先度 / CPU affinity 設定

セットアップ手順
-------------
前提
- Python 3.10 以上（PEP 604 の union 型演算子 (|) を使用）
- SQLite は標準ライブラリで利用可能
- システムによっては psutil 等のネイティブ依存あり

基本手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo_url>
   - (作業ディレクトリを src が含まれるルートにする)

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML
     - openai: ニュース NLP / レジーム検出で使用
     - PyYAML: validate_config が config/*.yaml のパースを行う場合に必要
     - duckdb: リサーチ・AI モジュールでのデータ参照用
   - 追加で必要なパッケージ（実際のブローカークライアント等）はプロジェクトに応じてインストール

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考にして .env を作成
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - LOG_LEVEL / LOG_DIR など

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いにする

使い方
------

一般的な起動方法
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作ると起動済みエンジンは停止シグナルを受け取る仕組みです（run_execution 側でチェック）。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、data/paper_trading.db に記録されます（本番 DB と分離）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path を使用（設定上の注意）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスを指定する場合: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）

AI 機能
- ニュース NLP（銘柄ごとのセンチメント）
  - 実行例: スクリプトや他モジュールから kabusys.ai.score_news を呼ぶ
  - OpenAI API キーは環境変数 OPENAI_API_KEY で設定
  - 失敗時は安全にフォールバックする設計（API 失敗はゼロスコア等で継続）

設定関連
- .env の生成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]

停止・Kill Switch
- Kill Switch は監視側でリスク条件（ドローダウンやポジション上限等）を評価して data/kill.flag を書き込みます。ExecutionEngine はこのフラグを検出して安全に停止する設計です。
- 手動で停止したい場合は data/stop_requested.flag を作成すると run_execution / run_monitoring のループが終了します。

ディレクトリ構成
----------------
以下は本リポジトリ内の主なファイル・ディレクトリ（抜粋）です。src/kabusys 以下に主要モジュールが配置されています。

- src/
  - kabusys/
    - __init__.py
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
    - config.py                      — Settings / .env 自動ロード
    - config_setup.py                — .env 対話式ウィザード
    - validate_config.py             — 設定検証 CLI
    - utils/
      - __init__.py
      - logging_setup.py             — ログ設定ユーティリティ
      - process_priority.py          — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py             — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py             — （ファイル未掲示だが存在想定）
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py             — （ファイル未掲示だが存在想定）
    - execution/
      - execution_engine.py          — （実行エンジン本体）
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py
  - config/
    - *.yaml                         — system_config 等（テンプレート生成スクリプトあり）
  - data/                            — デフォルト DB / フラグファイル等（runtime に作成）
    - monitoring.db (デフォルト SQLITE_PATH)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - paper_trading.db (ペーパートレード DB)
    - kill.flag / stop_requested.flag / execution.pid
  - logs/                            — ログファイル（デフォルト LOG_DIR）

補足・運用メモ
--------------
- DB のデフォルトパスは data/ 以下です。運用環境では適切な永続領域に変更してください。
- monitor は監視テーブル作成を冪等に行います（init_monitoring_db）。
- OpenAI を利用する機能は API コストとレート制限に注意してください。リトライやスロットリングロジックが入っていますが、運用ポリシーに合わせて調整してください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを強く推奨します（自動クリアは危険）。
- logging_setup はログディレクトリ作成に失敗した場合、自動的にファイル出力を無効化してコンソールのみで動作します。

ライセンス・貢献
----------------
（ここにライセンスやコントリビュート方法を追記してください）

以上。README の補足や特定モジュールの詳細な使用例（ExecutionEngine の設定項目、OrderRepository の API など）が必要であれば、追加で出力します。