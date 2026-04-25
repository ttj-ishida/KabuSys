# KabuSys

日本株自動売買システムの Python コードベース。戦略のリサーチ、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、AI を用いたニュース評価などのモジュール群で構成されています。

## プロジェクト概要
- 目的: 日本株の自動売買を安全に運用するためのフレームワークを提供します（戦略計算・ポートフォリオ構築・発注管理・監視・アラート・ペーパートレード機能など）。
- 設計方針:
  - DB（DuckDB/SQLite）を利用したデータ永続化と分析。
  - 本番とペーパートレードの明確な分離（ペーパートレードは専用 DB を使用）。
  - 監視コンポーネントにより異常検知 → Kill Switch を通じて ExecutionEngine を安全停止可能。
  - OpenAI を利用したニュースの NLP 評価（必要時）。

## 主な機能一覧
- リサーチ / ファクター計算
  - モメンタム / バリュー / ボラティリティ等を DuckDB から計算（kabusys.research）。
- ポートフォリオ構築
  - 候補選定、重み付け（等配分/スコア加重）、ポジションサイズ計算（単元株丸め、リスク制約）等（kabusys.portfolio）。
- 発注・実行系
  - ExecutionEngine（発注管理、リスク管理、オーダーリポジトリ等）。ペーパートレードモードでは MockBrokerClient を使用し、専用 SQLite に記録（kabusys.execution）。
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine。kill.flag による停止やアラート送信をサポート（kabusys.monitoring）。
- AI（ニュース NLP / レジーム判定）
  - raw_news を LLM（OpenAI）で評価して銘柄別スコアを生成（kabusys.ai.news_nlp）。
  - マクロニュースと ETF MA を合成して市場レジーム判定（kabusys.ai.regime_detector）。
- ユーティリティ
  - 環境設定ウィザード（.env 作成補助）、設定検証 CLI、ログ設定ユーティリティなど。
- ツール
  - ペーパートレード検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。

## 要求環境（推奨）
- Python >= 3.10（型注釈に | を使用）
- 主要依存ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証に任意）
- 標準ライブラリ: sqlite3, logging, argparse 等

（実際の requirements.txt はプロジェクト側で用意してください）

## セットアップ手順（開発環境向け）
1. リポジトリをクローン / 取得
2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - もしくは個別に: pip install duckdb psutil openai pyyaml
4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - あるいは手動で .env をプロジェクトルートに作成
   - 自動ロード: モジュールは起動時にプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（不要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります

## 主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、Execution は MockBroker を使い PAPER_TRADING_SQLITE_PATH に記録
- DB パス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (監視用, default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用: data/paper_trading.db)
- ログ
  - LOG_LEVEL (default: INFO)
  - LOG_DIR (default: logs/)
- その他
  - OPENAI_API_KEY (AI モジュールで使用)
  - PAPER_FILL_MODE (ペーパートレード約定モード: instant|partial|never|reject)
  - MONITOR_POLL_INTERVAL (監視ループのポーリング間隔 秒、default: 60)
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

## 使い方（実行スクリプト）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録します
  - 起動時に data/stop_requested.flag が存在すると起動しません
- Monitoring 起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は常に settings.sqlite_path（本番の monitoring DB）を使用します（環境に依らず）
  - 監視ループは data/stop_requested.flag の検知で終了
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db または env PAPER_TRADING_SQLITE_PATH
- AI スコアリング（プログラムから呼出）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## ログとファイル
- ログ: logs/<app_name>.log（TimedRotatingFileHandler により日次ローテーション・30日保持）
  - setup_logging(app_name="execution"|"monitoring" など) がルートロガーを設定します
- フラグ/制御ファイル:
  - data/kill.flag : Kill Switch による ExecutionEngine 停止指示（KillSwitch が書き込み）
  - data/stop_requested.flag : run_* スクリプトが外部で停止を検出するためのフラグ
  - data/execution.pid : ExecutionEngine の PID ファイル（存在場所は Settings で可変）
- DB:
  - デフォルト DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

## 注意・運用メモ
- 設定の自動ロード:
  - config モジュールはプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動読み込みします。テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用:
  - KABUSYS_ENV=live 設定時は LINE 通知等の設定が必須に近い（validate_config が警告を出します）。
  - KILL_FLAG_CLEAR_ON_START=1 は本番で危険。デフォルト 0 を推奨。
- OpenAI 利用:
  - OPENAI_API_KEY を環境変数で設定するか、関数に明示的に api_key を渡してください。
  - API 呼び出しはリトライやフォールバック（失敗時 0.0 など）を組み込んでいますが、API 使用にはコスト・レート制限がある点に注意してください。
- ペーパートレード:
  - paper_trading モードでは本番 DB と完全分離して動作します（PAPER_TRADING_SQLITE_PATH を使用）。
- Python バージョン:
  - typing の記法等から Python 3.10 以上を想定しています。

## ディレクトリ構成（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                — ニュースセンチメント評価（OpenAI）
    - regime_detector.py         — 市場レジーム判定（MA + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 発注株数計算・集約キャップ処理
    - risk_adjustment.py         — セクター上限、レジーム乗数
  - research/
    - factor_research.py         — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py     — 将来リターン・IC・統計サマリー
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（テーブル初期化・CRUD）
    - system_monitor.py          — システム状態・データ鮮度監視
    - trade_monitor.py           — （発注ログ等の監視）※実装ファイル参照
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag 制御
    - monitoring_engine.py       — 各 Monitor を束ねる
    - alert_manager.py           — （通知管理）※実装ファイル参照
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity 設定ユーティリティ

（他にも execution/*.py、data/*.py、research の補助モジュール等があります。詳細はソースツリーを参照してください。）

## 開発・テスト時のヒント
- 単体関数群（portfolio、research 等）は副作用がなく純粋関数として設計されている箇所が多く、ユニットテストが容易です。
- OpenAI 呼び出し部分は内部で分離されており、テスト時は _call_openai_api をモックすることで外部 API への依存を切れます。
- Monitoring / Execution の起動はフラグファイル（data/stop_requested.flag / data/kill.flag）で外部制御できます。テスト環境ではこれらファイルの作成・削除で挙動を確認してください。

---

この README はコードベースの主要点をまとめたものです。実運用前に必ず python -m kabusys.validate_config で設定を検証し、.env の内容・ログ設定・DB パス等を確認してください。必要があれば README に含める具体的な requirements.txt やデプロイ手順を追加できます。