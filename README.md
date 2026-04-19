# KabuSys

日本株向けの自動売買システム（ライブラリ/実行スクリプト群）

このリポジトリは、取引ロジック・ポートフォリオ構築・監視・検証ツール・LLMを使ったニュース解析などを含む、自動売買プラットフォームのコア部分を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

- 設計方針は「本番環境と開発/ペーパートレードを明確に分離」することと「外部 API 呼び出し（例: 発注や OpenAI）は設定制御・フェイルセーフを持つ」ことです。
- モジュール群は大きく分けて:
  - 実行エンジン（ExecutionEngine 起動スクリプト）
  - 監視（Monitoring）
  - ポートフォリオ構築（選定・重み付け・株数決定）
  - リサーチ（ファクター計算・特徴量解析）
  - AI 支援（ニュース NLP、レジーム判定）
  - ユーティリティ（設定読み込み、ロギング、プロセス優先度）
  - CLI ツール（設定ウィザード、設定検証、レポート生成）
- データ永続化は主に DuckDB（分析用）と SQLite（監視・ペーパートレード用）で行います。

---

## 主な機能一覧

- 実行/発注周り（ExecutionEngine、OrderManager、RiskManager 等） — 本番 / ペーパーの分離
- 監視機能
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存確認、データ鮮度
  - TradeMonitor / RiskMonitor / MonitoringEngine: 注文滞留、ドローダウン監視、Kill Switch 判定、アラート送信
  - MonitoringDB: 監視ログ用の SQLite テーブル/インデックスの初期化と CRUD
- ポートフォリオ構築
  - 候補選定、等金額・スコア加重配分、リスクベースのポジションサイズ算出
  - セクターキャップ・レジーム乗数の適用
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC 計算、統計サマリー
- AI/LLM
  - ニュースのセンチメントスコアリング（OpenAI を使用）
  - 市場レジーム判定（ETF MA + マクロセンチメントの合成）
- CLI ツール
  - .env を対話的に作成/更新する `kabusys.config_setup`
  - 環境設定を検証する `kabusys.validate_config`
  - ペーパー取引の検証レポート生成 `kabusys.tools.paper_verification_report`

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントで `X | Y` を使用）
- SQLite（標準ライブラリ）
- 推奨インストールコマンド例（venv 推奨）:

1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）PyYAML を入れると `validate_config` で YAML の検証が有効になります:
     - pip install pyyaml

3. ディレクトリ作成（デフォルトのデータ/ログディレクトリ）
   - mkdir -p data logs

4. 環境変数設定
   - 対話式ウィザードで .env を作成する（推奨）:
     - python -m kabusys.config_setup
   - もしくは `.env` を手動作成（リポジトリ内に .env.example があれば参照）。
   - 主要な環境変数（代表）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB、デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR)
     - OPENAI_API_KEY (AI機能利用時に必要)

5. 設定検証（オプション）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

---

## 使い方（代表コマンド）

- 実行スクリプト（モジュールとして起動）
  - 監視ループ起動（SystemMonitor ポーリング）
    - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）  
      注: 1 未満の値や非数は無視され、デフォルト 60 秒にフォールバックします。
    - 監視は常に Settings.sqlite_path（本番用パス）を使用します（環境に関わらず）。
    - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します。

  - 実行エンジン起動（ExecutionEngine）
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と完全分離されます。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動をせず終了します。
    - 実行中のプロセス情報は data/execution.pid（デフォルト）に書き出されます。

- CLI ツール
  - .env ウィザード:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config
    - Strict モード: python -m kabusys.validate_config --strict
  - Paper Trading 検証レポート生成:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定: --db PATH（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI 機能（プログラム経由）
  - ニュース NLP スコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照します。
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- Kill Switch / 停止フラグ
  - ExecutionEngine を安全に停止させたい場合は data/kill.flag を書き込む（KillSwitch が評価してアクションします）。
  - KillSwitch を手動でクリアする:
    - (Python) KillSwitch.clear() を呼ぶ、またはファイルを削除: rm data/kill.flag
  - 監視・実行を即時停止させたい（run_*.py 停止ループ用）:
    - touch data/stop_requested.flag

