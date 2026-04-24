# KabuSys

日本株自動売買システムのコアライブラリ（ドメインロジック・運用ユーティリティ群）

バージョン: 0.1.0

---

このリポジトリは、戦略・ポートフォリオ構築、発注エンジン、監視、研究用ユーティリティ、AI を使ったニュース解析などを含む自動売買システムの主要コンポーネントを収めています。本 README はコードベースを使い始めるための概要・セットアップ・実行方法を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 起動・使い方
- 主要環境変数
- 運用メモ（停止フラグ / PID / ログ）
- ディレクトリ構成（主要ファイル説明）

---

プロジェクト概要
- 戦略（ファクター計算、特徴量解析）、ポートフォリオ構築（候補選定、重み付け、ポジション決定）、注文発行（ExecutionEngine）、
  監視（System/Trade/Risk Monitor）、AI（ニュース NLP / レジーム判定）などを包含したモジュール群。
- データストア: DuckDB（分析用）と SQLite（監視／発注ログ用）を併用。
- 環境依存設定は .env または環境変数で管理。プロジェクトのルート（.git / pyproject.toml がある場所）から自動で .env をロードします。
- OpenAI を利用する処理（news_nlp, regime_detector）は API キーを必要とします（OPENAI_API_KEY）。

主な機能一覧
- portfolio: 候補選定、等重・スコア重み、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算
- research: ファクター計算（Momentum/Volatility/Value）、将来リターン、IC, 統計サマリー
- execution: ExecutionEngine（発注処理）、Broker クライアントファクトリ（paper/live 切替）
- monitoring: System/Trade/Risk モニタ、KillSwitch（停止フラグ生成）、Monitoring DB（永続化）
- ai: ニュース NLP（OpenAI で銘柄センチメント算出）、市場レジーム判定
- tools: Paper Trading の検証レポート生成スクリプト等
- CLI ユーティリティ:
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env と config/*.yaml の事前検証

セットアップ手順（ローカル開発向け）
1. Python 環境（推奨: 3.10+）を用意
2. 依存ライブラリをインストール（例）
   - 必要パッケージ（抜粋）: duckdb, psutil, openai, PyYAML（任意）
   - 例: pip install duckdb psutil openai PyYAML
   - 実運用では requirements.txt / poetry 等で管理してください
3. プロジェクトルートに移動（.git または pyproject.toml が存在するディレクトリ）
4. .env を作成する
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を手動作成
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証（必須環境変数や YAML をチェック）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

主要環境変数（代表）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — 監視 DB デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（KABUSYS_ENV=paper_trading 時に使用）
  - PID_FILE_PATH — Execution の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch の flag（デフォルト: data/kill.flag）
- ログ / 実行
  - LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
  - LOG_DIR — ログ保存先（デフォルト: logs/）
- Paper Trading / AI
  - PAPER_FILL_MODE — "instant" | "partial" | "never" | "reject"（デフォルト: instant）
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- 自動ロード制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env の自動読み込みを無効化

起動・使い方（主要スクリプト）
- ExecutionEngine（発注エンジン）起動
  - usage:
    python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、paper_db（data/paper_trading.db 等）に分離して記録します。
    - スレッドで ExecutionEngine を起動。data/stop_requested.flag が存在すると起動/実行中に停止します。
    - 実行時に PID を data/execution.pid に書きます（設定により変更可）。
- Monitoring 起動（常駐監視）
  - usage:
    python -m kabusys.run_monitoring
  - 動作:
    - SystemMonitor をポーリングして監視ログを SQLite に永続化します。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本来の sqlite_path（SQLITE_PATH）を使用します（監視 DB は本番を参照）。
    - data/stop_requested.flag が検知されるとループを終了します。
- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話形式で .env を作成・更新します
- 設定検証
  - python -m kabusys.validate_config
  - .env の必須項目や config/*.yaml の存在/パースをチェック
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB を指定可能
- AI バッチ処理
  - kabusys.ai.score_news（関数呼び出し / スクリプト化は自由）
  - OpenAI API を呼ぶ処理のため OPENAI_API_KEY が必要
  - 429 / 一時的エラーは内部でリトライ処理あり

運用メモ（フラグ・PID・ログ）
- stop/kill フラグ
  - data/stop_requested.flag: run_execution / run_monitoring の外部停止用フラグ（存在するとプロセスが停止）
  - data/kill.flag: KillSwitch によって書き込まれる停止トリガ（ExecutionEngine への停止シグナルとして利用）
  - KillSwitch はリスク条件（ドローダウン閾値・ポジション上限等）を満たした場合に理由付きで kill.flag を書き込みます
- PID ファイル
  - Execution は設定された PID_FILE_PATH（デフォルト data/execution.pid）に PID を書きます
- ログ
  - 共通ロギングユーティリティ: kabusys.utils.logging_setup.setup_logging
  - 出力: stdout（StreamHandler）および 日次ローテートされたログファイル logs/<app_name>.log
  - ログレベルは LOG_LEVEL / 引数で制御

注意事項 / 実装上のポイント
- 設定の自動ロード:
  - プロジェクトルートに .env / .env.local があれば自動で読み込まれます（OS 環境変数が優先）。
  - テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB の分離:
  - 本番発注ログとペーパートレードログは分離（paper_trading の場合は paper_sqlite_path を使用）。
  - 監視は常に SQLITE_PATH を参照（本番を監視するため）。
- OpenAI
  - news_nlp と regime_detector は gpt-4o-mini を利用する設計（response_format に JSON mode を使用）。
  - API キー未設定時は例外・フォールバック処理があります。AI 関連処理はフェールセーフでスキップする設計になっています。

ディレクトリ構成（主要ファイル説明）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定取得ユーティリティ（Settings クラス）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - risk_adjustment.py — セクターキャップ / レジーム乗数
    - position_sizing.py — 発注株数決定ロジック
    - __init__.py
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン / IC / 統計
    - __init__.py
  - ai/
    - news_nlp.py — ニュースセンチメント解析（OpenAI 呼び出し）
    - regime_detector.py — 市場レジーム判定（ETF + マクロ NPL）
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化 & 永続化 API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 発注ログ監視（滞留注文や価格異常等。※ファイルでは一部省略）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（flag 書き込み）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — 通知管理（LINE 等への通知。※コードベース参照）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - monitoring/*, execution/*, data/*, research/* など（各サブシステムの実装）

付録: よく使うコマンド例
- .env 作成:
  python -m kabusys.config_setup
- 設定チェック:
  python -m kabusys.validate_config
- Execution 起動（バックグラウンド等は運用側で管理）:
  python -m kabusys.run_execution
- Monitoring 起動:
  python -m kabusys.run_monitoring
- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- （AI 処理を手動で呼ぶ場合は）Python REPL で関数を呼ぶ:
  from kabusys.ai.news_nlp import score_news
  score_news(duckdb_conn, date(2026,4,1), api_key="...")

最後に
- 本 README はコードに含まれる設計コメント・ドキュメントを元に要点を抜粋したものです。
- 実運用前に必ず python -m kabusys.validate_config で設定を検証し、テスト環境（paper_trading）で動作確認を行ってください。
- セキュリティ: .env をリポジトリにコミットしないでください。

問題や追加のドキュメント化が必要な箇所があれば、どの部分を深掘りしたいか教えてください。