# KabuSys

日本株向けの自動売買・研究・監視用ライブラリ群および起動スクリプト群です。  
本リポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算・リサーチ、AI を使ったニューススコアリングなどのコンポーネントを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要条件・依存パッケージ
- セットアップ手順
- 環境変数（.env）と代表的な設定
- 実行方法（使い方）
- よく使う CLI / スクリプト一覧
- ディレクトリ構成（概観）
- 補足・運用メモ

---

プロジェクト概要
- KabuSys は「日本株自動売買システム」のコアロジック群を提供します。
- 発注・注文管理・リスク管理・監視（システム/取引/リスク）・ポートフォリオ構築・ファクター計算・ニュース NLP（LLM を利用したセンチメント）などを含みます。
- 設定は .env により管理。実行環境（development / paper_trading / live）により動作が切り替わります。

---

主な機能
- ExecutionEngine（発注・注文管理・リスク制御）
  - paper_trading（モックブローカー）と live（実ブローカー）を切り替え可能
  - 発注ログ / ポジション管理を SQLite に永続化
- Monitoring（監視）
  - CPU / メモリ / ディスク使用率、プロセス生存チェック、データ鮮度チェック
  - トレード／リスク監視、Kill Switch（条件による実行停止）/ アラート連携
- Portfolio（ポートフォリオ構築）
  - 候補選定、等分配・スコア加重、ポジションサイズ算出、セクター制限・レジーム乗数
- Research（研究）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン、IC 計算、統計サマリー
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 等）を用いたニュースの銘柄別センチメント算出（ai_scores テーブルへ書込）
  - マクロ見出しを用いた市場レジーム判定（market_regime テーブル）
- ツール
  - Paper Trading の検証レポート出力ツール（過去期間の稼働率・注文成功率・レイテンシなどを集計）

---

必要条件・依存パッケージ（主要）
- Python 3.9+（型注釈や一部の新構文を使用）
- 必須（本リポジトリから参照されている外部ライブラリ）
  - duckdb
  - psutil
  - openai
- 任意（機能に応じて）
  - PyYAML（config/*.yaml のパース検証に使用。未インストールでも動作は可能）
- SQLite / DuckDB はそれぞれ Python 標準モジュール / duckdb パッケージで扱います。

例（pip）
pip install duckdb psutil openai pyyaml

---

セットアップ手順（ローカル）
1. リポジトリをクローン / 作業フォルダへ配置
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合）pip install -r requirements.txt
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 生成後、設定を検証: python -m kabusys.validate_config
5. データディレクトリ等の作成（通常は自動作成されますが手動で準備しても良い）
   - デフォルト DB / ファイル: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag
6. （Paper / AI を使う場合）OPENAI_API_KEY を .env に設定

---

環境変数（代表例）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB パス / ログ
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用、デフォルト）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
  - LOG_DIR: ログ保存先（デフォルト: logs/）
- AI
  - OPENAI_API_KEY: OpenAI API キー（news/regime 機能で使用）
- 監視関連
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

.env の自動読み込み
- プロジェクトルートに .env / .env.local があれば自動で読み込みます（OS 環境 > .env.local > .env の優先順）
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡単な .env サンプル（対話ウィザードを推奨）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

使い方（代表的なコマンド）
- 環境セットアップ（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
    - --strict を付けると警告もエラー扱いで exit(1)
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録します
    - 起動時に data/execution.pid に PID を書き込み、data/stop_requested.flag を監視して停止する
    - 起動直後にプロセス優先度を "high" に設定します（可能な環境で）
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は本番 sqlite_path を利用（KABUSYS_ENV に依存しません）
    - data/stop_requested.flag の存在で監視ループを終了
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）
- AI / バッチ関数（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  # DuckDB 接続を渡して実行
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

監視・停止制御（ファイルベース）
- Kill Switch（システム側が条件を満たすと data/kill.flag を書き込み）
  - ExecutionEngine は起動時に kill.flag を確認し、自動起動しないオプションを提供
- 手動停止
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のメインループが検知して終了する

ログ
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
- デフォルトはコンソール (stdout) と日次ローテートされたファイル (logs/<app_name>.log) に出力
- ログディレクトリは LOG_DIR 環境変数かデフォルト logs/（自動作成）

---

ディレクトリ構成（主要ファイル / モジュールの概観）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別スコア算出
    - regime_detector.py — マクロニュース + ETF MA を使ったレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite に対する永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py — （取引監視ロジック; 本 README では概要）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各モニタを束ねるランナー
    - alert_manager.py — （アラート送信を担う部分）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出・単元丸め・キャップ処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - （その他: execution/ data/ strategy/ 等、実装モジュール群）

（注）上記はソースの抜粋に基づく概観です。実際のリポジトリにはさらに細かなモジュール、実装ファイルが存在する可能性があります。

---

補足・運用メモ
- paper_trading モードでは実ブローカーに発注せず、専用の SQLite（PAPER_TRADING_SQLITE_PATH）へ記録するため本番 DB と完全分離して検証できます。
- 設定検証ツール（validate_config）は .env と config/*.yaml の存在や基本妥当性チェックを行います。--strict で警告も失敗にできます。
- AI 機能を運用する場合は OpenAI の API 使用料が発生します。バッチ実行の頻度と API コール数に注意してください。
- ローカル / CI から自動で .env を読み込む仕組みがありますが、本番環境では OS 環境変数による上書きを保護するため .env の上書きを制御しています。
- DB マイグレーションの簡易対応（monitoring_db.init_monitoring_db）は実装済みで、既存カラムの有無をチェックして追加する処理があります。

---

問題発生時のトラブルシュート（簡易）
- ログが出力されない / ログファイルが作成されない
  - LOG_DIR の書込権限、ディレクトリ作成の失敗を確認
- ExecutionEngine がすぐ停止する
  - data/stop_requested.flag や data/kill.flag の存在を確認
- AI 通信エラー
  - OPENAI_API_KEY が設定されているか、ネットワーク接続、API rate limit を確認
- 設定検証でエラーが出る
  - python -m kabusys.validate_config で原因メッセージを確認し、.env を修正

---

貢献 / 開発時の注意
- .env は秘密情報を含むため絶対にリポジトリにコミットしないでください。
- 新しい DB カラムを追加する場合は monitoring_db.init_monitoring_db のマイグレーションパターンを踏襲してください（既存 DB への安全な追記処理）。
- AI 関連の外部呼び出しはリトライ・タイムアウト・バリデーションが組み込まれていますが、実行回数に注意してコスト管理を行ってください。

---

必要があれば、README に含める具体的な .env.example（完全版）や systemd のユニットファイル例、運用手順（起動/停止/ログローテーション/バックアップ）なども追加で作成できます。どの部分を詳しく書くか指示してください。