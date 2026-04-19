KabuSys — 日本株自動売買システム（簡易 README）
==================

本リポジトリは日本株向けの自動売買・研究・監視機能を含むモジュール群です。  
ここではプロジェクト概要、主な機能、セットアップ手順、起動方法（利用方法）、および主要ディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
KabuSys は以下の目的を持つ Python パッケージ群です。

- 取引エンジン（ExecutionEngine）: ブローカーとのインタフェースを通じて発注、注文管理、リスク管理を行う。
- 監視（Monitoring）: システム稼働状況、注文ログ、リスク（ドローダウン・ポジション数等）を定期的にチェックし、アラート／Kill Switch を制御。
- 研究（Research）: DuckDB 上の時系列データに対するファクター計算・特徴量解析機能。
- AI 補助（AI）: OpenAI を用いたニュースセンチメント評価や市場レジーム判定。
- ペーパートレード用の分離データベースと検証ツール。

主要な実行スクリプト:
- run_execution.py — ExecutionEngine の起動スクリプト
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- config_setup.py — .env 対話式セットアップウィザード
- validate_config.py — 起動前設定検証 CLI
- tools/paper_verification_report.py — ペーパートレード検証レポート生成

主な機能一覧
-------------
- 環境設定ウィザード (.env) と自動ロード機能
- 実行環境切替: development / paper_trading / live
  - paper_trading では MockBrokerClient を使用し、本番 DB と分離
- 監視機能:
  - システムリソース（CPU/メモリ/ディスク）
  - データ鮮度（prices_daily 等）
  - 注文ログ / 約定レイテンシ監視
  - リスク監視（ドローダウンアラート、ポジション上限）
  - Kill Switch（data/kill.flag）による ExecutionEngine 停止
- ログ管理:
  - 共通の setup_logging で stdout と日次ローテートファイル出力を統一
- プロセス優先度設定（High/Normal/Low）と CPU affinity 設定補助
- ポートフォリオ構築ユーティリティ（候補選定 / 重み付け / 位置サイズ計算 / セクター制限）
- DuckDB を用いたファクター計算・将来リターン・IC 計算
- OpenAI を使用したニュースセンチメントとレジーム判定（フェイルセーフ、バッチ処理・リトライ実装）
- ペーパートレード用検証レポート（稼働率、成功率、レイテンシ等の集計と判定）

セットアップ手順（推奨）
-----------------------
1. Python と仮想環境
   - Python 3.9+ を推奨（プロジェクト要件に合わせて調整してください）。
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - requirements.txt が提供されている場合:
     - pip install -r requirements.txt
   - 主要依存（最低限）:
     - duckdb, psutil, openai
   - 任意（YAML 検証を使う場合）:
     - PyYAML

3. .env の初期作成（推奨）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - PAPER_FILL_MODE（paper_trading 用: instant / partial / never / reject）

   - 自動ロードの注意:
     - パッケージ初期化時に .env を自動読み込みします（プロジェクトルートが検出される場合）。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定検証
   - 起動前に設定を検証:
     - python -m kabusys.validate_config
     - 警告を失敗扱いにする場合は --strict を付与

5. データディレクトリ
   - デフォルトの DB/ログ/flag 保存先:
     - data/ (monitoring.db, paper_trading.db, kill.flag, *.pid, stop_requested.flag ...)
     - logs/ (execution.log, monitoring.log 等)
   - 必要に応じて環境変数でパスを変更してください。

使い方（起動例）
-----------------

- ExecutionEngine を起動（通常、バックグラウンドや supervisor/システムサービス より実行）
  - python -m kabusys.run_execution
  - 起動時にプロセス優先度を "high" に設定します。
  - KABUSYS_ENV=paper_trading の場合は MockBroker が使われ、PAPER_TRADING_SQLITE_PATH に書き込みます。
  - data/stop_requested.flag が存在すると起動を中断または実行中に停止します。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
  - Monitoring は常に production 相当の sqlite_path（SQLITE_PATH）を参照します（環境に依らず）。
  - stop_requested.flag によりループを終了します。

