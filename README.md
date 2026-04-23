# KabuSys

日本株自動売買システムのサンプル実装。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、Paper Trading 検証レポート、LLM を使ったニュースセンチメント評価などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた自動売買基盤の簡易実装です。

- DuckDB / SQLite を用いたデータ分析・永続化
- ファクター計算（モメンタム・バリュー・ボラティリティ）
- 研究用ユーティリティ（将来リターン計算、IC 等）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ算出）
- ExecutionEngine（ブローカークライアント経由での発注処理）
  - `paper_trading` 環境では MockBrokerClient を使用し、本番 DB と分離された `data/paper_trading.db` を使用
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ログ・プロセス優先度ユーティリティ
- AI モジュール（OpenAI を用いたニュースセンチメント / レジーム検出）
- 各種 CLI ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

設計上の注意点:
- 環境変数／.env による設定管理
- 本番（live）環境時は特に注意が必要（Kill Switch / LINE 通知 等）
- AI 機能は OpenAI API キーが必要（無ければスキップする設計の箇所あり）

---

## 機能一覧

主なモジュールと役割：

- kabusys.config, config_setup.py, validate_config.py
  - 環境変数読み込み、自動 .env ロード、対話式ウィザード、設定検証
- kabusys.utils
  - logging_setup: 統一ログ設定（コンソール + 日次ローテーション）
  - process_priority: プロセス優先度 / CPU affinity 設定
- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー計算
  - feature_exploration: 将来リターン・IC・統計サマリー
- kabusys.portfolio
  - portfolio_builder: 候補選定・重み（等金額 / スコア加重）
  - position_sizing: 発注株数計算（risk_based / equal / score）
  - risk_adjustment: セクター上限、レジーム乗数
- kabusys.execution
  - ExecutionEngine, BrokerClientFactory, OrderManager, RiskManager 等（発注ロジック）
- kabusys.monitoring
  - monitoring_db: SQLite ベースの監視データ永続化
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - run_monitoring.py: 監視ポーリングループの起動
- kabusys.tools
  - paper_verification_report.py: Paper Trading 検証レポート生成
- kabusys.ai
  - news_nlp: ニュースを LLM でスコアリングして ai_scores に格納
  - regime_detector: MA + マクロセンチメントで市場レジームを判定

---

## 必要条件（依存パッケージ）

主に以下が必要です（プロジェクトで使っているものの一部）:

- Python 3.9+
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML（設定ファイル検証を行う場合、任意）
- その他標準ライブラリ

インストール例（仮）:
pip install duckdb psutil openai pyyaml

（実際はプロジェクトの requirements.txt / pyproject.toml に合わせてください）

---

## セットアップ手順

1. リポジトリをクローン／展開する。
2. Python 環境を準備する（venv など）。
3. 必要な依存パッケージをインストールする。
4. .env を作成する（対話式ウィザード推奨）:

   python -m kabusys.config_setup

   ウィザードでは以下などを設定します（必須）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   環境設定の主要キー:
   - KABUSYS_ENV: development | paper_trading | live
   - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
   - LOG_LEVEL
   - LINE_CHANNEL_ACCESS_TOKEN（任意）
   - OPENAI_API_KEY（AI 機能を使う場合）

5. 設定検証:

   python -m kabusys.validate_config
   # --strict を付けると警告もエラー扱いになる
   python -m kabusys.validate_config --strict

6. データディレクトリ、ログディレクトリの作成は自動的に行われますが、アクセス権等を確認してください。

---

## 使い方（主要スクリプト）

- 実行エンジン（ExecutionEngine）起動:

  python -m kabusys.run_execution

  動作:
  - Settings に基づいて SQLite / DuckDB に接続
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（デフォルト: data/paper_trading.db）へ記録
  - 起動時に data/stop_requested.flag が存在すると起動しない
  - 実行中に stop flag が作成されると安全に停止します
  - PID ファイルを data/execution.pid に書きます（設定により変更可）

- 監視ループ起動:

  python -m kabusys.run_monitoring

  動作:
  - SystemMonitor 等を初期化してポーリング実行
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 監視ログは sqlite_path（Settings.sqlite_path）に記録されます（監視用 DB は常に本番 sqlite_path を使用）

- .env ウィザード（初期設定）:

  python -m kabusys.config_setup

- 設定検証:

  python -m kabusys.validate_config

- Paper Trading 検証レポート生成:

  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（プログラム呼び出し）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  いずれも OpenAI API キー（OPENAI_API_KEY または引数）が必要です。

---

## 重要な挙動・運用メモ

- 環境切替:
  - KABUSYS_ENV により挙動が変わります:
    - development: 開発用（発注しない等の差分あり）
    - paper_trading: 発注はモック／paper DB に保存（本番 DB と分離）
    - live: 本番（実際に発注）
  - live 設定時は LINE 通知などの設定漏れがないか validate_config で確認してください。

- Kill Switch:
  - kabusys.monitoring.kill_switch が条件を満たすと `data/kill.flag` に理由を記したファイルを書き込み、ExecutionEngine 側で検出して停止する仕組みです。
  - 本番では `KILL_FLAG_CLEAR_ON_START=0` を推奨（誤って自動消去されると危険）。

- DB 分離:
  - 監視 DB（monitoring.db）と Paper Trading DB（paper_trading.db）は明確に分離されています。
  - DuckDB は分析向け（prices_daily / raw_financials / raw_news 等）を想定。

- ロギング:
  - 共通の setup_logging を使い、stdout と日次ローテートファイル（logs/<app_name>.log）に出力します。
  - LOG_DIR 環境変数でログ保存先を変更可能。

- プロセス優先度:
  - run_* スクリプトは起動時に set_process_priority("high") を呼び、優先度を可能な範囲で上げようとします。権限不足時は警告のみ出します。

- MONITOR_POLL_INTERVAL:
  - 監視ループの間隔を秒で上書きできます（0 以下や不正な値は無視されデフォルト 60 秒にフォールバック）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

modules:
- ai/
  - news_nlp.py
  - regime_detector.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- execution/  (発注ロジック関連)
  - (BrokerClientFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler, ...)
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

プロジェクトルート（想定）:
- .env (.env.local)
- data/            # DB, flag, pid 等（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid）
- logs/            # ログファイル
- config/          # YAML 設定テンプレート等
- src/             # ソースコード（上記）

---

## 例: 最低限の起動フロー（開発ローカル）

1. 仮想環境作成・依存インストール
2. python -m kabusys.config_setup で .env を作成（KABUSYS_ENV=development）
3. python -m kabusys.validate_config で検証
4. python -m kabusys.run_monitoring を別ターミナルで起動（監視）
5. python -m kabusys.run_execution を別ターミナルで起動（Engine）
6. Paper Trading レポート:
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## よくある質問 / トラブルシュート

- Q: .env を自動読み込みしないようにするには？
  - A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します（テスト時に便利）。

- Q: OpenAI が無い・キーが無いときは？
  - A: AI 関連機能は API キーが無い場合は例外を投げる部位と、失敗時にフェイルセーフで 0 にフォールバックする箇所があります。AI を使う場合は OPENAI_API_KEY を設定してください。

- Q: ログファイルが作成されない
  - A: 権限や LOG_DIR 設定を確認してください。ディレクトリ作成に失敗するとコンソール出力のみになります（警告が表示されます）。

---

README はこのプロジェクトの主要ポイントをまとめたものです。細部の使用方法や内部の実装方針は各モジュールのドキュメント（ファイル内 docstring）を参照してください。必要であれば、起動例や .env.example のテンプレート、デプロイ手順（systemd / Supervisor 例）などの追加ドキュメントを作成します。