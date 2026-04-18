# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ + 起動スクリプト群）です。  
このリポジトリは以下を含みます：監視サービス、Execution エンジン、ポートフォリオ構築ユーティリティ、ファクター計算、AI を使ったニュース解析など。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような責務を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注を行う（本番／ペーパートレード切替対応）
- 監視（Monitoring）: システム稼働状況、データ鮮度、注文ログ、リスク（ドローダウン・ポジション上限）を監視し、アラート／Kill Switch を制御
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ算出、セクター制限、レジーム補正
- 研究・ファクター計算: Momentum / Volatility / Value 等のファクター計算、IC などの解析ユーティリティ
- AI モジュール: ニュースのセンチメントスコア算出（OpenAI）および市場レジーム判定
- CLI ツール: .env ウィザード（config_setup）、設定検証（validate_config）、Paper Trading 検証レポート生成 等

設計の主要ポイント:
- 環境変数ベースで設定を読み込み（.env 自動読み込みと対話式ウィザードあり）
- DuckDB（分析）と SQLite（監視 / 発注ログ）を併用
- ペーパートレード時は実際の発注を行わず、専用の SQLite（data/paper_trading.db）に書き込むことで本番 DB と分離
- OpenAI を使う処理は API キーが必要。API 失敗時はフェイルセーフで継続する実装が多い

---

## 主な機能一覧

- 実行エンジン起動スクリプト: src/kabusys/run_execution.py
  - KABUSYS_ENV により本番 / paper_trading を切替
  - paper_trading の場合は MockBrokerClient（data/paper_trading.db を使用）
  - PID ファイル管理、stop フラグ検知による安全停止
- 監視起動スクリプト: src/kabusys/run_monitoring.py
  - 定期ポーリングで SystemMonitor の check を実行
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視 DB は環境にかかわらず本番 sqlite_path を使用
- 設定ウィザード（.env 作成）: src/kabusys/config_setup.py
- 設定検証 CLI: src/kabusys/validate_config.py
  - .env / config/*.yaml / 必須環境変数 のチェック
- Paper Trading 検証レポート: src/kabusys/tools/paper_verification_report.py
  - 期間指定で稼働率・約定率・レイテンシ等の集計と判定を出力
- 監視関連（Monitoring）:
  - system_monitor, trade_monitor, risk_monitor, MonitoringEngine, KillSwitch, MonitoringDB（SQLite）
- ポートフォリオ: candidate 選定、等重・スコア重み、ポジションサイズ計算、セクター キャップ、レジーム乗数
- 研究（Research）:
  - ファクター算出（momentum, volatility, value）
  - 将来リターン、IC、統計サマリ等のユーティリティ
- AI:
  - news_nlp: raw_news を集約して OpenAI に投げセンチメントスコアを生成して ai_scores に保存
  - regime_detector: ETF 1321 の MA200 とマクロニュースセンチメントを合成して market_regime に書き込み

---

## 必要環境

- Python 3.10 以上（型ヒントに `X | Y` を使用）
- 推奨インストールパッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を有効にする場合）
- 依存をまとめた requirements.txt がない場合は手動でインストールしてください:
  - pip install duckdb psutil openai pyyaml

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker 挙動（instant / partial / never / reject。デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合に必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- LOG_DIR: ログディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。default: 60）。0 以下・不正値はデフォルトにフォールバック
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=自動クリア、0=しない。デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動読み込みを無効化

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil openai pyyaml
   - （requirements.txt がある場合は pip install -r requirements.txt）
4. .env を作成する（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで各値を入力するとプロジェクトルートに .env が生成されます
5. 設定を検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)
6. データディレクトリやログディレクトリが存在しない場合は自動生成されますが、権限などに注意してください

---

## 使い方（主要コマンド）

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を上書き可
  - 監視は data/stop_requested.flag の存在で終了（ファイルを作ることで外部から停止指示）
- 実行エンジンの起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録（本番 DB と分離）
  - 実行中は data/execution.pid に PID が書かれ、停止は data/stop_requested.flag / Kill Switch により行われる
- .env の初期化・編集（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - エラー／警告／情報を出力
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを明示可能（PAPER_TRADING_SQLITE_PATH 環境変数も使用可）
- AI モジュールの利用例（スクリプト内から呼ぶ）
  - DuckDB 接続を作り、関数を呼び出す:
    - import duckdb
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date=date(2026,4,10), api_key=os.environ.get("OPENAI_API_KEY"))
  - 同様に regime_detector.score_regime(conn, target_date, api_key=...)
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で指定）

注意:
- run_execution は内部で BrokerClientFactory.create(settings) を呼びます。ブローカークライアント実装が必要です（ペーパートレードでは MockBroker を使う想定）。
- run_monitoring / run_execution はそれぞれ stop フラグ（data/stop_requested.flag）をチェックします。手動で停止したい場合は該当ファイルを作成してください。

---

## 重要ファイル / データ場所

デフォルト（.env 未設定時）:

- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID / フラグ:
  - data/execution.pid
  - data/kill.flag (Kill Switch が書き込む停止フラグ)
  - data/stop_requested.flag (外部からスクリプトを停止するためのフラグ)
- ログ: logs/<app_name>.log （app_name は `execution` / `monitoring` 等）

---

## ディレクトリ構成

（プロジェクトルート: src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル作成含む）
    - system_monitor.py       — システム・データ鮮度モニタ
    - trade_monitor.py        — 注文ログ・滞留注文監視（実装あり）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の書き込みロジック
    - monitoring_engine.py    — 各モニタの統合ループ
    - alert_manager.py        — （アラート送信管理）
  - execution/
    - execution_engine.py     — Execution エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - tools/
    - paper_verification_report.py
  - data/                     — 実行時に使用するデータ / DB / フラグ（リポジトリ直下 data/）

---

## 実運用上の注意事項

- KABUSYS_ENV=live（本番）設定時は、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や Kill Switch の動作（KILL_FLAG_CLEAR_ON_START 等）を十分に確認してください。validate_config は本番用の追加チェックを行います。
- .env は絶対に Git にコミットしないでください（config_setup は README 中にその注意が埋め込まれています）。
- OpenAI 呼び出しはコストとレイテンシの影響が大きいため、API キーの管理とレート制限考慮が必要です。モジュール側でもリトライや部分失敗の保護がなされていますが、運用設計は慎重に行ってください。
- SQLite / DuckDB ファイルのバックアップやディスク容量管理、ログローテーション（logs/ は TimedRotatingFileHandler で日次・30日保持）を運用で整備してください。

---

## 開発者向けメモ

- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml がある場所）を起点に `.env` と `.env.local` を自動で読み込みます。
  - テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギング:
  - setup_logging(app_name="...") を各起動スクリプトの最初に呼んで統一的にログ出力されます。
  - デフォルトは logs/<app_name>.log に日次ローテーション（30日保持）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成・簡易マイグレーション（カラム追加）を行います。

---

必要であれば README に「サンプル .env」「起動フロー図」「詳細アーキテクチャ（クラス図）」などを追記できます。どの項目を優先して詳述しましょうか？