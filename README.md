# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買／研究／監視ツール群を含むプロジェクトです。README はプロジェクト全体の概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群から構成されています。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行うコンポーネント
- 監視（Monitoring）: システム稼働状況、注文滞留、ドローダウン等の監視とアラート/Kill Switch
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、株数決定、セクター制約などの純粋関数群
- 研究（Research）: ファクター計算・将来リターン・IC 等の解析ツール（DuckDB ベース）
- AI モジュール: ニュース NLP（OpenAI）を使ったセンチメント集計や市場レジーム判定
- ツール群: Paper Trading の検証レポート生成などの CLI スクリプト
- 設定管理: .env のウィザード・検証ツール

設計方針として、本番リスクを考慮した安全機構（paper_trading モードの分離、Kill Switch、フェイルセーフ）や、ルックアヘッドバイアスを避ける実装（日時参照の制限）などが盛り込まれています。

---

## 主な機能一覧

- run_execution: ExecutionEngine 起動（本番 / ペーパートレード切替）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db を利用
- run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整可）
  - 監視ログは SQLite（monitoring.db）に永続化
- MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor をまとめたポーリングエンジン
- Kill Switch: 指定条件（ドローダウンやポジション上限）で data/kill.flag を書き ExecutionEngine を停止
- Portfolio: 候補選定、等重/スコア加重、リスク調整、株数決定（単元丸め・利用限度考慮）
- Research: DuckDB を用いたファクター計算（Momentum / Volatility / Value）・IC/サマリー
- AI:
  - news_nlp: OpenAI を使った銘柄別ニュースセンチメント算出（ai_scores 書込）
  - regime_detector: ETF の MA + マクロニュースで日次レジーム判定
- tools:
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート生成
- 設定ヘルパー:
  - config_setup: .env の対話式ウィザード
  - validate_config: .env と config/*.yaml を起動前に検証

---

## セットアップ手順

1. リポジトリをクローン／配置
   - この README はパッケージルート（src 配下が kabusys パッケージになる構成）を想定しています。

2. Python 環境を準備（推奨: venv）
   - Python 3.10+ を想定（DuckDB, psutil, openai 等を使用）

3. 依存パッケージのインストール
   - requirements.txt が無い場合は手動でインストールしてください。主要なライブラリ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で推奨だが必須ではない）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```

4. .env を作成
   - 対話式ウィザードで生成:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（ウィザード / validate_config でチェックされます）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主な環境変数（デフォルト値を持つもの含む）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 専用 SQLite（data/paper_trading.db）
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能利用時に必要
     - PAPER_FILL_MODE — ペーパートレードの約定挙動 (instant | partial | never | reject)
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)

5. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. data ディレクトリ等の初期作成（多くは実行時に自動作成されますが確認推奨）
   - 例: `mkdir -p data`

注意: .env は機密情報を含むため絶対に Git にコミットしないでください。

---

## 使い方

基本的にパッケージをモジュールとして実行します（プロジェクトルートで実行）。

- 実行エンジン起動
  - 本番（KABUSYS_ENV=live）/ 開発（development）/ ペーパートレード（paper_trading）に応じて挙動が変わります。
  - ペーパートレードでは MockBrokerClient を利用し、データベースは paper_trading 用に分離されます。
  ```
  # ペーパートレードで起動例
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  実行時の特徴:
  - 起動直後にプロセス優先度を "high" に変更（set_process_priority）
  - 停止は data/stop_requested.flag（内部的に実行スレッドを停止）や data/kill.flag（Kill Switch）で制御
  - 実行中は pid ファイル（デフォルト data/execution.pid）を生成

- 監視サービス起動
  - SystemMonitor のポーリングループを開始します。デフォルトのポーリング間隔は 60 秒。
  - MONITOR_POLL_INTERVAL 環境変数で上書き可能（秒単位、1 以上を指定）
  ```
  # デフォルト 60 秒
  python -m kabusys.run_monitoring

  # 30 秒間隔で実行
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  監視の特徴:
  - 監視用 DB（SQLite）の初期化は常に本番 sqlite_path を使って行われます（監視は環境に依存しない）
  - SystemMonitor はデータ鮮度（DuckDB 内の最終株価日付）や PID の存在チェック等を行う
  - MonitoringEngine を利用する場合、Kill Switch 評価や AlertManager 経由で通知可能

- Kill Switch（手動）：ExecutionEngine を停止するには kill.flag を立てます
  - 既定のパスは Settings.kill_flag_path（デフォルト: data/kill.flag）
  - KillSwitch は特定のリスク条件が満たされたとき監視側が書き込む仕組みも備えます

- Paper Trading 検証レポート生成（ツール）
  ```
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report

  # 期間指定と DB 指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI 機能
  - news_nlp.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定
    - 前日 15:00 JST ～ 当日 08:30 JST の記事を対象に銘柄別スコアを ai_scores テーブルへ書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA とマクロニュースを組み合わせて market_regime テーブルへ書き込み

---

## 動作上の注意点 / 安全機構

- ペーパートレードと本番データベースは分離されています（paper_trading モードで paper_sqlite_path を使用）。
- 監視ロジックは本番 sqlite_path を使用して監査ログを常に一箇所に残します（監視は環境によらない設計）。
- Kill Switch により重大なリスク（大きなドローダウン、ポジション上限超過）で自動的に停止できます。起動時に kill.flag を自動消去するかは KILL_FLAG_CLEAR_ON_START で制御できます（本番は 0 推奨）。
- OpenAI を用いるモジュールは API エラーや 5xx に対して指数バックオフ・フォールバックを行い、失敗時は安全なデフォルト（例: macro_sentiment = 0.0）で継続します。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソースは src/kabusys 以下にあります。代表的なファイルを列挙します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層 + MonitoringDB ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （未示; アラート送信管理）
  - execution/               — 発注/注文管理関連（OrderManager 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （上記はプロジェクトルートの config ディレクトリに配置される想定。generate 用スクリプトあり）

- data/
  - monitoring.db (デフォルト SQLite)
  - paper_trading.db (ペーパートレード用 SQLite)
  - kabusys.duckdb (DuckDB ファイル)
  - execution.pid, stop_requested.flag, kill.flag 等の運用用ファイル

---

## よく使うコマンド一覧

- .env 作成（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution 起動
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Monitoring 起動（ポーリング）
  ```
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

---

## 開発・拡張に関するメモ

- DuckDB を用いた研究／ファクター計算は副作用を持たない（読み取り専用）設計で、実際の発注ロジックから切り離されています。
- AI 関連の OpenAI 呼び出しは外部 API 依存です。テスト時は _call_openai_api をモック化することを想定しています。
- 単元株（lot_size）は現状グローバル定数として扱われますが、将来的には銘柄別設定に対応する拡張が設計されている箇所があります（コメント参照）。
- ログレベルは LOG_LEVEL 環境変数で制御できます。

---

この README はコードベースからの情報に基づいて作成しています。実際の運用前には必ず `python -m kabusys.validate_config` で設定検証を行い、.env の値を確認してください。さらに、openai / ブローカー接続等の外部依存は安全に扱い、テスト環境（paper_trading）での動作確認を強く推奨します。