# KabuSys

日本株向け自動売買システムのコードベース（抜粋）。本リポジトリはトレード実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント）等の主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主な機能は次のとおりです。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注・注文管理を行う（paper_trading / live 切替）。
- 監視（Monitoring）: システム状態、注文状況、リスク（ドローダウン・ポジション数）を定期的にチェックし、必要に応じて Kill Switch を発動。
- ポートフォリオ構築: 候補選定、ウェイト計算、ポジションサイズ決定、セクター制限、レジーム調整。
- リサーチ: DuckDB を用いたファクター／特徴量計算、将来リターンやICの算出。
- AI モジュール: ニュースの NLP（OpenAI）による銘柄別センチメント、マクロニュースを用いた市場レジーム判定。
- ユーティリティ: 設定ウィザード、設定検証、ロギング設定、プロセス優先度設定など。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local 自動読み込み（project root を検出）
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行・監視
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV に応じて paper_trading/mock ブローカー切替）
  - run_monitoring.py: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）

- データ永続化
  - DuckDB: 分析用 DB（デフォルト data/kabusys.duckdb）
  - SQLite: 監視・注文ログ等（デフォルト data/monitoring.db / paper: data/paper_trading.db）

- ポートフォリオ構成
  - 候補選定、等金額・スコア加重ウェイト、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数

- リサーチ
  - momentum / volatility / value ファクター計算
  - 将来リターン、IC、統計サマリー

- AI（OpenAI）
  - news_nlp: ニュース記事をまとめて LLM へ送り銘柄別スコアを生成・書込
  - regime_detector: ETF の MA200 とマクロニュースのセンチメントから日次レジーム判定

- 運用ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順（開発 / ローカル実行向け）

1. リポジトリをクローンしてワークディレクトリへ移動。

2. 仮想環境を作成・有効化（例: venv / pipenv / poetry）。

   例（venv + pip）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（requirements.txt があればそれを使用）。
   必要な主要パッケージ:
   - duckdb
   - psutil
   - openai  (AI 機能利用時)
   - PyYAML (config.yaml 検証機能を使う場合に任意)

   例:
   - pip install duckdb psutil openai pyyaml

