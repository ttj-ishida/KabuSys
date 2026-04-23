KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買システム「KabuSys」のコードベース（主要モジュールのみ抜粋）です。本READMEではプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
---------------
KabuSys は、データ取り込み・因子計算・ポートフォリオ構築・注文発行・監視・アラート機能を備えた日本株自動売買システムです。構成は以下の要素で成り立っています。

- 実行エンジン（ExecutionEngine）: ブローカークライアントを通じた発注・注文管理・リスク管理・照合（reconciler）。
- 監視（Monitoring）: システム稼働状況・データ鮮度・注文ログ・リスクを監視し、必要に応じて Kill Switch（停止フラグ）を作成。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定、セクター上限などを純粋関数で実装。
- リサーチ（Research）: DuckDB を用いたファクター計算・特徴量探索・IC 計算。
- AI（OpenAI）連携: ニュースの NLP によるセンチメント集約（ai_scores）や市場レジーム判定。
- ユーティリティ: 設定ウィザード、設定検証、レポート生成など。

主な機能一覧
-------------
- 環境設定ウィザード（python -m kabusys.config_setup）: .env を対話的に作成/更新
- 設定検証（python -m kabusys.validate_config）: .env や config/*.yaml の整合性チェック
- 実行エンジン起動（python -m kabusys.run_execution）:
  - 本番 / ペーパー（paper_trading）モード対応
  - ペーパートレード時は MockBroker を使用し DB を分離
  - リスク管理（Position, Drawdown, Rate Limits など）
- 監視エンジン起動（python -m kabusys.run_monitoring）:
  - System / Trade / Risk モニタをポーリングしてログ保存・アラート評価
  - MONITOR_POLL_INTERVAL でインターバル変更可（デフォルト 60 秒）
- Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）
- AI ニューススコアリング（kabusys.ai.score_news）:
  - raw_news / news_symbols を集約して OpenAI にバッチ送信
  - 結果を ai_scores テーブルへ書き込み
- レジーム判定（kabusys.ai.regime_detector.score_regime）:
  - ETF（1321）MA200 とマクロニュースセンチメントを合成して market_regime を更新
- ロギング・プロセス優先度設定ユーティリティ（utils.logging_setup, utils.process_priority）
- DuckDB / SQLite を用いたデータ保持（分析用 DuckDB、監視用 SQLite）

セットアップ手順
----------------
前提
- Python 3.10 以上（コード中で | 型注釈等を使用）
- SQLite は標準搭載
- システムにより追加ライブラリが必要: duckdb, psutil, openai（AI 機能利用時）、PyYAML（設定検証で YAML チェックを有効にする場合）

推奨仮想環境の作成例
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
- Windows:
  - python -m venv .venv
  - .venv\Scripts\activate

依存関係のインストール（例）
- pip install duckdb psutil openai
- 設定検証で YAML を使う場合: pip install pyyaml

.env の作成
- 対話式ウィザード推奨:
  - python -m kabusys.config_setup
- 手動作成: プロジェクトルートに .env（.env.example を参考に）

設定検証（任意だが起動前推奨）
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱い（exit 1）

ディレクトリ・ファイル準備
- data, logs ディレクトリを作る（自動作成されることもありますが、権限等で失敗する場合があるため事前に作成推奨）
  - mkdir -p data logs

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABUSYS_ENV: 実行モード（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（INFO 等）
- OPENAI_API_KEY: OpenAI 利用時に必要
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用）

使い方（起動例）
----------------

1) 実行エンジン（Execution）
- 通常起動（設定済みの .env を前提）:
  - python -m kabusys.run_execution
- ペーパートレードで起動するには .env の KABUSYS_ENV=paper_trading を設定するか環境変数を設定:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパー時は PAPER_TRADING_SQLITE_PATH に記録され、本番 DB と分離されます
- 停止: 実行はスレッドで走るため、data/stop_requested.flag または data/kill.flag 等により制御できます（スクリプトは停止フラグを監視します）。run_execution は stop フラグを検知すると engine.stop() を呼びエンジン停止します。

2) 監視プロセス（Monitoring）
- 起動:
  - python -m kabusys.run_monitoring
- ポーリング間隔を変更する:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - デフォルトは 60 秒
- run_monitoring は Settings から sqlite_path（監視 DB）を読み接続します。Monitoring は KABUSYS_ENV にかかわらず sqlite_path を使用します（監視データは共通の監視 DB に保存されます）。

3) 設定の作成・検証
- .env を作る:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルトの DB パスは data/paper_trading.db。--db で別パス指定可。

5) AI 関連（OpenAI）
- ニュースセンチメント付与:
  - 利用例（ライブラリ呼び出し）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

注意点・運用上のポイント
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient と data/paper_trading.db を使用し本番 DB と完全に分離します。live モードは実際の発注を行うため注意。
- 監視プロセスは MONITOR_POLL_INTERVAL 環境変数で間隔を変更できます。無効な値はデフォルトにフォールバックし警告が出ます。
- Kill Switch:
  - RiskMonitor 等の評価で kill.flag を書き込むと ExecutionEngine に停止シグナルが送られます（data/kill.flag を参照）。
  - .env の KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアしますが、本番では 0 を推奨。
- ロギング:
  - kabusys.utils.logging_setup.setup_logging を利用し stdout と日次ローテーションファイル（logs/<app_name>.log）へ出力します。
- プロセス優先度:
  - 起動時に utils.process_priority.set_process_priority("high") が呼ばれ、可能であれば優先度を上げます（OS に依存・権限により失敗することあり）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys の主要モジュール構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - run_execution.py              # ExecutionEngine 起動スクリプト
    - run_monitoring.py             # SystemMonitor ポーリング起動スクリプト
    - config.py                     # Settings / .env 自動読み込みロジック
    - config_setup.py               # .env 対話式ウィザード
    - validate_config.py            # 設定検証 CLI
    - utils/
      - logging_setup.py            # ロギングセットアップ
      - process_priority.py         # 優先度 / CPU affinity ユーティリティ
    - execution/                     # 発注・リスク関係の実装群（Factory, Engine, Manager 等）
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py            # SQLite テーブル作成・永続化層
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - alert_manager.py
      - kill_switch.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py                  # ニュース NLP（OpenAI）関連
      - regime_detector.py          # レジーム判定ロジック
      - __init__.py
    - tools/
      - paper_verification_report.py
    - data/                          # 実行時に生成する想定のディレクトリ（DB / flag / pid）
    - logs/                          # ログ出力先（デフォルト）

ドキュメント・設計参照
---------------------
コード内には PortfolioConstruction.md や StrategyModel.md 等の設計ドキュメントを参照するコメントがあり、アルゴリズムの根拠やパラメータの説明が付されています。実運用ではそれらの設計文書もあわせて参照してください。

最後に
-------
この README はコードベースの主要な使い方と構成を概説したものです。開発・デプロイの前に .env を適切に設定し、validate_config によるチェックを行ってください。AI を使う機能は API キー（OPENAI_API_KEY）やコストに注意して運用してください。

必要であれば、README にサンプル .env のテンプレートや systemd / docker-compose の起動例、テスト手順を追加できます。どの追加情報が要るか教えてください。