# KabuSys — 日本株自動売買システム

このリポジトリは日本株向け自動売買システムの主要コンポーネント群（発注エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助など）をまとめたものです。設計方針としては「本番・ペーパーの分離」「ルックアヘッドバイアス回避」「外部 API 呼び出しは明示的に行う（環境変数で制御）」が採用されています。

主な実装言語: Python（標準ライブラリ + duckdb / psutil / openai 等）

## 機能一覧

- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Broker クライアントファクトリで実口座・モックを切替
  - RiskManager / OrderManager / Reconciler を組み合わせた注文管理
- Monitoring（監視サブシステム）
  - システム状態（CPU/メモリ/ディスク）の定期ポーリング
  - 発注ログ・ポジションの監視（滞留注文、約定異常）
  - リスク監視（ドローダウン、ポジション数上限）
  - Kill Switch（条件を満たすと data/kill.flag を書き込みエンジン停止）
- DB 永続化
  - SQLite（monitoring.db / paper_trading.db 等）: 監視・トレードログなど
  - DuckDB（kabusys.duckdb）: 価格データ・ファクター計算・リサーチ
- Portfolio construction
  - 候補選定、等重・スコア重み、ポジションサイズ算出、セクター制約、レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン・IC / 統計サマリの計算
- AI 補助
  - ニュース NLP（OpenAI を用いた銘柄別センチメント → ai_scores へ保存）
  - レジーム判定（ETF MA + マクロニュースの LLM スコアを合成）
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
  - 統一的なログ設定（logs/ 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

## セットアップ手順

1. Python 環境を作成・有効化（例: pyenv/venv）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   ※ requirements.txt がない場合は必要なパッケージを個別にインストールしてください:
   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証で YAML をパースする場合）
   （開発環境により他パッケージが必要になります）

2. プロジェクトの設定 (.env) を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動でファイルを作成（プロジェクトルートの .env）。最小例:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
   - 自動 env ロードはデフォルトで有効です。無効化するには環境変数:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```

4. データディレクトリを準備（必要に応じて）
   ```
   mkdir -p data logs
   ```

5. OpenAI を使う機能を利用する場合は API キーを設定
   ```
   export OPENAI_API_KEY=sk-...
   ```

## 使い方（主なスクリプト・ツール）

- 発注エンジン（ExecutionEngine）を起動
  - 本番 / ペーパートレードは KABUSYS_ENV で切替。paper_trading の場合は MockBroker を使い DB は data/paper_trading.db に記録されます。
  ```
  python -m kabusys.run_execution
  ```
  - 起動前に data/stop_requested.flag が存在すると起動しません（停止済み扱い）。
  - 実行中に同ファイルが作成されると安全に停止します。
  - PID は data/execution.pid に書き出されます。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で変更:
    ```
    export MONITOR_POLL_INTERVAL=30  # 秒
    ```
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に関係なく production sqlite_path を使用する仕様）。

- .env の対話式作成（再掲）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（再掲）
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 系（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）
  - ニューススコアリング（関数）:
    - kabusys.ai.score_news（内部で DuckDB を使い ai_scores に書き込み）
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime

- ログ
  - デフォルトログディレクトリ: logs/
  - ログファイル名: <app_name>.log（例: execution.log, monitoring.log）
  - ローテーション: 日次、30日保持
  - ログ設定は共通ユーティリティ kabusys.utils.logging_setup.setup_logging を各スクリプトが呼び出します

## 重要な環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1、デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する（1 で無効化）

## 停止・Kill 操作

- プロセス停止用フラグ（監視 / 実行スクリプト共通）
  - data/stop_requested.flag: 存在すると run_monitoring・run_execution は起動中／ループ中に検知して停止する
- Kill Switch（自動停止判定）
  - monitoring 側で条件を満たした場合 data/kill.flag が書き込まれ、ExecutionEngine 側で検出されると停止します
  - KillSwitch クラス経由での冪等な書き込み／削除が可能

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定処理、Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring loop 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading レポートツール
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI で銘柄別スコア算出）
    - regime_detector.py     — 市場レジーム判定（ETF MA + LLM）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ & DB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - (Execution エンジン関連のモジュール群)
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — 優先度 / CPU affinity ユーティリティ
    - __init__.py

- data/                     — デフォルトの DB / フラグ / pid を置く場所（実行時に作成される）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb  (実際は data/kabusys.duckdb)
  - stop_requested.flag
  - kill.flag
  - execution.pid

- logs/                     — 日次ローテートされるログファイル

## 開発上の注意点

- 環境変数は .env / .env.local から自動ロードされます（プロジェクトルートが .git または pyproject.toml で検出可能な場合）。
- 設定値に不備があると validate_config が検出します。特に本番（KABUSYS_ENV=live）では LINE 通知設定や kill flag の挙動を注意深く確認してください。
- DuckDB クエリはローカルの prices_daily / raw_financials / raw_news 等のテーブルを前提とします。データの整備と日付フィルタ（ルックアヘッド回避）に注意してください。
- OpenAI 呼び出しは外部 API であり、レート制限・障害を考慮したリトライ・フェイルセーフ設計が組み込まれていますが、API キー管理は慎重に行ってください。

---

問題が発生したり README に追記して欲しい項目があれば教えてください。設定項目のサンプルやよくあるトラブルシュート（ログの見方、DB の初期化方法など）を追加できます。