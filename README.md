README
======

概要
----
KabuSys は日本株の自動売買・研究・監視を目的としたパッケージです。本リポジトリは以下の機能群を持つモジュール群で構成されています。

- 発注エンジン（ExecutionEngine）
- 監視・アラート（Monitoring）
- ポートフォリオ構築（選定・配分・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量解析）
- AI を使ったニュースセンチメント（OpenAI）
- 各種ユーティリティ（ログ設定、プロセス優先度等）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

主な設計方針は「本番 DB とペーパートレード DB の分離」「外部 API 呼び出し時のフェイルセーフ」「ルックアヘッドバイアス回避（日時参照の扱いに注意）」です。

機能一覧
--------
- Execution
  - 本番 / ペーパートレードに応じた Broker クライアント切替
  - 注文管理・リスク管理・再整合（reconciler）
  - PID / 停止フラグによる制御
- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）
  - Execution の生存確認（PID ファイル監視）
  - 注文ログ・リスクログの永続化（SQLite）
  - Kill Switch（ドローダウンやポジション上限で強制停止フラグ）
  - アラート送信ポイント（LINE などの設定に対応）
- Portfolio
  - 候補選定（スコア順）、等配分・スコア加重配分
  - セクター制約、レジームに基づく投下倍率
  - ポジションサイズ計算（単元丸め、リスクベース、利用可能資金のスケーリング）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュースを OpenAI へ投げて銘柄別センチメント取得（ai_scores テーブル書き込み）
  - マクロニュース + ETF MA200 乖離を用いた市場レジーム判定（market_regime）
  - API 呼び出しはリトライ / クリップ / バリデーション済み
- ユーティリティ
  - 統一的なログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定（Windows / POSIX 対応）
- ツール
  - .env 対話式作成ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（paper_verification_report）

前提・依存ライブラリ
--------------------
（コードから参照されている主な依存）
- Python 3.9+（型ヒント等に応じて適宜）
- duckdb
- psutil
- openai
- （任意）PyYAML（config/*.yaml 検証に使用。無ければ警告となる）

セットアップ手順（簡易）
----------------------
1. リポジトリをクローン、ソースルートに移動
   - パッケージは src/ 配下に配置されています。開発時は PYTHONPATH に src を追加するか pip install -e . を利用してください。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （テストや config 検証に PyYAML が必要な場合）pip install pyyaml

   ※ 実際の requirements.txt / setup.cfg が無ければプロジェクトに合わせて追加してください。

4. 環境変数設定 (.env)
   - 対話式ウィザードで .env を生成: python -m kabusys.config_setup
   - もしくは .env を手動作成（下記にサンプルを記載）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

環境変数（主要）
----------------
必須（最低限設定するもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要なオプション / デフォルト値
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知に使用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。本番は 0 推奨）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject、デフォルト instant）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

簡易 .env 例
------------
以下は config_setup により生成されるフィールドとデフォルト例です（実際には secret 値は置き換えてください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
OPENAI_API_KEY=  # AI 機能を使う場合はセット

使い方（主要スクリプト）
----------------------

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在すると起動を行いません
    - data/execution.pid を出力してプロセス管理に利用

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
    - 監視は常に（KABUSYS_ENV に関係なく）本番用 sqlite_path を使用して監視ログを記録します
    - stop_requested.flag を作成するとループが終了します

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict（警告も失敗扱い）

- .env 対話式作成
  - python -m kabusys.config_setup

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易的に稼働率・注文成功率・レイテンシ等をチェックするレポートを標準出力に出します

AI 関連
-------
- ニュースセンチメント取得
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キー（OPENAI_API_KEY）が必要
  - raw_news / news_symbols / ai_scores テーブルを使用

- レジーム判定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF (1321) の MA200 乖離 + マクロセンチメントを合成して market_regime テーブルへ保存

ログ
----
- ログは標準出力（stdout）とファイル（logs/<app_name>.log、日次ローテート）に出力されます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御できます。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

監視・停止フラグ
----------------
- data/kill.flag: Kill Switch が作成する停止フラグ。ExecutionEngine はこのフラグを検知すると安全停止を試みます。
- data/stop_requested.flag: 起動スクリプト（run_execution / run_monitoring）が外部からループ停止を検知するためのフラグ。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では推奨しない）。

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py                     - パッケージ定義
    config.py                       - 環境変数 / 設定管理 (Settings)
    config_setup.py                 - .env 対話式ウィザード
    validate_config.py              - 起動前設定検証 CLI
    run_execution.py                - ExecutionEngine 起動スクリプト
    run_monitoring.py               - Monitoring ポーリングループ起動スクリプト

    utils/
      logging_setup.py              - ログ設定ユーティリティ
      process_priority.py           - プロセス優先度 / CPU affinity
      __init__.py

    monitoring/
      monitoring_db.py              - monitoring 用 SQLite 操作層
      system_monitor.py             - システム状態・データ鮮度監視
      trade_monitor.py              - （注文監視：ファイルに含まれます）
      risk_monitor.py               - ドローダウン・ポジション上限監視
      kill_switch.py                - kill.flag の作成 / クリア
      monitoring_engine.py          - 各 Monitor を束ねるエンジン
      alert_manager.py              - アラート送信管理（LINE 等との連携）

    execution/
      broker_factory.py             - ブローカークライアント生成
      execution_engine.py           - 実際の実行エンジン（run_session など）
      order_manager.py              - 注文管理
      order_repository.py           - 注文永続化層
      reconciler.py                 - 注文再整合処理
      risk_manager.py               - 発注前リスク判定

    portfolio/
      portfolio_builder.py          - 候補選定・重み計算
      risk_adjustment.py            - セクター制約・レジーム乗数
      position_sizing.py            - 株数決定・スケーリング・単元丸め
      __init__.py

    research/
      factor_research.py            - Momentum/Volatility/Value 等
      feature_exploration.py        - 将来リターン・IC 等
      __init__.py

    ai/
      news_nlp.py                   - ニュースセンチメント集計・OpenAI 呼び出し
      regime_detector.py            - 市場レジーム判定（MA200 + マクロ）
      __init__.py

    data/                            - 実行時に利用するデータディレクトリ（デフォルト）
      monitoring.db                  - SQLite 監視 DB（デフォルト）
      paper_trading.db               - ペーパートレード用 DB（KABUSYS_ENV=paper_trading）
      kabusys.duckdb                 - DuckDB（分析用）

    tools/
      paper_verification_report.py   - ペーパートレード検証レポート生成ツール
      __init__.py

注意事項 / 運用メモ
------------------
- 本番（KABUSYS_ENV=live）では LINE 等の通知設定、KILL_FLAG_CLEAR_ON_START の値、DB パス等を十分に確認してください。
- OpenAI を利用する機能は API コストやレート制限に注意し、API キーの管理を厳重に行ってください。
- posix 系でのプロセス優先度変更や CPU affinity は権限（root 等）が必要な場合があります。
- DuckDB / SQLite のファイルパスは .env で変更可能です。バックアップ・永続化の運用を検討してください。
- この README はコードベースの主要点をまとめたものであり、実運用にあたっては個別モジュール（execution_engine, monitoring_engine 等）の詳細設計書を参照してください。

サポート
-------
- 開発者向けの追加ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）やスクリプトがある場合、それらを参照してください。
- バグ報告・機能要望はリポジトリの Issue をご利用ください。

以上。必要であれば README に含めたい具体的なコマンドや .env の完全テンプレート、systemd / supervisor 用の起動設定例なども追加できます。要望を教えてください。