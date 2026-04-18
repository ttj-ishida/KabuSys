# KabuSys

日本株向け自動売買システムの一部実装（ライブラリ / 実行スクリプト /監視・分析ツール群）。

本リポジトリにはトレーディング実行エンジン、監視エンジン、ポートフォリオ構築・ポジションサイジング、ファクター計算、LLM を使ったニュースセンチメント評価などのモジュールが含まれます。

---

## プロジェクト概要

KabuSys は以下の目的で設計されたコンポーネント群です。

- 株式売買の発注ロジック（ExecutionEngine、OrderManager、RiskManager 等）
- システム稼働状況と注文状態の監視（MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor）
- ポートフォリオ構築・ウェイト計算・ポジションサイジング（portfolio/*）
- 研究用ファクター計算・特徴量解析（research/* — DuckDB を利用）
- ニュースを LLM (OpenAI) で評価して AI スコアを生成する機能（ai/*）
- 環境設定ウィザード・設定検証ツール（config_setup.py、validate_config.py）
- ペーパートレードの検証レポート生成ツール（tools/paper_verification_report.py）

設計方針の一部：
- DuckDB と SQLite を使い、分析用データと監視/発注ログを分離
- 環境変数ベースの設定（.env）を採用。対話式ウィザードで初期化可能
- 本番とペーパートレードは DB を分離（PAPER_TRADING_SQLITE_PATH）
- LLM 呼び出しはリトライ・バリデーション・フェイルセーフを実装

---

## 主な機能一覧

- Execution
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - 注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager）
  - ExecutionEngine による取引セッション実行（PID ファイル管理、停止フラグ対応）
  - Paper Trading 用モックブローカー対応（KABUSYS_ENV=paper_trading）

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス起動確認、データ鮮度チェック
  - TradeMonitor：発注ログのチェック（滞留注文、約定異常など）
  - RiskMonitor：ドローダウンやポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止させる
  - MonitoringEngine：上記をまとめて定期ポーリング

- Research & Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
  - 候補選定・重み付け（等金額 / スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）、単元株丸め、aggregate cap

- AI
  - ニュース記事の銘柄別センチメントスコア化（OpenAI gpt-4o-mini を想定）
  - 市場レジーム判定（ETF の MA200 とマクロニュースの LLM スコアを合成）

- ユーティリティ
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - ロギング設定ユーティリティ（kabusys.utils.logging_setup）
  - プロセス優先度設定ユーティリティ（kabusys.utils.process_priority）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発 / 起動までの手順）

※ 実際の requirements.txt はリポジトリに無い可能性があります。以下は本コードベースで import されている主な外部依存です。

想定 Python バージョン: 3.9+

推奨パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML（config 検証でオプション）
- （標準ライブラリ: sqlite3, logging 等）

インストール例:
1. 仮想環境の作成（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai PyYAML

3. .env の作成（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
     - 対話に従い JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD などを設定してください。
     - KABUSYS_ENV を development / paper_trading / live のいずれかで設定します。

4. 設定検証:
   - python -m kabusys.validate_config
   - 必要であれば --strict を付けて警告もエラー扱いにすることができます。

5. データディレクトリの準備:
   - デフォルトで使用されるパス:
     - DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH で変更可)
     - SQLite (監視): data/monitoring.db (環境変数 SQLITE_PATH)
     - Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
   - 起動時に自動作成される場合が多いですが、必要に応じてディレクトリを作成してください:
     - mkdir -p data logs

注意:
- 自動で .env をロードする仕組みが有効（デフォルト）。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨（Kill Switch が誤ってクリアされないようにするため）。

---

## 使い方（主要スクリプト・コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 監視ループを起動（SystemMonitor 単体ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  - 監視スクリプトはプロセス優先度を "high" に設定し、monitoring DB（settings.sqlite_path）へ書き込みます
  - 停止するにはプロジェクトルート以下の data/stop_requested.flag を作成します（run_monitoring はこれを検知して終了します）

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード DB（data/paper_trading.db）を使用します
  - 起動中は data/execution.pid に PID を書き込みます
  - 停止するには data/stop_requested.flag を作成、または KillSwitch により data/kill.flag が書かれた場合 Engine は停止します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先される）
  - 出力: 標準出力に期間の各種指標（稼働率・成功率・レイテンシ等）を表示し PASS/FAIL を判定

- AI（ニューススコア / レジーム判定）
  - コード内 API（kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）を使って呼び出します
  - これらは直接の CLI エントリポイントではなく、Engine 内やスクリプトで呼ぶ想定です
  - OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか、関数引数で渡します

- ログ設定
  - 各起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出しているため、LOG_LEVEL / LOG_DIR を環境変数で調整できます
  - 既定では logs/<app_name>.log に日次ローテートで出力されます

---

## 主要設定環境変数（抜粋）

必須（少なくとも設定しておくこと）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用に関する重要変数
- KABUSYS_ENV — 実行環境: development / paper_trading / live
  - paper_trading の場合は発注をモック（DB 分離）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY — OpenAI API キー（ai.* を使う場合）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant | partial | never | reject
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（1 または 0。production は 0 推奨）

その他: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを抑制します（テスト用）。

---

## 停止 / Kill スイッチについて

- 停止フラグ（run_monitoring / run_execution が監視）
  - data/stop_requested.flag：これを作ると起動中の monitoring/execution スクリプトが終了処理を行って停止します（外部プロセスからの停止要求に利用）
- Kill Switch（自動判定）
  - 条件により KillSwitch が data/kill.flag を書くと、ExecutionEngine 起動時や monitoring が検出してエンジンを停止させる仕組みがあります
  - 設定により起動時に kill.flag を自動でクリアすることもできますが、本番では無効（0）が推奨です

---

## ディレクトリ構成

（リポジトリ内の主要ファイルを抜粋した構成）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（schema + helper）
    - system_monitor.py      — システム状態監視
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - (その他: trade_monitor.py, alert_manager.py 等)
  - execution/
    - execution_engine.py    — ExecutionEngine（セッション実行）
    - broker_factory.py      — BrokerClientFactory（本番 / mock 切替）
    - order_manager.py
    - order_repository.py
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
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
    - __init__.py

- data/    — 実行時に使用する DB / フラグファイル を置く想定（例: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag）
- logs/    — ログファイル出力先（デフォルト）

---

## 開発者向けメモ / 注意点

- DuckDB と SQLite を併用しているため、分析クエリ（research/*）は DuckDB 接続を期待します。一方、監視・注文履歴は SQLite（monitoring_db.py）に保存します。
- LLM 呼び出し（OpenAI）は外部 API 利用のため API キーが必要です。失敗時はフェイルセーフ（0.0 など）で動作継続する設計になっていますが、実行結果は慎重に確認してください。
- 本番環境では KABUSYS_ENV=live の設定と、LINE 通知等のアラート設定を必ず確認してください（validate_config で注意喚起されます）。
- ログディレクトリ作成に失敗した場合、ファイル出力はスキップされコンソールのみになります（setup_logging の挙動）。

---

この README はコードベースの主要なエントリポイントと設計意図をまとめたものです。実運用やデプロイ時は環境固有の設定（DB バックアップ、監視、プロセス管理、認証情報の安全な保管等）を別途整備してください。必要であれば、さらに詳しい起動手順や systemd ユニット例、サンプル .env.example を作成できます。