- .env の対話式生成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- その他ユーティリティ
  - 研究用モジュールは duckdb 接続を渡して直接呼び出す:
    - kabusys.research.calc_momentum 等
  - AI スコアリング / レジーム判定:
    - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
    - OPENAI_API_KEY の設定が必須（引数で明示することも可能）

重要な挙動・運用上の注意
-----------------------
- Kill Switch:
  - kill.flag（Settings.kill_flag_path デフォルト data/kill.flag）を書き込むと ExecutionEngine 側で停止要求として扱います。
  - KILL_FLAG_CLEAR_ON_START=1 を有効にすると起動時に自動で kill.flag をクリアしますが、本番では 0 を推奨します。

- DB 分離:
  - paper_trading モードでは paper_trading 用の SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番データと分離されます。
  - Monitoring は常に SQLITE_PATH を参照します（監視用 DB）。

- ロギング:
  - setup_logging により stdout と logs/<app>.log（日次ローテート）に出力します。
  - LOG_DIR 環境変数でログディレクトリを変更可能。

- プロセス管理:
  - 起動スクリプトは実行時にデフォルトでプロセス優先度を "high" に設定します。
  - PID ファイル（data/execution.pid 等）が使用されます。既存の stop/kill flag を確認してから起動してください。

ディレクトリ構成（主要ファイル）
----------------------------
以下は src/kabusys 以下の主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env の読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト

  - ai/
    - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py      — 市場レジーム判定（ma200 + macro sentiment）

  - monitoring/
    - monitoring_db.py        — SQLite の監視テーブル定義 / DB 操作ラッパ
    - system_monitor.py       — システムリソース・データ鮮度チェック
    - trade_monitor.py        — （注文ログ監視）※実装詳細ファイルあり
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 制御ロジック
    - monitoring_engine.py    — 全モニタを束ねる Polling Engine
    - alert_manager.py        — アラート送信（LINE 等）※実装あり

  - execution/
    - execution_engine.py     — 実行エンジン（セッション管理、発注ループ等）
    - broker_factory.py       — BrokerClient の生成（Mock / 実API 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 発注株数決定（lot 単位丸め、aggregate cap）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py      — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ

  - monitoring/ (既出)
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

  - utils/
    - logging_setup.py        — 共通ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - その他ユーティリティ

- その他（プロジェクトルート）
  - .env.example              — （存在する場合）.env の例
  - config/*.yaml             — 設定テンプレート（generate 用）
  - data/                     — デフォルトの DB / flag / pid の保存先
    - kabusys.duckdb (default)
    - monitoring.db (default)
    - paper_trading.db (default)
    - kill.flag, stop_requested.flag, execution.pid, ...
  - logs/                     — ログファイル保存先（デフォルト）

追加情報 / トラブルシューティング
--------------------------------
- PyYAML がインストールされていない場合、validate_config は YAML の中身検証をスキップします（警告）。
- DuckDB の接続は各モジュールで期待するテーブル（prices_daily, raw_financials, raw_news, ai_scores, market_regime 等）が存在することが前提です。データ投入パイプラインは別途用意してください。
- OpenAI API 呼び出し部分はリトライ・クリッピング・レスポンス検証を実装していますが、API キーやレート制限に注意してください。
- 実運用での起動・監視は systemd / supervisor / k8s 等のプロセスマネージャで管理することを推奨します（ログローテーション・PID 管理・再起動ポリシーなど）。

最後に
-------
ここに記載したのはコードベースから読み取れる主要な使い方と注意点の概略です。実運用前には必ず:
- .env を設定し validate_config で検証
- 小規模なローカルテスト（paper_trading）で機能確認
- モニタリング・Kill Switch の動作確認
を行ってください。

必要であれば、README をより詳細（例: systemd サービス定義、Dockerfile、requirements.txt、実運用手順）に拡張します。どの情報を追加したいか教えてください。