4. 環境変数の準備:
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - または手動で .env を作成。必須項目:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - その他:
       - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
       - DUCKDB_PATH (default: data/kabusys.duckdb)
       - SQLITE_PATH (default: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
       - LOG_LEVEL (default: INFO)
       - OPENAI_API_KEY (AI 機能を使う場合)
       - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の動作を制御
       - KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を消すか（注意: 本番では 0 推奨）

   - .env 自動読み込み:
     - Settings モジュールはプロジェクトルートに .env / .env.local があれば自動読み込みします
     - 自動読み込みを無効にする場合:
       - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証:
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにするには --strict を付ける

6. データディレクトリの作成（必要なら）:
   - デフォルトでは data/ に DB や PID / flag を置きます。必要に応じて作成:
     - mkdir -p data logs

---

## 使い方（起動・運用）

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - 本番 / ペーパートレード切替は KABUSYS_ENV で制御
  - 起動:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録
    - 起動前に data/stop_requested.flag が存在すると起動されません
    - 実行中に stop flag を作成するとエンジンを停止します
    - ExecutionEngine の PID は data/execution.pid（Settings.pid_file_path）に書かれる

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔:
    - デフォルト 60 秒
    - 環境変数 MONITOR_POLL_INTERVAL で上書き可能（例: MONITOR_POLL_INTERVAL=30）
    - 0 以下や不正な値は無効扱いでデフォルトにフォールバック
  - 監視は Settings.sqlite_path（monitoring.db）を使用。monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します
  - 停止:
    - data/stop_requested.flag を作成すると監視ループを終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニュース NLP / レジーム判定）
  - 環境変数 OPENAI_API_KEY が必須（または関数呼び出し時に api_key を渡す）
  - news_nlp.score_news, regime_detector.score_regime を使用して DuckDB 上のテーブルに書き込みます
  - OpenAI の呼び出しはレート制限・5xx 等に対してリトライ実装あり

- ログ
  - 共通ログ設定: kabusys.utils.logging_setup.setup_logging を各スクリプトが呼び出します
  - StreamHandler（stdout） + TimedRotatingFileHandler（デフォルト logs/<app_name>.log、日次ローテート、30日保持）
  - ログディレクトリは環境変数 LOG_DIR、またはデフォルト logs/

- Kill / Stop フラグ
  - Kill Switch: data/kill.flag — KillSwitch が設置することで ExecutionEngine に停止シグナル送信
  - Stop フラグ: data/stop_requested.flag — run_execution / run_monitoring のループ停止に使用
  - PID ファイル: data/execution.pid（ExecutionEngine が使用）

---

## 主要コマンドまとめ（例）

- .env 作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行:
  - python -m kabusys.run_execution

- 監視:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- LOG_DIR — default: logs/
- OPENAI_API_KEY — AI 機能を使う場合
- PAPER_FILL_MODE — instant | partial | never | reject （paper_trading 用、default: instant）
- KILL_FLAG_CLEAR_ON_START — 0/1（default: 0）

運用フラグ:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると Settings の自動 .env 読み込みを抑制

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定読み込みロジック
- config_setup.py           — .env 作成ウィザード CLI
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

subpackages / modules:
- ai/
  - __init__.py
  - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py        — SQLite 永続化レイヤ
  - system_monitor.py       — システム状態 / データ鮮度監視
  - trade_monitor.py        — (注文監視) ※ファイル内一部抜粋
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag の書き込み
  - monitoring_engine.py    — モニタ群の統合
  - alert_manager.py        — (アラート管理) ※参照
- execution/
  - execution_engine.py     — ExecutionEngine（起動・セッション管理）
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
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
  - logging_setup.py        — 共通ログ設定
  - process_priority.py     — プロセス優先度 / CPU affinity
  - __init__.py
- tools/
  - __init__.py
  - paper_verification_report.py

補助:
- data/                    — DB, PID, flag 等（運用時に使用）
- logs/                    — ログ出力先（デフォルト）

（上記はリポジトリ内の抜粋を基にしています）

---

## 実装上の注意点・運用上のポイント

- DB 分離:
  - paper_trading モードでは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番データベースと明確に分離されます。
  - 監視（monitoring）は環境にかかわらず Settings.sqlite_path を使用する設計の箇所があります。運用時に意図した DB の指定を確認してください。

- ログ:
  - まずはログディレクトリ（デフォルト logs/）が書き込み可能であることを確認してください。作成失敗時はコンソール出力のみになります。

- Kill / Stop:
  - Kill Switch（kill.flag）は本番運用での緊急停止手段です。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアされますが、本番環境では 0 を推奨します。

- OpenAI / ネットワーク呼び出し:
  - news_nlp / regime_detector は外部 API（OpenAI）へ依存します。API キー未設定時は例外を投げるか、フォールバック動作（macro_sentiment=0 など）で続行する実装が各所にあります。
  - レート制限や一時エラーにリトライ実装がありますが、API 使用量には注意してください。

- テスト:
  - API 呼び出しや外部依存部分は patch / mock できるように設計されています。ユニットテストでは外部呼び出しをモックしてください。

---

## 参考（よく使うファイル / 関数）

- Settings（kabusys.config.Settings）
  - プロジェクト全体の設定読み出しに使います。settings = Settings() または単純に import された settings を利用可能。

- logging_setup.setup_logging(app_name="execution")
  - 各スクリプトの冒頭で呼び出して統一的にログを設定します。

- utils.process_priority.set_process_priority("high")
  - 起動スクリプトは最初にプロセス優先度を上げる処理を行います（権限不足時は警告で続行）。

---

README はここまでです。実行やデプロイに関して具体的な要件（ブローカー情報、J-Quants API の取り扱い、運用ルール等）がある場合は、運用ドキュメントに追記してください。必要ならデプロイ手順・systemd / supervisor 用の起動ユニット例も作成します。