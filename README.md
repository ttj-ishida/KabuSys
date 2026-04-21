KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株の自動売買システム「KabuSys」のコアモジュール群です。戦略・ポートフォリオ構築、発注エンジン、監視・アラート、研究用ユーティリティ、及び AI を使ったニュース／レジーム判定モジュールを含みます。

概要
----
KabuSys は以下の責務を持つコンポーネントで構成されています。

- 発注実行（ExecutionEngine）: ブローカークライアント経由で発注を行うエンジン（本番 / ペーパートレード対応）。
- 監視モジュール（Monitoring）: システム状態、注文ログ、リスク（ドローダウン・ポジション数）を定期チェックし、必要なら Kill Switch を発動。
- ポートフォリオ構築（portfolio）: 候補選定、重み算出、ポジションサイズ計算、セクター制限等。
- リサーチ（research）: ファクター計算（モメンタム／バリュー／ボラティリティ）や特徴量解析ユーティリティ。
- AI モジュール（ai）: OpenAI を使ったニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）。
- ユーティリティ（utils）: ログ設定、プロセス優先度設定など。
- CLI ツール: .env ウィザード（config_setup）、設定検証（validate_config）、Paper Trading 検証レポート等。

主な機能一覧
-------------
- 実行環境分離:
  - KABUSYS_ENV に応じて挙動を切り替え（development / paper_trading / live）。
  - paper_trading 時は MockBrokerClient を使用し、paper トレード用 DB に記録（本番 DB と完全分離）。
- 監視/キルスイッチ:
  - システム稼働率、CPU/メモリ/ディスク、データ鮮度、滞留注文、ドローダウン、ポジション上限などを監視。
  - 条件を満たすと data/kill.flag を書き、ExecutionEngine を安全に停止させる。
- ポートフォリオ構築:
  - 候補選定（スコア順）、等配分/スコア加重、リスクベースの発注株数計算、セクター集中チェック等を提供。
- 研究用ユーティリティ:
  - DuckDB 接続を利用したファクター計算、将来リターン計算、IC（Information Coefficient）等。
- AI 統合:
  - OpenAI（gpt-4o-mini 等）を呼び出し、ニュースから銘柄別センチメントやマクロセンチメントを算出。結果は ai_scores / market_regime 等のテーブルに書き込み。

前提条件（推奨）
----------------
- Python 3.10+
- 主要ライブラリ（少なくとも以下をインストール）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証のために任意）
- SQLite（標準ライブラリに含まれるため追加不要）

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
2. 必要パッケージをインストールします（requirements.txt がないため主要ライブラリを個別に）。
   - pip install duckdb psutil openai PyYAML
3. .env を用意します（推奨: python -m kabusys.config_setup で対話的に作成）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数の例:
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY (AI 機能を使う場合)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - LOG_LEVEL (例: INFO)
     - PAPER_FILL_MODE (instant|partial|never|reject)
4. データディレクトリを作成（必要に応じて）。
   - mkdir -p data logs

.env 自動読み込み
-----------------
- config.Settings モジュールはプロジェクトルート（.git または pyproject.toml）を探索し、.env/.env.local を自動読込します。
- テスト等で自動読込を無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（主要スクリプト）
------------------------

- 環境設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - strict モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）。
    - 実行中、data/stop_requested.flag の存在で安全に停止。
    - エンジンは PID ファイル（デフォルト: data/execution.pid）を扱います。

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 挙動:
    - デフォルトポーリング間隔: 60 秒（MONITOR_POLL_INTERVAL 環境変数で上書き可能; 正の整数）
    - 監視は Settings.sqlite_path（監視 DB）を本番パスとして使用（KABUSYS_ENV に依らず本番 DB を参照）。
    - 停止フラグを検知するとループを終了。

- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定（デフォルト: data/paper_trading.db）。

AI 機能（news_nlp / regime_detector）
------------------------------------
- OpenAI API を利用するため、OPENAI_API_KEY を設定してください。
- news_nlp.score_news(conn, target_date, api_key=None) は DuckDB 接続を受け取り ai_scores テーブルを書き換えます。
- regime_detector.score_regime(conn, target_date, api_key=None) は market_regime テーブルへ結果を書き込みます。
- エラー耐性（API エラー時はフォールバック動作）が組み込まれていますが、API キーが未設定だと ValueError を送出します。

ログ
----
- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（例: logs/execution.log）。日次ローテーション（30日保持）。
- 標準出力にもログを出力します（StreamHandler を stdout に設定）。

Kill Switch / 停止フラグ
-----------------------
- run_execution と run_monitoring はプロジェクト直下の data/stop_requested.flag（パスは定義参照）を確認し、存在時に起動停止や実行中停止を行います。
- KillSwitch は data/kill.flag を作成して ExecutionEngine の停止を要求します（監視が条件を満たしたときに作成）。
- ExecutionEngine 起動時に kill.flag を自動クリアする挙動は設定で制御できます（KILL_FLAG_CLEAR_ON_START）。

設定値バリデーションと YAML
---------------------------
- validate_config は .env の確認に加えて config/*.yaml の存在と構文チェック（PyYAML があれば YAML のパース検証）を行います。
- 主要な config ファイル例:
  - config/system_config.yaml
  - config/data_config.yaml
  - config/strategy_config.yaml
  - config/risk_config.yaml
  - config/execution_config.yaml
  - config/monitoring_config.yaml
- YAML がない場合は警告が出ますが必須ではありません（運用に応じて利用）。

ディレクトリ構成（主要ファイル）
------------------------------

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading レポート生成
  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (存在)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (存在)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（上記は主要ファイルの抜粋です。実際のリポジトリにはさらにモジュールが含まれます。）

サンプル .env（例）
------------------
以下は .env の最小例（実運用では機密情報を適切に管理してください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
PAPER_FILL_MODE=instant
KILL_FLAG_CLEAR_ON_START=0

注意事項 / 運用上のヒント
-----------------------
- paper_trading を使うときは PAPER_TRADING_SQLITE_PATH が本番 DB と分離されていることを必ず確認してください。
- 本番（KABUSYS_ENV=live）の場合、LINE 通知や各閾値の設定を慎重に確認してください。validate_config の live ガードが参考になります。
- MONITOR_POLL_INTERVAL は run_monitoring のポーリング間隔（秒）を環境変数で変更できます。1 以上の整数を指定してください。無効値はデフォルト 60 秒にフォールバックします。
- OpenAI 呼び出しには料金が発生します。バッチサイズやリトライ設定は ai/news_nlp.py / ai/regime_detector.py にて管理されています。
- ログディレクトリの作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります（警告あり）。

貢献・開発
----------
- 新しい機能を追加する際は unit テストや integration テストを追加してください（本リポジトリでは一部の関数が純粋関数として実装されておりテストが容易です）。
- 外部 API 呼び出し部分はモックしやすい設計になっています（_call_openai_api 等を patch）。

ライセンス
---------
- 本 README にはライセンス表記は含みません。実際のリポジトリの LICENSE ファイルを参照してください。

以上がこのコードベースの概要・セットアップ・使用方法です。追加で README に記載したいサンプルコマンドや詳しい設定例（監視閾値、RiskConfig の説明、ExecutionEngine の起動オプション等）があれば教えてください。必要に応じて README を拡張します。