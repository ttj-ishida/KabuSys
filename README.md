# KabuSys

日本株向けの自動売買／リサーチ基盤ライブラリ（部分実装）。  
このリポジトリは、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI ベースのニュースセンチメントなどのコンポーネント群を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチのための内部ライブラリ群です。主な設計方針は次のとおりです。

- 本番データとペーパートレーディング環境を明確に分離
- DuckDB を用いた分析処理、SQLite を用いた監視・注文ログ永続化
- OpenAI を用いたニュースセンチメント・レジーム判定の統合（APIキー必須）
- モジュールはできるだけ副作用を抑え、外部依存は明示的に管理

主な使用例:
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- .env 作成ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動 (run_execution.py)
  - Broker クライアントの切替（KABUSYS_ENV=paper_trading では MockBrokerClient を使用）
  - 注文管理、リスク管理、リコンシリエーションの組立て

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - システムリソース監視（CPU/Mem/Disk）、プロセス死活、データ鮮度チェック
  - 注文滞留・約定異常価格検出、ドローダウン監視、Kill Switch（data/kill.flag）

- Portfolio
  - 候補選定、等配分 / スコア配分、リスクベースのポジションサイズ算出
  - セクター上限適用、レジーム乗数（Bull/Neutral/Bear）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量要約

- AI（OpenAI 統合）
  - ニュースのセンチメントを LLM で評価し ai_scores に保存（news_nlp）
  - マクロニュース + ETF MA に基づく市場レジーム判定（regime_detector）

- Tools
  - ペーパートレード検証レポート生成（paper_verification_report）
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

- Utilities
  - 環境変数の自動読み込み/解析（config.py）
  - プロセス優先度 / CPU affinity 設定ユーティリティ（utils/process_priority.py）

---

## セットアップ手順

前提:
- Python 3.10 以上（| 型アノテーションを使用しているため）
- Git、pip

1. リポジトリをクローン
   - git clone <このリポジトリ>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要な Python パッケージをインストール
   主要依存（明示的に使われているもの）:
   - duckdb
   - psutil
   - openai
   - pyyaml（config ファイル検証用・必須ではない）

   例:
   - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がない場合は上記を個別にインストールしてください）

4. 環境変数の準備（.env）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 任意・設定例:
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）
     - LOG_LEVEL（DEBUG/INFO/…）
   - 自動読み込み:
     - config.py はプロジェクトルートの .env / .env.local を自動で読み込みます。
     - 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

---

## 使い方（主要スクリプト）

- 実行エンジン起動（Engine）
  - python -m kabusys.run_execution
  - 動作概要:
    - Settings に基づいて SQLite / DuckDB に接続
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient を利用
    - 実行中は data/execution.pid を作成
    - data/stop_requested.flag が存在するとループ停止

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 動作概要:
    - Process priority を "high" に設定（可能な環境で）
    - Monitoring DB（SQLite）を初期化（init_monitoring_db）
    - SystemMonitor.check_once() を周期的に呼び出す
    - ポーリング間隔は環境変数で上書き可能:
      - MONITOR_POLL_INTERVAL=<秒>（デフォルト 60 秒）
    - 停止用フラグ: data/stop_requested.flag を検出すると終了

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env ファイルを対話式で生成／更新します

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 簡易的に稼働率、注文成功率、レイテンシ等の指標を出力します

- AI 関連（プログラムから直接呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news, news_symbols を基に LLM で銘柄ごとにセンチメントを計算し ai_scores に書き込む
    - api_key は引数または環境変数 OPENAI_API_KEY で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム（bull/neutral/bear）を計算して market_regime テーブルに保存

注意:
- run_execution は起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します（安全措置）。
- run_monitoring は監視処理を行い、KillSwitch が発動した場合 data/kill.flag を書き込みます。

---

## 主要な設定項目（Settings）

- KABUSYS_ENV: development / paper_trading / live（必須ではないが適切に設定推奨）
  - paper_trading の場合、発注はモック実行（DB 分離）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒、デフォルト 60）

関連メソッドは src/kabusys/config.py を参照してください。

---

## ディレクトリ構成

（主要ファイル・サブパッケージのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — .env 読み込み / Settings 定義
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 統合）
    - regime_detector.py      — 市場レジーム判定（OpenAI 統合）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        — （未掲示だが通知管理用）
  - execution/                — Execution 関連（order_manager 等）
  - utils/
    - process_priority.py
  - data/                     — 実行時に生成されるファイル（SQLite, DuckDB, pid/flag等）

---

## ファイルベースの制御（Kill / Stop）

- data/kill.flag
  - 監視側 KillSwitch が異常検出時に書き込むフラグファイル
  - ExecutionEngine はこのフラグを読み（または監視プロセスが用いて）停止シグナルとして扱える

- data/stop_requested.flag
  - 管理者が作成することで run_monitoring/run_execution のループを止めるために使用

- data/execution.pid
  - 実行エンジンが起動時に PID を書き込む

---

## 注意事項 / 運用メモ

- OpenAI を利用する機能は API キーが必須。API 制限・エラーに対してはリトライ・フェイルセーフ実装あり。
- 本番環境（KABUSYS_ENV=live）では設定内容（LINE 通知など）を十分に確認すること。validate_config.py にて注意喚起あり。
- SQLite / DuckDB ファイルの親ディレクトリが存在しない場合、警告が出ますが起動時に自動作成されることもあります。validate_config で確認してください。
- process priority / cpu affinity の設定は psutil の権限に依存します。権限不足時はログに警告が出てスキップされます。

---

## 最後に

詳細な設計・アルゴリズム（PortfolioConstruction.md, StrategyModel.md 等）はリポジトリ内ドキュメントを参照してください。  
その他、起動時や運用に関する不明点があれば、実際のログ出力や validate_config の結果を元に確認・問い合わせを行ってください。