---

## 主要な設定項目（.env の例と説明）

config_setup に示される主要キー（抜粋）:

- KABUSYS_ENV (development | paper_trading | live)
  - 実行環境。paper_trading 指定で発注はモック。
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート用）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR)
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか

注意: 環境変数は OS 環境変数 > .env.local > .env の順で上書きされます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## フォルダ・ファイル構成

リポジトリ内の主要なファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  -- 環境変数読み込み / Settings クラス
  - config_setup.py            -- .env 対話式ウィザード
  - validate_config.py         -- 設定検証 CLI
  - run_monitoring.py          -- SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           -- ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py         -- ログ設定ユーティリティ
    - process_priority.py      -- プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py         -- SQLite 監視 DB 初期化・読み書き
    - system_monitor.py
    - trade_monitor.py         -- （存在する想定の監視モジュール）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         -- （アラート送信管理）
  - execution/
    - execution_engine.py      -- ExecutionEngine（エントリポイントは run_execution）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py               -- OpenAI を使ったニュースセンチメント
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - data/                      -- 実行時に利用するファイル領域（非コミット推奨）
    - monitoring.db            -- デフォルト: SQLITE_PATH
    - paper_trading.db         -- PAPER_TRADING_SQLITE_PATH
    - kabusys.duckdb           -- DUCKDB_PATH
    - execution.pid
    - stop_requested.flag
    - kill.flag
  - logs/                      -- ログ出力先（デフォルト）

---

## ログと監視について

- setup_logging() によりコンソール（stdout）とファイル（logs/<app_name>.log）に出力されます。ログは日次ローテートされ 30 日保持されます。
- ログレベルは LOG_LEVEL 環境変数または引数で設定可能。
- SystemMonitor はプロセス生存確認やデータ鮮度チェック（DuckDB の prices_daily）を行い、MonitoringDB に記録します。

---

## 停止・安全装置

- Kill Switch:
  - RiskMonitor の結果（例: ドローダウン閾値超過）により KillSwitch が data/kill.flag を書き込み、ExecutionEngine の停止トリガーとなります。
  - 本番での自動クリアは危険なので KILL_FLAG_CLEAR_ON_START はデフォルト 0（無効）を推奨。
- stop_requested.flag:
  - run_monitoring.py / run_execution.py が監視するシンプルな停止フラグ（data/stop_requested.flag）。管理者が作成するとループが安全に終了します。

---

## 開発・テスト時の注意点

- .env は絶対に Git にコミットしないでください（config_setup でもヘッダに注意書きあり）。
- validate_config で PyYAML が未インストールだと config/*.yaml の中身検証はスキップされます（警告）。
- OpenAI を使う機能は API キーが必要です。テスト時は実際の API 呼び出しをモック（unittest.mock）することを推奨します（コード内でもテスト差し替え想定の仕掛けあり）。
- psutil による優先度変更は権限が必要な場合があります。失敗時は警告ログにフォールバックします。

---

## 追加メモ（実装上のポイント）

- Settings クラスは .env の自動読み込みを行い、必要なキーがない場合は早期に ValueError を発生させます。
- monitoring_db.init_monitoring_db は既存 DB のマイグレーション（カラム追加）を安全に行います。
- AI 呼び出しはレート制限や一時エラーに対して指数バックオフでリトライする設計になっています（429 / 5xx / タイムアウト等）。
- portfolio/ 以下の関数群は純粋関数（副作用なし）となるよう設計され、単体テストが容易です。

---

## よく使うコマンドまとめ（例）

- .env の作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に含める具体的な .env テンプレート、実行例のスクリーンショット出力例やデプロイ手順（systemd / Dockerfile / cron）を追加で作成します。どの情報を優先して追加しますか？