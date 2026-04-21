# KabuSys

日本株向けの自動売買・研究基盤ライブラリ / 実行ツール群

このリポジトリは、売買実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算・研究、ニュースNLP（LLM を使ったセンチメント評価）などを含む日本株向け自動売買システムのコードベースです。ライブラリとしての利用だけでなく、各種起動スクリプトやツールも提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数一覧（主要）
- 停止 / Kill スイッチについて
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は次のような目的で作られたコンポーネント群です。

- 実行エンジン（ExecutionEngine）：ブローカークライアントを使って注文発行・管理を行う（本番 / ペーパートレード切替あり）。
- 監視（Monitoring）：システム状態、注文ログ、リスク指標を定期チェックし、必要に応じてアラート発行や Kill Switch をトリガする。
- ポートフォリオ構築：銘柄選定、重み計算、ポジションサイズ計算、セクター上限適用など。
- 研究（Research）：DuckDB 上の価格データを用いたファクター計算 / 特徴量探索。
- AI（news_nlp / regime_detector）：OpenAI API を用いたニュースセンチメント評価や市場レジーム判定。
- ツール：ペーパートレードの検証レポート生成、設定ウィザード、設定検証 CLI など。
- ユーティリティ：ログ設定、プロセス優先度設定、DB 初期化など。

設計方針として、DB（SQLite / DuckDB）をデータ永続化に使用し、ペーパー口座は本番 DB と明確に分離しています。

---

## 主な機能一覧

- 実行/監視起動スクリプト
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- 設定支援・検証
  - python -m kabusys.config_setup   （対話式 .env ウィザード）
  - python -m kabusys.validate_config （起動前チェック）
- 監視コンポーネント
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - kill_switch による flag ファイルでの実行停止
- ポートフォリオ構築
  - 候補選定、等重／スコア重み、リスクベースのポジションサイズ算出、セクターキャップ適用
- 研究用計算
  - モメンタム / ボラティリティ / バリューファクター計算
  - 将来リターン計算・IC 計算・ファクターサマリー等
- AI モジュール
  - news_nlp.score_news: OpenAI を使ってニュースをスコアリングして ai_scores に書き込み
  - regime_detector.score_regime: ETF/ニュースを組合せて市場レジームを判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定レポートを出力

---

## セットアップ手順

1. Python インストール（推奨: 3.9+）
2. 必要パッケージのインストール（例）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で YAML チェックをしたい場合）
   - その他標準ライブラリ（sqlite3 等は標準）

   例:
   pip install duckdb psutil openai pyyaml

   （requirements.txt は本リポジトリに含まれていません。環境に合わせて必要なパッケージをインストールしてください。）

3. プロジェクトルートに .env を作成
   - 対話式ウィザードを使うのが簡単です:
     python -m kabusys.config_setup
   - ウィザードで作成される .env の例（一部）:
     JQUANTS_REFRESH_TOKEN=your_jquants_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

4. 設定検証（任意）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

5. データディレクトリの作成（必要に応じて）
   - デフォルトでは data/、logs/ を使用します。スクリプトが自動作成することもありますが、権限等が問題になる環境では事前に作成してください。

---

## 使い方

主要な起動方法とオプション例を示します。

1. 実行エンジン起動
   - 本番 / ペーパーは KABUSYS_ENV により切り替え
   - 起動:
     python -m kabusys.run_execution
   - ペーパートレード時:
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     この場合、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。

2. 監視ポーリング起動
   - 起動:
     python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数で上書き:
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     （単位: 秒、デフォルト 60 秒）

3. 設定ウィザード
   python -m kabusys.config_setup
   → .env を対話式で作成・更新します。

4. 設定検証
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict

5. ペーパートレード検証レポート
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   --db で別ファイルを指定可能:
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

