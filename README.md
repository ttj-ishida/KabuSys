KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買／研究／監視を目的とした軽量なフレームワークです。  
README はコードベース（src/kabusys 以下）を基に日本語でまとめています。

概要
----
KabuSys は以下の機能を持つモジュール群で構成されたシステムです。

- 注文実行エンジン（ExecutionEngine）
  - 本番接続 / ペーパートレード（モックブローカー）をサポート
  - 注文管理、リスク管理、リコンサイル機能
- 監視（Monitoring）
  - システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を監視
  - Kill Switch（条件を満たしたら Execution を停止するフラグ）
- ポートフォリオ構築（Portfolio）
  - 候補選定、重み計算、ポジションサイズ計算、セクター上限・レジーム調整
- 研究用モジュール（Research）
  - ファクター計算、将来リターン、IC 計算、特徴量探索
- AI 補助（AI）
  - ニュース NLP（OpenAI）を使った銘柄センチメント、レジーム判定
- 運用ツール
  - Paper Trading 検証レポート生成スクリプト 等
- 共通ユーティリティ
  - 設定管理、ログ設定、プロセス優先度設定等

主な特徴
--------
- 環境変数ベースでの設定 (.env をサポート、interactive ウィザードあり)
- production / paper_trading / development の実行モード切替
- DuckDB（分析用）および SQLite（監視・履歴）の併用
- OpenAI API を使ったニュースセンチメント・レジーム判定（任意）
- 実運用向けの監視ループ・アラート（kill.flag 等の仕組み）

必要要件（概略）
----------------
- Python 3.10+
- ポピュラーなライブラリ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - pyyaml（設定ファイル検証時にあると便利）

簡単なインストール例
--------------------
仮想環境を使うことを推奨します。

1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil

3. AI 機能を使う場合：
   - pip install openai

4. 設定検証・YAML 検証を行うなら：
   - pip install pyyaml

設定（.env）
------------
プロジェクトルートに .env を置くか、環境変数で設定します。自動ロード機能あり（.env/.env.local を自動読み込み。無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY （AI 機能を使う場合）
- KABUSYS_ENV （development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
- SQLITE_PATH （監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH （paper_trading モード用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL （デフォルト: INFO）
- LOG_DIR （デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START （0 / 1、デフォルト 0）

.env を対話的に作る
------------------
付属のウィザードを使うと .env の生成を補助します。

- 実行:
  - python -m kabusys.config_setup

設定の検証
--------
作成した設定・ファイルや環境変数のチェックができます。

- 実行:
  - python -m kabusys.validate_config
- 厳密モード（警告も FAIL）:
  - python -m kabusys.validate_config --strict

起動と使い方（メインのスクリプト）
---------------------------------

1) 監視ループ（SystemMonitor）起動
- 目的: システム稼働監視・データ鮮度確認・監視ログ保存
- 実行:
  - python -m kabusys.run_monitoring
- オプション/挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定（デフォルト 60）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで検知して停止
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視 DB に接続

2) ExecutionEngine 起動（実注文 / ペーパートレード）
- 目的: 発注ループの起動（EngineConfig 等を使って当日セッションを実行）
- 実行:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用しデータは data/paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止
  - 実行中に stop_requested.flag を作成すると停止処理を行う
  - 実行中は data/execution.pid に PID が書かれる（設定により場所変更可）

3) Paper Trading 検証レポート
- 目的: ペーパートレード DB を元に期間別パフォーマンス / 稼働性指標を出力
- 実行例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを直接指定可能（省略時は環境変数 PAPER_TRADING_SQLITE_PATH or data/paper_trading.db）

AI / LLM 関連
-------------
- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約し OpenAI に送って銘柄別センチメントを ai_scores テーブルへ保存
  - OPENAI_API_KEY が必要
  - リトライ / 失敗時のフォールバックが実装されている（安全設計）
- レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）MA200 とマクロニュースの LLM スコアを合成して market_regime に書き込む

ログ
----
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション、30日保管）へ出力されます。
- ログの設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
- LOG_DIR 環境変数でログ出力先を変えられます。

監視・停止フラグ
----------------
- Kill Switch:
  - 条件（ドローダウン超過、ポジション上限超過等）を満たすと data/kill.flag が作成され ExecutionEngine に停止シグナルを送ります。
  - KillSwitch は冪等に振る舞い、既存の flag を上書きしません。
- stop_requested.flag:
  - run_monitoring / run_execution は data/stop_requested.flag の存在を見て自発停止します。
- kill.flag を自動でクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できますが、本番では 0 を推奨します。

DB とマイグレーション
--------------------
- 監視 DB（SQLite）スキーマの初期化・マイグレーションは kabusys.monitoring.monitoring_db.init_monitoring_db() が担います。
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルなどを作成／必要カラム追加を行います。
- 分析用データは DuckDB（デフォルト data/kabusys.duckdb）で扱います。

主要ディレクトリ構成
--------------------

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み／Settings クラス（各種設定プロパティ）
- config_setup.py
  - 対話式 .env ウィザード
- validate_config.py
  - 設定検証 CLI
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト

subpackages:
- ai/
  - news_nlp.py — ニュースを LLM で評価して ai_scores に書き込む
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — 監視用 SQLite 永続化層
  - system_monitor.py — システム状態 / データ鮮度監視
  - trade_monitor.py —（注文ログの監視ロジック、コードベースに同名モジュールあり）
  - risk_monitor.py — ドローダウン・ポジション数監視
  - kill_switch.py — kill.flag 制御
  - monitoring_engine.py — 複数 Monitor を束ねるエンジン
  - alert_manager.py —（アラート通知の管理）
- execution/
  - execution_engine.py — 実行エンジン本体
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み付け
  - position_sizing.py — 銘柄別株数計算・集約制限
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン / IC / 統計要約
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — ログ設定ヘルパ
  - process_priority.py — プロセス優先度・affinity 設定ユーティリティ
  - その他ユーティリティ群
- data/ (ランタイムに作られる想定)
  - monitoring DB / paper_trading DB / kill.flag / execution.pid / stop_requested.flag などを配置

開発メモ・注意点
----------------
- Python の型ヒントで | 演算子（PEP 604）を使用しているため Python 3.10+ が必要です。
- .env は絶対にリポジトリへコミットしないでください（機密情報含む）。
- run_monitoring は監視 DB に対して本番 sqlite_path を使用します。開発環境で安全に試す場合は sqlite_path を別ファイルに変更してください。
- AI 関連は外部 API（OpenAI）に依存します。API キーやレート制限に注意してください。
- process_priority.set_process_priority() はプラットフォーム依存で失敗する場合があります（権限不足など）。失敗時は警告に留めて起動を続行します。

よくある操作例
--------------
- .env を作る（ウィザード）
  - python -m kabusys.config_setup
- 設定チェック
  - python -m kabusys.validate_config
- 監視を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- エンジン（Execution）を起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

貢献・拡張案
-------------
- ブローカークライアントの追加（実ブローカー連携）
- 単元サイズを銘柄ごとにサポート（現状は共通 lot_size）
- アラート送信バックエンド（LINE / Email など）を AlertManager に追加
- DuckDB スキーマ拡張と分析パイプライン自動化
- テスト・CI（ユニットテスト・モックを充実）

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状: 0.1.0）。

おわりに
--------
この README は現行のソースを元に主要な使い方・構成をまとめたものです。実際の運用前には必ず python -m kabusys.validate_config で設定を検証し、テスト環境で動作確認を行ってください。質問や追加説明が必要な箇所があれば教えてください。