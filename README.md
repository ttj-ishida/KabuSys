README
=====

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤の軽量フレームワークです。  
主な機能として、取引実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を利用したセンチメント評価）などを備えています。  
バージョン: 0.1.0

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード（分離された SQLite）に対応
  - リスク管理、注文管理、リコンサイル機能を備える
- Monitoring（監視）
  - CPU/メモリ/ディスク・プロセス稼働・データ鮮度などを定期記録
  - Kill Switch（ドローダウンやポジション上限で止めるフラグ）
  - アラート発行フック
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額やスコア加重配分、ポジションサイズ計算
  - セクターキャップ・レジーム乗数適用
- Research（リサーチ）
  - DuckDB を用いたファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI（OpenAI 連携）
  - ニュースを LLM でスコア化して ai_scores に保存
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証（validate_config）
  - ペーパートレード検証レポート生成スクリプト

前提条件
--------
- Python 3.10 以上を推奨（PEP 604 の型表記などを使用）
- SQLite（標準ライブラリ）
- 主要外部ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証時に任意で使用）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリに移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそれを使ってください）

4. 初回設定（.env の作成）
   - 対話式ウィザードを使う: python -m kabusys.config_setup
     - J-Quants / kabuAPI の認証情報や DB パス等を対話で作成できます。
   - 手動で .env を作る場合は .env.example（存在する場合）を参照してください。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 必要なら厳密モード: python -m kabusys.validate_config --strict

6. データディレクトリの作成（必要に応じて）
   - デフォルト DB 等は data/ 以下を参照します。自動作成される場合もありますが、権限等に注意してください。
   - 例: mkdir -p data logs

環境変数（主なもの）
--------------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 主要（既定値あり）
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
  - PAPER_FILL_MODE — ペーパートレードでの約定挙動（instant/partial/never/reject）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring で使用。デフォルト 60）

- ファイル/フラグ
  - PID_FILE_PATH（デフォルト data/execution.pid）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（"1" で起動時に kill.flag を自動クリア、デフォルト "0"）

使い方（起動コマンド）
---------------------
- 環境設定ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine の起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 起動時にプロセス優先度を High に設定し、実行中は data/execution.pid を管理します。

- Monitoring の起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60）
  - 監視は常に（KABUSYS_ENV に関係なく）本番用 sqlite_path を使用してログを記録します。
  - 停止フラグは data/stop_requested.flag を参照します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 範囲指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- AI 機能（プログラムから呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...) の返す接続）を受け取り、データベースのテーブルを参照・更新します。OpenAI API キーが必要です。

運用上の注意
------------
- KABUSYS_ENV=live の場合は本番データ・実発注になります。LINE 等の通知設定を必ず確認してください。
- KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag が消えるため、本番では 0 を推奨します。
- run_monitoring は監視情報を常に production sqlite_path に記録します（環境に依存せず）。
- ペーパートレードと本番は DB を分離する設計（PAPER_TRADING_SQLITE_PATH を利用）です。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール（抜粋）です。実際のリポジトリでも同様の構成を想定してください。

- src/kabusys/
  - __init__.py  (バージョン定義)
  - config.py             （環境変数・設定管理）
  - config_setup.py       （.env 対話式ウィザード）
  - validate_config.py    （起動前設定検証 CLI）
  - run_execution.py      （ExecutionEngine 起動スクリプト）
  - run_monitoring.py     （SystemMonitor ポーリング起動スクリプト）
  - tools/
    - paper_verification_report.py  （ペーパートレード検証レポート）
  - execution/            （ExecutionEngine 関連: broker, order_manager, risk_manager 等）
  - monitoring/
    - monitoring_db.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用するファイル群)
    - monitoring.db (デフォルトの sqlite)
    - paper_trading.db (ペーパートレード用 DB)
    - stop_requested.flag, kill.flag, execution.pid などのフラグファイル／PIDファイル
  - config/ (YAML 設定テンプレート群)
    - system_config.yaml
    - data_config.yaml
    - strategy_config.yaml
    - risk_config.yaml
    - execution_config.yaml
    - monitoring_config.yaml

開発／デバッグのヒント
---------------------
- ログは logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリを作成）。
- 設定検証（validate_config）は YAML のパースに PyYAML を使います。未インストール時は内容検証をスキップします。
- OpenAI 呼び出しは外部コールなので開発時はモック化（unittest.mock）を推奨します。news_nlp と regime_detector の API 呼び出し関数はテストで差し替え可能な設計です。
- ペーパートレードの検証は tools/paper_verification_report.py を使うと主要指標（稼働率・注文成功率・レイテンシ等）をまとめて確認できます。

ライセンス
----------
（リポジトリに記載のライセンスがあればここに追記してください）

お問い合わせ / 貢献
------------------
バグ報告や機能追加は Issue / Pull Request を送ってください。README に付け加えるべき実運用情報や追加サンプルがあれば PR を歓迎します。

以上。