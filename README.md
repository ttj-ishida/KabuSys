KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのコンポーネント群です。  
主な役割は以下の通りです。

- ExecutionEngine：発注・注文管理・リスク管理などの実行系（本番 / ペーパートレード対応）
- Monitoring：システム稼働監視、トレード監視、キルスイッチ（危険時に Execution を停止）
- Research / Portfolio：ファクター計算、特徴量探索、ポートフォリオ構築・資金配分・ポジションサイジング
- AI モジュール：ニュースの NLP 評価 / 市場レジーム判定（OpenAI を利用）
- Tools：ペーパートレード検証レポート等のユーティリティ
- 設定ユーティリティ：.env を対話的に生成するウィザード、起動前検証 CLI

特徴一覧
--------
- 本番 / ペーパートレード（環境切替）をサポート
- DuckDB（分析用） + SQLite（監視 / 発注ログ）を併用する設計
- OpenAI を用いたニュースセンチメント評価・レジーム判定（フェイルセーフ実装）
- 監視用エンジン（System / Trade / Risk モニタ）と Kill Switch による自動停止機構
- ロギング統一化（コンソール + 日次ローテーションファイル）
- ペーパートレードの検証レポート生成機能（稼働率・約定率・レイテンシ等）

前提・依存
-----------
推奨環境
- Python 3.10+（型ヒント・モダンパッケージを利用。3.8+ でも動作する箇所あり）

主要 Python パッケージ（最低限）
- duckdb
- psutil
- openai
- PyYAML（validate_config の YAML 検証に使用。必須ではない）
SQLite は標準ライブラリに含まれます。

インストール（例）
- 仮想環境作成後:
  pip install duckdb psutil openai PyYAML

セットアップ手順
--------------
1. リポジトリをクローン / 展開
2. Python 仮想環境を作成して activate
3. 依存パッケージをインストール（上記参照）
4. .env の作成（対話ウィザード推奨）
   - 対話ウィザード:
     python -m kabusys.config_setup
   - 主要に必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他:
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR, OPENAI_API_KEY など

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     python -m kabusys.validate_config --strict

6. データディレクトリ等の作成
   - .env の path に指定した parent ディレクトリ（data/ や logs/）は基本的に自動作成されますが、必要に応じ手動で作成できます。

主要ファイル / 環境変数メモ
- data/
  - data/monitoring.db : デフォルトの監視用 SQLite（Settings.sqlite_path）
  - data/paper_trading.db : ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）
  - data/kabusys.duckdb : DuckDB（分析用、Settings.duckdb_path）
  - data/execution.pid : ExecutionEngine の PID ファイル（Settings.pid_file_path）
  - data/kill.flag / stop_requested.flag : Execution 停止用フラグ

- 環境変数の一部（代表）
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG/INFO/...
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: paper_trading の MockBroker の約定モード（instant/partial/never/reject）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）

使い方
------
起動スクリプト（モジュールとして実行）

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 停止方法:
    - data/stop_requested.flag を作成すると監視ループは検知して終了します

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と完全分離）
  - 起動時に data/stop_requested.flag が既にあれば起動せず終了
  - 実行中は data/execution.pid が作成されます。停止は stop flag を書き込むことでエンジンが停止します

ユーティリティ / ツール

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗と見なす

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - レポートは稼働率・約定率・送信率・P95 レイテンシ等を算出し PASS/FAIL を判定します

- AI / 研究機能（プログラムから呼び出す）
  - ニュース NLP（銘柄別センチメント算出）:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（conn）、target_date（date）、OPENAI_API_KEY または api_key 引数が必要
  - 市場レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 研究用ファクター計算:
    - kabusys.research.calc_momentum / calc_volatility / calc_value
  - ポートフォリオ構築:
    - kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes など

ログ
----
- ログはデフォルトで logs/ ディレクトリに app_name ごとのファイル（例: logs/execution.log）で日次ローテーション（30日保管）されます。  
- コンソール出力は stdout に出ます。ログ設定は kabusys.utils.logging_setup.setup_logging を使用して統一されています。

ディレクトリ構成（主要）
----------------------
src/kabusys/
- __init__.py
- config.py               — 環境変数 & Settings
- config_setup.py         — .env 対話ウィザード
- validate_config.py      — 起動前設定検証 CLI
- run_monitoring.py       — Monitoring ポーリングループ起動スクリプト
- run_execution.py        — ExecutionEngine 起動スクリプト

packages / サブモジュール（抜粋）
- kabusys/ai/
  - news_nlp.py           — ニュース NLP（OpenAI）で ai_scores を生成
  - regime_detector.py    — レジーム判定（MA + マクロセンチメント）

- kabusys/monitoring/
  - monitoring_db.py      — SQLite テーブルの初期化 & 簡易永続化 API
  - system_monitor.py     — システム監視（CPU/メモリ/ディスク、データ鮮度、プロセス生死）
  - trade_monitor.py      — （トレード監視: 滞留注文・約定異常など）※実装参照
  - risk_monitor.py       — ドローダウン / ポジション上限監視
  - monitoring_engine.py  — 各モニタの束ね、Kill Switch 評価、アラート通知

- kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
    — Execution の主要実装（発注・管理・リスク）

- kabusys/research/
  - factor_research.py     — Momentum / Volatility / Value の計算
  - feature_exploration.py — 将来リターン計算、IC、統計概要

- kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- kabusys/utils/
  - logging_setup.py       — ロギング初期化
  - process_priority.py    — プロセス優先度 / affinity 設定ユーティリティ

運用上の注意
-------------
- KABUSYS_ENV=live の場合は本番環境です。LINE 等の通知設定や Kill Switch の設定を十分に確認してください（validate_config の live 用ガードあり）。
- OpenAI API を叩く機能は外部 API を利用するため、API キーの管理とコストに注意してください。API 失敗時はフォールバック動作をするよう設計されていますが、事前に十分なテストを行ってください。
- ペーパートレードは本番 DB と可能な限り分離されていますが、設定ミスに備えバックアップを用意してください。
- logs/ や data/ のファイルパスは .env で上書き可能です。

貢献 / 拡張案
-------------
- 銘柄別単元（lot_size）やブローカー別実装の拡張
- 詳細なモニタリングメトリクスの追加（ネットワーク、API レートなど）
- AI の出力検証・キャリブレーション用のテストスイート追加
- DuckDB を用いたバッチ解析スクリプトの強化

ライセンス・バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

最後に
-----
この README はコードベース内の主要スクリプト・モジュールから要点をまとめたものです。詳しい実装や追加の設定は該当モジュール（例: kabusys/ai/news_nlp.py、kabusys/monitoring/*、kabusys/execution/*）の docstring とソースを参照してください。質問や具体的な実行例が必要であれば、実行したいユースケースを教えてください。