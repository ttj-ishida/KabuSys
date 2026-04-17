KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。本リポジトリには以下の主要機能を提供するモジュールが含まれます。

- 注文実行エンジン（ExecutionEngine）およびブローカークライアントの抽象化（paper_trading によるモック対応）
- 監視コンポーネント（システム稼働・データ鮮度・注文滞留・リスク監視）
- Kill Switch（閾値超過時に停止フラグを書き込み Execution を安全停止）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイジング・セクター制限）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）および特徴量解析ユーティリティ
- AI 支援モジュール（ニュースのセンチメント評価、レジーム判定。OpenAI を利用）
- 各種ユーティリティ（プロセス優先度設定、DB 初期化、検証/設定ウィザード、レポート生成）

主な特徴
--------
- 環境分離: KABUSYS_ENV により development / paper_trading / live を区別。paper_trading 時は専用の SQLite（data/paper_trading.db）へ記録され本番 DB と分離されます。
- 監視・アラート: system / trade / risk の各監視器を統合し、LINE Push による一方向通知が可能（トークン未設定時はログのみ）。
- フェイルセーフ: OpenAI 等の外部 API 呼び出し失敗時にはフォールバックやリトライを行う設計（致命的例外を最小化）。
- DuckDB を利用したオフライン分析・研究（prices_daily, raw_financials などを参照）。
- .env による設定管理と対話式ウィザード、起動前設定検証ツールを提供。

セットアップ（開発環境）
--------------------
前提: Python（3.8+ 推奨）。SQLite は標準ライブラリで利用可能。

1. リポジトリをチェックアウト
   - 例: git clone ... && cd <repo>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（最低限）
   - pip install psutil duckdb openai requests PyYAML
   - 注意: 実行環境に応じて追加の依存がある可能性があります（テスト用 mocks 等）。

4. 初期環境変数設定
   - プロジェクトルートに .env を作成します。対話式ウィザードを利用することを推奨します:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 主要オプション:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方（起動例）
----------------

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使って PAPER_TRADING_SQLITE_PATH に記録。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は PID を data/execution.pid に書きます（PID ファイルの stale 検出処理あり）。
    - プロセス優先度を high に設定しようとします（権限不足時は警告）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 動作:
    - Settings の sqlite_path（監視 DB）へ接続し、SystemMonitor をポーリング。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。0 以下は無効でデフォルトにフォールバックします。
    - data/stop_requested.flag を検知すると監視ループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD （開始日）
    - --to YYYY-MM-DD （終了日）
    - --db PATH （DB ファイル指定。PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- AI 系機能
  - ニュースセンチメントスコア（ai/news_nlp.py）
    - kabusys.ai.score_news で呼び出し可能。OpenAI API キーが必要。
    - target_date（処理対象日）を与えて実行します。
  - レジーム判定（ai/regime_detector.py）
    - market_regime テーブルへ判定結果を書き込みます。OpenAI API キーが必要。

注意点／運用メモ
----------------
- paper_trading モードは本番 DB と完全分離されるよう設計されています。運用時は KABUSYS_ENV の値とパス設定を必ず確認してください。
- Kill Switch:
  - kill.flag（デフォルト: data/kill.flag）を作成すると ExecutionEngine に停止シグナルを送る仕組みがあります。Settings.kill_flag_clear_on_start を 1 にすると起動時に自動クリアされますが、本番では危険なので注意してください。
- データ鮮度:
  - SystemMonitor は DuckDB の prices_daily から最終価格日付を取得し、最新日が過去 3 日以内かを確認します（閾値はコード内で変更可能）。
- プロセス優先度:
  - set_process_priority("high") を呼びますが、Linux 等では権限が必要で失敗する可能性があります（警告のみ）。
- OpenAI 利用:
  - API レート制限やサーバーエラーに対して指数バックオフのリトライを実装していますが、API キー・コストには注意してください。
- 自動 .env ロード:
  - デフォルトでプロジェクトルートの .env / .env.local を自動ロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要ディレクトリ構成（src/kabusys）
---------------------------------
- __init__.py
- config.py
  - Settings クラス: 環境変数取得・バリデーション、自動 .env 読込ロジック
- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 起動前チェック（python -m kabusys.validate_config）
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト
- monitoring/
  - monitoring_db.py — SQLite 用のテーブル初期化と永続化 API（MonitoringDB）
  - monitoring_engine.py — 各 Monitor を束ねるループロジック
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常価格チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の書き込みロジック
  - alert_manager.py — LINE Push 通知のラッパ
- execution/ (発注ロジック関連 — サンプルとして OrderRepository 等が参照されています)
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, order_record.py 等（実行ロジック）
- portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 株数決定・集計キャップ処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム / ボラ / バリュー等の計算（DuckDB 利用）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ等
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
- tools/
  - paper_verification_report.py — Paper Trading のパフォーマンス / 稼働レポート生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

サンプル .env（最低限）
---------------------
以下は最低限必要な項目の例（実際は config_setup で生成してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx (AI 機能を使う場合)

追加情報 / トラブルシューティング
---------------------------------
- DB スキーマ初期化: monitoring_db.init_monitoring_db() は冪等で実行可能で、既存 DB に対する軽微なマイグレーション（カラム追加）にも対応します。
- DuckDB の接続はファイルパスで行い、研究用クエリは prices_daily / raw_financials / raw_news 等のテーブルを想定しています。
- validate_config が示す通り、production（KABUSYS_ENV=live）では LINE 通知設定や Kill Flag の設定等を厳密に確認してください。
- 実行中にプロセス優先度や CPU affinity の設定が失敗することがあります（権限不足）。その場合はログに警告が出て処理は継続します。

貢献・拡張
----------
- broker クライアントの実装や ExecutionEngine の戦略プラグイン追加、単体テストの充実、監視ルールの追加などが主な拡張ポイントです。
- AI 呼び出し部分はテスト容易性のため _call_openai_api をパッチしてモックできます（news_nlp.py / regime_detector.py にて設計済み）。

ライセンス
---------
（本 README にはライセンス情報が含まれていません。実プロジェクトでは LICENSE ファイルを必ず追加してください。）

以上。必要であれば README に含める具体的なコマンド例、さらに詳細な設定項目の説明や運用手順を追記します。