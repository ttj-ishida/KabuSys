KabuSys — 日本株自動売買システム
================================

概要
---
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。
主な用途は以下の通りです。

- シグナル生成・ポートフォリオ構築（portfolio）
- 発注実行エンジン（ExecutionEngine）および注文管理（execution）
- システム稼働監視とリスク監視（monitoring）
- DuckDB を用いたファクター計算・研究機能（research）
- ニュースの NLP によるセンチメント評価 / 市場レジーム判定（ai）
- ペーパートレードの検証レポート生成ツール（tools）
- 環境設定ウィザード・検証ツール（config_setup / validate_config）

本 README はソースコード（src/kabusys 以下）をベースに、セットアップ・起動手順と主な機能の使い方をまとめたものです。

主な機能一覧
---
- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - config_setup: 対話式に .env を作成・更新
  - validate_config: 起動前チェック（必須環境変数・YAML・パス等）
- 実行エンジン
  - run_execution: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBroker を使用し data/paper_trading.db に記録
  - 発注管理・リスク管理・リコンシリエーションを含む
- 監視
  - run_monitoring: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定）
  - MonitoringEngine: System / Trade / Risk の監視を統合してアラート発行・Kill Switch 評価
  - モニタリング永続化（SQLite）を提供する MonitoringDB（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構成
  - 候補選定・重み計算（等金額・スコア加重）
  - セクターキャップ適用、レジーム乗数、ポジションサイズ計算（単元株丸め・集約キャップ）
- 研究用モジュール
  - DuckDB を使ったファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（OpenAI）
  - news_nlp: raw_news を集約して LLM（gpt-4o-mini）へ送り銘柄ごとのセンチメントを ai_scores に格納
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM 評価を合成して日次レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を集計し PASS/FAIL 判定と指標を表示

セットアップ手順
---
前提
- Python 3.9+（実装の typing 機能に合わせてください）
- OS: Linux / macOS / Windows（主要機能はクロスプラットフォームだが process priority / cpu affinity は制限あり）

1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config が YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを利用してください（本リポジトリ例では同梱されていません）。

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - オプション: --env-file を指定して別パスに保存
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（主要なもの）
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY (AI モジュール使用時)
     - LOG_LEVEL, LOG_DIR
     - KILL_FLAG_CLEAR_ON_START (0/1) — production では 0 を推奨
     - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動

5. 設定検証
   - python -m kabusys.validate_config
   - 警告を致命扱いにする場合:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - run_monitoring や run_execution の起動時に必要なテーブルが自動作成されます（init_monitoring_db）。

使い方（実行・運用）
---
ログ設定
- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
- デフォルトログディレクトリ: logs/
- ログファイル: logs/<app_name>.log（日次ローテーション、30日保持）
- 環境変数 LOG_DIR / LOG_LEVEL で上書き可能

監視プロセス起動
- ポーリング監視（SystemMonitor）を起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可能（デフォルト 60）
  - 監視は Settings.sqlite_path（本番 sqlite_path）を利用（環境に依らず本番データを参照）
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します

実行エンジン起動
- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離
  - 起動時に data/stop_requested.flag が既にある場合は起動せず終了する（安全機構）
  - 実行時は data/execution.pid に PID を書き込みます
  - 停止: data/stop_requested.flag を作成、もしくは Kill Switch による data/kill.flag 作成で ExecutionEngine 停止を誘発可能

ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- 環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能
- 出力は標準出力に検証指標（稼働率・成功率・P95 等）と PASS/FAIL を表示

AI / レジーム判定（プログラム呼び出し）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡して実行（ai_scores へ書き込み）
  - api_key を None にすると環境変数 OPENAI_API_KEY を参照
- ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意点 / 運用上のヒント
- KABUSYS_ENV=live の場合は本番環境のため .env を慎重に管理すること（LINE 通知や Kill Switch 設定の確認）
- KILL_FLAG_CLEAR_ON_START=1 は本番では危険（Kill Switch が自動クリアされる）
- run_monitoring は常に Settings.sqlite_path（本番監視 DB）を使う設計になっています
- run_execution の paper_trading は paper_sqlite_path を使用し本番 DB とは分離されます
- process priority / cpu affinity は psutil による操作で権限によっては失敗する可能性があり、失敗時は警告でスキップします
- OpenAI を利用する機能は API エラーに対するリトライ・フェイルセーフが組み込まれていますが、API キーやレート制限には注意してください

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み・Settings クラス（.env 自動ロード機能含む）
- config_setup.py
  - 対話式 .env ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 起動前の設定検証 CLI（python -m kabusys.validate_config）
- run_monitoring.py
  - SystemMonitor をポーリングする起動スクリプト（MONITOR_POLL_INTERVAL）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）
- monitoring/
  - monitoring_db.py — SQLite 用永続化層（テーブル作成・CRUD）
  - monitoring_engine.py — 各 Monitor を統合する実行ループ
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度 / PIDチェック
  - trade_monitor.py — （存在する想定・監視ロジック）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — data/kill.flag の制御
  - alert_manager.py — （存在する想定・通知管理）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
    - Execution のコアロジック（EngineConfig, RiskConfig 等）
- portfolio/
  - portfolio_builder.py — 候補選定・重み
  - position_sizing.py — 発注株数計算（リスク制限・単元丸め）
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — モメンタム・ボラティリティ・バリュー等の計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — raw_news を LLM でスコアリングし ai_scores に保存
  - regime_detector.py — MA200 + マクロニュースで market_regime を算出
- tools/
  - paper_verification_report.py — ペーパートレード検証レポートを生成
- utils/
  - logging_setup.py — ルートロガー設定（stdout + 日次ローテーションファイル）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（その他、execution や monitoring 内に複数の補助モジュールが含まれます。上記は主なファイルの一覧です。）

補足（トラブルシューティング）
---
- .env が読み込まれない場合:
  - プロジェクトルート検出 (_find_project_root) は .git または pyproject.toml を基準に行います。配布後や配置によっては自動ロードがスキップされる場合があります。必要なら環境変数を明示的に設定してください。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます（主にテスト用）。
- DuckDB / SQLite 関連:
  - 初回起動時に必要なテーブルは init_monitoring_db によって作成されます
  - DuckDB のパス（DUCKDB_PATH）・SQLite のパス（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を確認してください
- OpenAI 関連:
  - API キーが未設定だと ai 関数は ValueError を出します。OPENAI_API_KEY を .env に設定するか関数の api_key 引数で渡してください
  - レート制限・ネットワーク障害に対するリトライロジックが実装されていますが、過負荷時はスコア取得に失敗することがあります

ライセンス・貢献
---
- この README ではライセンス情報は記載していません。実際のリポジトリに LICENSE を含めてください。
- 機能追加やバグ修正は Pull Request を受け付けます。ドキュメントの更新は歓迎します。

以上が主要な利用方法と構成のまとめです。実運用に移す前に必ず python -m kabusys.validate_config で設定を検証してください。質問や補足があれば教えてください。