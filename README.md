# KabuSys

日本株向け自動売買システムの Python コードベース。ポートフォリオ構築、発注実行、監視、研究（ファクター計算）、AI（ニュース NLP / レジーム検出）などの機能を含むモジュール群から構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は次を目的に設計されたモジュール式の自動売買フレームワークです。

- 市場データ（DuckDB）を用いたファクター計算・研究
- シグナル→ポートフォリオ構築→発注量決定（純粋関数群）
- 発注実行エンジン（実口座 / ペーパートレード切替）
- 実行・システムの監視とアラート / Kill Switch
- ニュースを LLM（OpenAI）で評価して AI スコアに反映
- 開発支援ツール（設定ウィザード、検証、ペーパートレードの検証レポート生成）

設計思想として、DB/外部 API の呼び出し箇所を明確に分離し、ユニットテストしやすい純粋関数と副作用を持つコンポーネントを分離しています。

---

## 主な機能一覧

- Execution（発注）
  - 実市場（live）とペーパートレード（paper_trading）の切替
  - BrokerClientFactory により実際のブローカーまたは MockBroker を生成
  - リスク管理（RiskManager）、オーダー管理（OrderManager）、Reconciler、ExecutionEngine など

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk / データ鮮度 / 実行プロセス検出
  - TradeMonitor: 取引ログの監視（滞留注文・約定異常など）
  - RiskMonitor: ドローダウン / ポジション上限監視、risk_logs への記録
  - KillSwitch: 条件に応じた停止フラグ (data/kill.flag) の書き込み
  - MonitoringEngine: 各モニタを束ねたポーリングループ

- Portfolio（銘柄選定・配分・株数決定）
  - 候補選定（select_candidates）
  - 等配分 / スコア配分（calc_equal_weights / calc_score_weights）
  - セクター集中制限（apply_sector_cap）
  - レジームに応じた乗数（calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes）

- Research（研究 / ファクター計算）
  - モメンタム、ボラティリティ、バリューファクター計算（DuckDB を使用）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等

- AI
  - news_nlp: raw_news を集約し OpenAI でセンチメントを算出、ai_scores に格納
  - regime_detector: ETF の MA とマクロニュースを組み合わせ市場レジーム判定

- ユーティリティ
  - 環境設定ロード/パーサ（.env 読み込みの堅牢化）
  - 対話型 .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ログ設定ユーティリティ（setup_logging）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

- ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

---

## セットアップ手順（開発 / ローカル実行向け）

1. Python 環境を用意（推奨: 3.10+）
2. 必要パッケージをインストール（プロジェクトに requirements.txt がある場合はそちらを使用）
   - 主な依存:
     - duckdb
     - psutil
     - openai (AI 機能を利用する場合)
     - PyYAML（設定ファイル検証 / 任意）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. プロジェクトルートにて .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env を直接作成（.env.example を参考）
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live） デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時）
     - LOG_LEVEL（INFO 等）
     - KILL_FLAG_CLEAR_ON_START（1にすると起動時に kill.flag を自動クリア）

4. 設定の検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの作成（必要に応じて）
   - デフォルトでは `data/`、`logs/` が使用されます。起動時に自動作成されることもありますが、権限等で失敗する場合は手動で準備してください。

---

## 使い方（起動 / CLI）

- 実行エンジンを起動する（ExecutionEngine）
  - ペーパートレード / 本番は KABUSYS_ENV で切り替え
  ```
  python -m kabusys.run_execution
  ```
  - 起動時にプロセス優先度を `high` に設定します。
  - ペーパートレード時は MockBrokerClient を使用し、専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。

- 監視モニタを起動する（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に本番用の sqlite_path（SQLITE_PATH）を参照します（監視ログは本番 DB に記録される想定）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```

- プログラムから利用（例）
  - portfolio / research / ai モジュールは関数ベース API を公開しています。DuckDB 接続や sqlite 接続を渡して使用します。
  - 例: ニューススコア算出
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    cnt = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

---

## 重要なファイル / フラグ

- data/stop_requested.flag
  - run_execution/run_monitoring が監視しているフラグ。存在するとループが終了します。
- data/execution.pid
  - ExecutionEngine が pid ファイルとして使用するパス（Settings.pid_file_path がデフォルト）。
- data/kill.flag
  - KillSwitch により書き込まれる停止フラグ（ExecutionEngine はこれを検出して停止する想定）。
- ログ
  - デフォルトログディレクトリ: logs/
  - デフォルトファイル: logs/execution.log, logs/monitoring.log（app_name に依存）
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一

---

## 環境変数（主なもの）とデフォルト

- KABUSYS_ENV: execution モード（development, paper_trading, live） — default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL — default: http://localhost:18080/kabusapi
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイル — default: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite — default: data/paper_trading.db
- PAPER_FILL_MODE: ペーパートレードでの約定挙動 — default: instant（instant / partial / never / reject）
- LOG_LEVEL: ログレベル — default: INFO
- LOG_DIR: ログ出力先ディレクトリ — default: logs/
- MONITOR_POLL_INTERVAL: 監視ループのポーリング秒数 — default: 60
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（1=有効、0=無効） — default: 0
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動で .env をロードする動作を無効化（値が存在すれば無効化）

---

## 動作上の注意 / トラブルシューティング

- .env に必要な必須キー（JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD）がないと Settings が例外を投げます。`python -m kabusys.validate_config` で事前にチェックしてください。
- Docker 等で実行する場合は data/ と logs/ に正しい書き込み権限を与えてください。
- DuckDB / SQLite ファイルはプロジェクト外の永続ボリュームに置くことを推奨します。
- OpenAI を使う機能は API のレート制限やネットワークエラーに対してリトライロジックを備えていますが、API キーが未設定だと例外になります。
- Monitoring は常に sqlite_path（監視 DB）へ書き込みます。paper_trading 時の Execution は paper_sqlite_path を使用して分離する設計です（監視 DB は別）。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主要モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP / OpenAI 連携
    - regime_detector.py     — 市場レジーム判定
    - __init__.py

  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 株数決定・集計調整
    - risk_adjustment.py     — セクター制限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py     — Momentum / Volatility / Value の計算
    - feature_exploration.py — forward returns / IC / 統計
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（tables）
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 取引ログ監視（存在）
    - risk_monitor.py        — ドローダウン・ポジション監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor の統合
    - alert_manager.py       — （存在）アラート配信（LINE など）
  
  - execution/
    - broker_factory.py      — ブローカークライアント生成
    - execution_engine.py    — Engine 実行ループ
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - (その他発注周りモジュール)

  - data/                    — データ用（デフォルト: data/ 以下に DB, flags を置く）
  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
    - __init__.py

---

## 開発上のヒント

- 各サブモジュールは明確に責務が分割されているため、単体でのユニットテストが書きやすくなっています（純粋関数は副作用が少ない）。
- DuckDB 接続を渡してローカルで手元データを使った研究・検証が可能です。
- AI 関連は API キーを渡せばオンデマンドで呼び出せますが、テスト時は内部呼び出し関数をモックするよう設計されています（_call_openai_api の置換など）。

---

必要に応じて README を拡張します。ドキュメントに追加したい項目（API リファレンス、詳細な起動例、Dockerfile / systemd ユニット例 など）があれば教えてください。