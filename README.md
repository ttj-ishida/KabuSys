KabuSys — 日本株自動売買システム
=================================

このリポジトリは、研究（ファクター計算）・ポートフォリオ構築・発注エンジン（ExecutionEngine）・監視（Monitoring）・AI 補助（ニュース NLP / レジーム判定）を含む日本株自動売買システムのコア実装です。ここではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
---------------
KabuSys は以下の責務を持つモジュール群から構成されます。

- データ分析 / 研究（DuckDB を利用したファクター計算、将来リターン計算、IC 評価など）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制限）
- Execution エンジン（ブローカークライアントを通じた発注管理、ペーパートレード対応）
- 監視（システム状態、注文ログ、リスク監視、Kill Switch）
- AI モジュール（ニュース NLP によるセンチメントスコア、レジーム判定）
- 運用ツール（.env ウィザード、設定検証、Paper Trading 検証レポート等）
- ロギング / プロセス優先度ユーティリティ等の共通ユーティリティ

主な特徴 / 機能一覧
-----------------
- Settings クラスによる環境変数 / .env の統一管理
  - 主要な環境変数: KABUSYS_ENV (development | paper_trading | live), JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL 等
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して専用 DB に記録）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 監視コンポーネント
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, KillSwitch, MonitoringDB（SQLite永続化）
  - kill.flag / stop_requested.flag を使った停止・キルスイッチ制御
- ポートフォリオ構築
  - 候補選定（select_candidates）、等重・スコア重み（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（risk_based / equal / score）、単元株丸め、aggregate cap 調整
  - セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier
- 研究（research）
  - calc_momentum / calc_volatility / calc_value: DuckDB 内 prices_daily/raw_financials を参照
  - 複数ホライズンの将来リターン計算、IC（スピアマン）等の統計ツール
- AI モジュール
  - news_nlp.score_news: OpenAI を用いた記事ベースの銘柄センチメント算出（ai_scores へ書き込み）
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM 評価を合成して market_regime を算出
  - 両モジュールは OPENAI_API_KEY を必要とし、API エラー時はフェイルセーフで継続する設計
- 運用ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証（--strict オプションあり）
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを生成

前提・依存
----------
- Python 3.10+（typing の | 演算子等を使用）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- ローカル環境で動かす場合は .env を準備すること（config_setup.py で対話的に作成可）

セットアップ手順
---------------
1. リポジトリをクローン / コピー
   - 例えば: git clone <repo_url>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール
   - 依存ファイルがない場合は最低限次を入れる:
     - pip install duckdb psutil openai
   - PyYAML は設定検証で推奨:
     - pip install PyYAML

4. 環境変数 / .env の準備
   - 対話的に作成: python -m kabusys.config_setup
   - もしくは .env.example を基に .env を用意（リポジトリに例ファイルがなければ config_setup を使って生成してください）
   - 重要変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使用する場合）
     - KABUSYS_ENV（development | paper_trading | live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方
------
基本的な起動・利用方法を示します。

- ExecutionEngine を起動する（実際の注文 / ペーパートレード）
  - python -m kabusys.run_execution
  - 動作挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_db（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient を使って発注を記録（本番 DB と完全分離）
    - 停止は data/stop_requested.flag を作成することで行えます（スクリプトは起動時にこのフラグを見て起動しない / 実行中に検知して停止します）
    - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可）

- Monitoring を起動する
  - python -m kabusys.run_monitoring
  - 動作挙動:
    - SystemMonitor をポーリングして system_status 等を SQLite（Settings.sqlite_path）に記録します
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは本番 DB を使う設計）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定

- .env 作成ウィザード
  - python -m kabusys.config_setup
  - 対話で .env を生成・更新します。完了後に python -m kabusys.validate_config を実行してください。

- 設定検証（CLI）
  - python -m kabusys.validate_config
  - --strict オプションで警告を fail 扱いにできます

- AI 機能（プログラム的に呼ぶ）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...") などを呼び出して ai_scores を更新します
  - regime_detector.score_regime(conn, target_date, api_key="...") で market_regime 書き込み

運用時の注意点
---------------
- Kill Switch / Stop フラグ
  - data/kill.flag: KillSwitch が書き込むファイル。存在すると ExecutionEngine に停止シグナルを送る運用。
  - data/stop_requested.flag: run_execution / run_monitoring の起動ループが検知して停止するためのフラグ。
  - KILL_FLAG_CLEAR_ON_START 設定に注意（本番で自動クリアは危険）。

- ロギング
  - setup_logging() により stdout ログと日次ローテートされたファイルログ（logs/<app_name>.log）が設定されます。
  - LOG_LEVEL, LOG_DIR でロギング挙動を調整可能。

- DB 分離
  - paper_trading モードではペーパートレード用 SQLite を使用し、本番の monitoring.db と分離して記録されます（PAPER_TRADING_SQLITE_PATH を確認）。

- OpenAI / API 使用
  - OPENAI_API_KEY を .env か環境変数で設定してください。API エラーはリトライやフェイルセーフ（0.0 等で続行）する設計です。
  - LLM 出力は JSON Mode を想定して厳密な JSON を要求していますが、パース失敗時の保護コードも入っています。

ディレクトリ構成（主要ファイル）
-----------------------------
（ここでは src/kabusys 以下の主要ファイル群を示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照あり)
  - execution/
    - execution_engine.py (参照あり)
    - order_manager.py (参照あり)
    - order_repository.py (参照あり)
    - reconciler.py (参照あり)
    - broker_factory.py (参照あり)
    - risk_manager.py (参照あり)
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
  - data/ (ランタイムで生成される想定)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (ペーパートレード用)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - execution.pid, kill.flag, stop_requested.flag 等のフラグ/PID ファイル
  - logs/ (ログ出力先、デフォルト)

（注意）一部モジュールはここに示した以外にも内部的参照があり、外部のデータパイプライン（kabusys.data.*）やブローカークライアント実装が必要です。実際に発注接続するには broker の設定や API 情報（KABU_API_PASSWORD 等）が必要です。

サンプル .env （最低限）
---------------------
以下は最低限必要となる主要項目の例（実際の値は適切に設定してください。機密情報は決して Git にコミットしないでください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
OPENAI_API_KEY=sk-xxxxxx
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

よくある操作例
--------------
- .env を作成: python -m kabusys.config_setup
- 設定チェック: python -m kabusys.validate_config
- 監視開始: python -m kabusys.run_monitoring
- エンジン開始: python -m kabusys.run_execution
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

貢献・拡張ポイント
------------------
- ブローカークライアントの実装（kabuステーションとの接続）や MockBrokerClient の拡充
- AI モジュールのプロンプトチューニング、API 呼び出しのエラーハンドリング改良
- テストスイート（ユニット・統合）の整備
- Docker / systemd ユニットファイルによるデプロイ手順

ライセンス
----------
リポジトリに記載のライセンスに従ってください（ここでは省略）。

補足
----
この README はコードベースの主要な設計・運用ポイントをまとめたものです。詳細な設計意図や追加のユーティリティ、システム間の契約（DB スキーマ、テーブル名、カラム規約等）は各モジュールのドキュメント文字列およびソースコード内コメントを参照してください。質問や追記したい点があれば教えてください。