6. AI モジュール（ライブラリ関数）
   - news_nlp.score_news(conn, target_date, api_key=None)
   - regime_detector.score_regime(conn, target_date, api_key=None)
   これらは DuckDB 接続（kabusys が想定するスキーマ）を渡して呼び出します。API キーは引数または環境変数 OPENAI_API_KEY で指定します。

ログ
- ログはデフォルトで stdout とファイル（logs/<app_name>.log）に出力されます。ログディレクトリは環境変数 LOG_DIR で変更可能。ログレベルは LOG_LEVEL（デフォルト INFO）。

---

## 環境変数（主要）

以下はコード中で参照・利用される主要な環境変数とデフォルト値の一覧（抜粋）です。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合に必要)
- LINE_CHANNEL_ACCESS_TOKEN (任意、アラート通知用)
- LINE_USER_ID (任意、アラート通知先)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring 用 DB（監視は環境に依らず本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — ペーパートレード専用 DB
- PAPER_FILL_MODE (デフォルト: "instant") — ペーパーブローカーの約定挙動 ("instant" | "partial" | "never" | "reject")
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR (ログ出力ディレクトリ)
- MONITOR_POLL_INTERVAL (監視ループのポーリング間隔秒、デフォルト 60)
- PID_FILE_PATH (PID / 実行識別子のパス、デフォルト data/execution.pid)
- KILL_FLAG_PATH (Kill Switch フラグパス、デフォルト data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか。0/1。デフォルト 0)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT （監視の閾値）

注意: 重要な資格情報は .env に平文で保存されます。絶対に Git へコミットしないでください（config_setup.py の案内文にも注意書きがあります）。

---

## 停止 / Kill スイッチ

- run_execution / run_monitoring は両方ともプロセス外から停止要求を受け付けるファイルフラグを参照します。
  - data/stop_requested.flag が存在すると、ポーリングループ・実行エンジンは安全に停止します（run_execution は起動時にフラグが既に立っていれば起動しません）。
  - KillSwitch（監視から呼ばれる）は data/kill.flag を作成して ExecutionEngine 停止を要求します。これは特定のリスク条件（ドローダウン超過等）で発生します。
  - kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 で許可できます（本番では 0 を推奨）。

停止方法（手動例）:
- 即時停止要求: touch data/stop_requested.flag
- Kill フラグの削除（手動クリア）: rm data/kill.flag

---

## ディレクトリ構成（抜粋）

以下は本コードベースの主なファイル・モジュール構成です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（自動 .env ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングスクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py      — 市場レジーム判定
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — IC / 将来リターン / 統計サマリ
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ初期化 + DB 永続化 API
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py        — （trade_monitor 実装はこのベースに依存）
    - alert_manager.py        — （AlertManager 実装により通知手段を提供）
  - utils/
    - __init__.py
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/, research/, ai/ などにさらに純関数群や DB 操作用コードあり

（上記はコードベースの一部ファイルを抜粋した構成です。完全なツリーはプロジェクトルートをご参照ください。）

---

## 補足 / 運用上の注意

- DB 分離:
  - 監視用 SQLite（monitoring.db）は常に settings.sqlite_path（本番設定）を使用します。
  - 実行エンジンは KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番データと分離します。
- ログ:
  - setup_logging() により stdout と logs/<app>.log に出力されます。ログローテーションは日次で 30 日分を保持します。
- OpenAI / 外部 API:
  - AI 機能を使う場合は OPENAI_API_KEY の設定が必要です。API 呼び出しはエラー時にリトライやフォールバックを行う設計ですが、API 利用料や呼び出し頻度には注意してください。
- テスト / 開発:
  - 自動 .env ロードは無効化できます: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - validate_config.py は起動前チェックに便利です。PyYAML がインストールされていない場合、YAML の内容検証はスキップされます（警告が出ます）。

---

問題発生時は、まず logs/<app_name>.log と標準出力を確認してください。設定に関する問題は python -m kabusys.validate_config で事前に検出できます。

README の内容はコードベースの現状実装に基づいています。運用やデプロイに合わせて .env やディレクトリ構成を調整してください。