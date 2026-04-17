# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買に関するコアライブラリと起動スクリプト群を含みます。  
README はコードベース（src/kabusys 以下）をもとに作成しています。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド / 実行例）
- 環境変数（主な設定項目）
- ディレクトリ構成

プロジェクト概要
- KabuSys は日本株自動売買システムのコアモジュール群（注文・リスク管理・ポートフォリオ構築・監視・研究・AI 補助など）を提供します。
- モジュール設計は本番/ペーパートレードを分離し、安全機構（Kill Switch / リスク監視 / アラート）を備えます。
- DB は分析用に DuckDB、運用ログ・監視用に SQLite を使用します。OpenAI（LLM）を利用する機能も含まれます（任意）。

主な機能一覧
- Execution 起動スクリプト（run_execution.py）
  - 実際の ExecutionEngine をスレッドで起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite に記録して本番 DB と分離。
  - 停止フラグ（data/stop_requested.flag）で安全停止。
  - PID ファイル管理（data/execution.pid）。
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor をポーリングして CPU/メモリ/Disk・データ鮮度・プロセス状態などを監視。監視データは monitoring 用 SQLite に永続化。
  - ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に production sqlite_path を使用（環境に依らず）。
- 監視コンポーネント
  - SystemMonitor：プロセス存在確認、データ鮮度チェック、system_status に記録
  - TradeMonitor：滞留注文、約定価格の異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新、risk_logs への記録
  - KillSwitch：条件に応じて data/kill.flag を書き込み、Execution に停止シグナルを送る
  - MonitoringEngine：これらを束ねてポーリングしアラート通知（AlertManager 経由）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等分・スコア重み、セクター制約、レジームに応じた乗数、ポジションサイズ計算（単元株丸め等）
- 研究（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）、将来リターン、IC（情報係数）計算、統計サマリー
  - DuckDB を用いた SQL + Python ベースの処理
- AI（kabusys.ai）
  - news_nlp: raw_news を集約し OpenAI に送って銘柄ごとのセンチメントを ai_scores に格納
  - regime_detector: ETF(1321) MA200 乖離＋マクロニュースの LLM 評価で市場レジーム判定
  - OpenAI API（OPENAI_API_KEY）が必要。API 呼び出しはフェイルセーフ設計（リトライやフォールバック）
- ツール
  - config_setup.py：.env を対話式で作成/更新するウィザード
  - validate_config.py：.env と config/*.yaml の簡易検証 CLI
  - tools/paper_verification_report.py：ペーパートレードの検証レポート生成

セットアップ手順（開発向け）
1. 前提
   - 推奨 Python バージョン：3.10+
   - システムに SQLite があれば OK（標準ライブラリ）
2. 仮想環境の準備（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージのインストール
   - 最低限の依存（例）
     - pip install duckdb psutil openai
   - 追加（validate_config の YAML 検証を有効にする場合）
     - pip install PyYAML
   - （実運用で利用する場合は broker 等の実装に応じた依存を追加）
4. 環境変数の設定
   - プロジェクトルートに .env を置くか、環境変数で設定します。
   - 自動ロード機構が組み込まれており、.env（→ .env.local）の順で読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - .env を対話式で作るには:
     - python -m kabusys.config_setup
   - 作成後、設定検証:
     - python -m kabusys.validate_config
     - 本番前に --strict オプションを推奨: python -m kabusys.validate_config --strict

使い方（主要コマンド / 実行例）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict
- Execution エンジン起動（本番/ペーパートレードに従う）
  - python -m kabusys.run_execution
  - ペーパートレード時は KABUSYS_ENV=paper_trading を設定すると paper_trading DB を使用
  - stop：data/stop_requested.flag を作成すると安全に停止（run_execution はこのフラグを監視）
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔の変更（秒）:
    - export MONITOR_POLL_INTERVAL=30
  - stop：data/stop_requested.flag を作成するとループを抜けます
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- 注意
  - AI 機能（kabusys.ai.*）を使うには OPENAI_API_KEY を設定する必要があります。未設定だと例外を投げる箇所があります。

環境変数（主な設定項目）
- 必須（validate_config にてチェック）
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
  - LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- データベースパス
  - DUCKDB_PATH — 分析用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- Paper Trading 動作
  - PAPER_FILL_MODE — "instant" | "partial" | "never" | "reject"（デフォルト: instant）
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必要）
- LINE（任意、アラート送信に使用）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- 監視 / Kill Switch
  - PID_FILE_PATH — 実行 PID ファイルのパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアする（"1" で有効。production は "0" 推奨）
- 監視ループ間隔
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト: 60）

データ / フラグファイル（デフォルト）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/stop_requested.flag — run_* スクリプトが監視して停止するためのフラグ
- data/kill.flag — KillSwitch が書き込む（Execution に停止シグナル）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数の読み取り・.env 自動ロードロジック
  - config_setup.py — .env 作成ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレードの検証レポート
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄スコア化
    - regime_detector.py — マーケットレジーム判定（MA200 + LLM）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ / 永続化クラス（MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送信ロジック)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py
  - （execution 以下に ExecutionEngine 実装や broker_factory 等が存在すると想定）

トラブルシューティング & 補足
- validate_config.py は PyYAML が無いと config/*.yaml のパース検証をスキップします（警告表示）。PyYAML を入れると YAML 構成の検証が可能です。
- news_nlp / regime_detector は OpenAI API 呼び出しを行います。API キーやネットワークの問題に対してはリトライやフォールバック動作を行う設計ですが、API キー未設定だと関数が ValueError を投げます。
- run_monitoring.py は「監視」用で、監視は常に Settings.sqlite_path（本番 path）を参照します。開発中に監視 DB を分離したい場合は Settings のパスを調整してください。
- process priority / CPU affinity 設定は psutil に依存します。権限不足や OS 非対応時は警告を出してスキップします。

開発者向け注意点
- コード内の時間処理はルックアヘッドバイアスを避ける意図で date.today() / datetime.today() を直接参照しない設計になっている箇所があります（AI モジュール等）。
- DB マイグレーション（monitoring_db.init_monitoring_db）は既存カラムの有無をチェックして必要なら ALTER TABLE で列を追加するようになっています（冪等）。

貢献 / 拡張
- AlertManager の実装（LINE などの通知送信）や BrokerClient の具体実装、ExecutionEngine の詳細ロジックは実装/拡張ポイントです。
- 単体テストや CI で .env の自動ロード無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD）を利用するとテストが安定します。

以上が本リポジトリの README（日本語）になります。README に追加したい具体的なコマンド例や .env のテンプレート（例: .env.example）をお望みであれば追記します。どの部分をより詳しく書くか（例: ExecutionEngine の起動手順、AlertManager の設定方法など）を教えてください。