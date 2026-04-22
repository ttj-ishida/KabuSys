# KabuSys

日本株自動売買システムのコアライブラリ群（ミニマル版）。  
このリポジトリには、設定・監視・発注・ポートフォリオ構築・リサーチ・AI（ニュースNLP／レジーム判定）など、システムの主要コンポーネントの実装が含まれます。

注意: README はリポジトリの一部コードから生成しています。運用前に必ず設定ウィザード (`config_setup`) → 検証 (`validate_config`) を実行してください。

---

プロジェクトの主な特徴、セットアップ手順、使い方、ディレクトリ構成を以下にまとめます。

プロジェクト概要
- 日本株自動売買システムのコア機能をモジュール化したライブラリ群。
- 実行スクリプト: 実行エンジン（ExecutionEngine）や監視ループ（Monitoring）を起動するためのエントリポイントを含む。
- 監視・ログ・DB保存（SQLite / DuckDB）・フェイルセーフ（Kill Switch）・ペーパートレードの分離等の運用機能を実装。
- AI 関連: ニュース記事のセンチメントを LLM（OpenAI）で評価し ai_scores に格納、マクロセンチメントと価格を合成して市場レジーム判定を行うモジュールを提供。

機能一覧
- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）／対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行・監視
  - run_execution: ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）
  - 停止制御: data/stop_requested.flag によるデーモン停止、KillSwitch による data/kill.flag 書き込みで発注エンジン停止
- 監視（monitoring）
  - system_monitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度チェック
  - trade_monitor: 発注・約定履歴や滞留注文の検出（コード内で参照）
  - risk_monitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ記録
  - monitoring_db: SQLite ベースの永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - monitoring_engine: 各 Monitor をまとめてポーリング・アラート送信
- 発注周り（execution）: Broker クライアントのファクトリ、OrderManager、ExecutionEngine、RiskManager 等（本 README では参照のみ）
- ポートフォリオ構築（pure functions）
  - 候補選定、重み計算、セクターキャップ適用、ポジションサイズ計算（単元株丸め／aggregate cap 対応）
- リサーチ
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - feature_exploration: 将来リターン計算、IC（Spearman ランク相関）、統計サマリ
- AI（OpenAI 依存）
  - news_nlp: ニュース記事を LLM に投げて銘柄別センチメントを取得・ai_scores に格納
  - regime_detector: ETF（1321）MA200 乖離とマクロ記事の LLM センチメントを合成して市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB を集計し PASS/FAIL レポートを生成

セットアップ手順（ローカル開発向け）
1. リポジトリをチェックアウト
   - 例: git clone ... && cd <repo>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある想定（このコードベースでは外部パッケージを利用しています）
   - 例:
     - pip install duckdb psutil openai
     - 任意: pip install pyyaml  （validate_config は PyYAML があると config/*.yaml を検証します）

   ※ 実際の requirements.txt が無い場合は、上記主要パッケージを個別にインストールしてください。

4. 環境変数設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定が必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を設定（news_nlp / regime_detector で参照）
   - 主要な環境変数（デフォルト値あり）
     - KABUSYS_ENV: development / paper_trading / live（default: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時の専用 DB）
     - LOG_LEVEL, LOG_DIR
     - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の約定モード）

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備（必要に応じて）
   - data/ ディレクトリと logs/ ディレクトリは自動作成されますが、権限の確認を行ってください。

基本的な使い方（実行例）
- 実行エンジン（ExecutionEngine）を起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV による:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - python -m kabusys.run_execution
  - run_execution は起動時にプロセス優先度を high に設定し、paper_trading の場合は専用 DB（PAPER_TRADING_SQLITE_PATH）と MockBroker を使用します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視ループは data/stop_requested.flag の存在を検出すると終了します。
  - Monitoring は Settings にかかわらず本番 sqlite_path を使って監視ログを保存します。

- Kill Switch / 手動停止
  - KillSwitch は設定された flag_path（デフォルト: data/kill.flag）に理由テキストを書き込み、ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine 側は flag の存在を確認して安全に停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI モジュール（OpenAI を使用）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニューススコアを計算・ai_scores に書き込みます。
    - OPENAI_API_KEY を環境変数で設定するか、api_key 引数にキーを渡します。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 とマクロ記事の LLM スコアを合成して market_regime テーブルへ書き込みます。

ログについて
- ログは共通の logging_setup を通じて設定されます。
  - 標準出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力。
  - 環境変数 LOG_DIR / LOG_LEVEL で上書き可能。
  - デフォルトでログディレクトリは logs/、保管は 30 日分。

運用上の注意
- paper_trading は本番 DB と完全に分離するよう意図されています（PAPER_TRADING_SQLITE_PATH を使用）。
- 環境変数の自動ロードはプロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を読み込みます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- OpenAI など外部 API のエラーはフェイルセーフ（リトライやフォールバック）を多用し、例外が上位に波及しない設計がなされていますが、API キーやレート制限に注意してください。
- run_monitoring は Monitoring 用 DB に接続します（監視ログ）。run_execution は起動環境に応じた SQLite DB を使用します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（Settings クラス）
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・単元丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル初期化・操作）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （発注/約定監視、実装あり）
    - risk_monitor.py — ドローダウン・ポジション監視
    - kill_switch.py — kill.flag 書込ユーティリティ
    - alert_manager.py — アラート送信（実装参照）
    - monitoring_engine.py — Monitor を束ねるエンジン
  - execution/  (発注関連コンポーネント、Engine 等)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + MA200）
    - __init__.py
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - monitoring/ (上で列挙)
  - data/ (ランタイム生成想定)
  - logs/ (ランタイム生成想定)

主要 CLI / 実行コマンドまとめ
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

補足（実装上の注意点）
- Settings クラスはプロパティベースで環境変数をラップしています。必須キーが未設定だと ValueError を投げます。
- monitoring_db.init_monitoring_db はテーブルの作成と簡易マイグレーション（カラム追加）を行います。既存 DB に対して冪等に動作する設計です。
- AI 関連の OpenAI 呼び出しはリトライやレスポンス検証（JSON モード）を実装しています。API 仕様変化に備えて呼び出し抽象化が行われています（テスト時の差し替えが可能）。
- 実際の運用ではログレベル / 通知先（LINE トークンなど）の設定や、Broker クライアントの実装確認が必須です。

問題が発生した場合
- まず python -m kabusys.validate_config を実行し、設定・ファイル配置を確認してください。
- ログは logs/<app>.log に出力されるため、該当ログを確認してください。
- AI 関連で JSON 解析エラーが発生した場合は、OpenAI のレスポンス制御（model / response_format）や API レートを見直してください。

以上がこのコードベースの README.md 内容です。必要であれば運用用の systemd ユニットや Dockerfile、requirements.txt などの追加ドキュメントも作成します。どの部分を優先して整備しましょうか？