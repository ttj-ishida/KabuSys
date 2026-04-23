# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システムの一部実装です。戦略・ポートフォリオ構築・注文実行・監視・研究用ユーティリティ・AI ベースのニュースセンチメント評価などを含みます。本 README はプロジェクト概要・機能一覧・セットアップ手順・基本的な使い方・ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群から構成されます。

- 戦略・ファクター計算（research）
- ポートフォリオ構築（portfolio）
- 注文管理・ExecutionEngine（execution）
- 監視（monitoring）：システム稼働監視・リスク監視・Kill Switch 等
- AI モジュール（ai）：ニュースの NLP によるセンチメント評価、レジーム判定
- 環境設定・検証ツール（config_setup / validate_config）
- ユーティリティ（logging_setup / process_priority など）
- Paper Trading 向けツール（tools）

設計方針の要点：
- 本番 DB（SQLite）と Paper Trading 用 DB は分離
- DuckDB を分析用に利用（prices_daily 等テーブルを想定）
- 外部 API 呼び出し（OpenAI など）は明示的な API キーの指定を要求
- フラグファイル（data/kill.flag, data/stop_requested.flag 等）でプロセス制御を行う

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env の対話的作成・更新を支援
- 設定検証 CLI（python -m kabusys.validate_config）
  - .env と config/*.yaml の存在・基本妥当性をチェック
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - 本番/ペーパートレード切替対応（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント生成
  - PID ファイル、停止フラグに対応
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - SystemMonitor を定期ポーリング（既定 60 秒）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能
  - 監視ログは SQLite に保存（monitoring.db）
- 監視サブシステム（kabusys.monitoring）
  - system_monitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス検出
  - risk_monitor: ドローダウン / ポジション上限をチェックしリスクログを作成
  - kill_switch: リスクトリガーで data/kill.flag を書き込み ExecutionEngine 停止を促す
  - monitoring_db: 監視用テーブル群（system_status / trade_logs / positions / risk_logs / dashboard）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等重・スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究用（kabusys.research）
  - ファクター（モメンタム・ボラティリティ・バリュー）計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI 機能（kabusys.ai）
  - news_nlp: raw_news を OpenAI へ送りセンチメントを ai_scores へ保存
  - regime_detector: ETF の MA200 とマクロニュースを合成して market_regime を算出
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

以下はローカルで動かすための基本手順例です。

1. リポジトリをクローン / ソースを準備
   - プロジェクトルートに `src/` があり、Python パッケージは `kabusys` です。

2. Python 環境を準備（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なライブラリをインストール
   以下のパッケージが本コード中で使用されています（バージョンは環境に合わせて指定してください）。
   - duckdb
   - psutil
   - openai
   - PyYAML（optional：validate_config の YAML 検証で使用）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

   注: SQLite は標準ライブラリで提供されます。

4. .env を作成
   - 対話式ウィザードを推奨:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限設定が必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主な環境変数（例、デフォルトが用意されているもの）:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - OPENAI_API_KEY: OpenAI を使う機能がある場合に設定
     - LOG_LEVEL, LOG_DIR など

5. 設定の検証
   ```
   python -m kabusys.validate_config
   # 警告も FAIL として扱う場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの準備
   - デフォルトで `data/`、`logs/` ディレクトリが使用されます。自動作成されますが、権限設定など必要なら事前に作成してください。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（フォアグラウンド）
  ```
  python -m kabusys.run_execution
  ```
  動作ポイント:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録。
  - 停止したい場合はプロジェクトルートの `data/stop_requested.flag` を作成すると起動中のループが検知して終了します。
  - 実行時に `data/execution.pid` が書き込まれます。

- Monitoring を起動（ポーリング監視）
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視用 DB は Settings.sqlite_path（デフォルト data/monitoring.db）。monitoring は環境にかかわらず本番 sqlite_path を使用する設計になっています。
  - 停止フラグ: `data/stop_requested.flag` を作成すると監視ループが終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI（ニューススコア／レジーム判定）
  - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または関数呼び出しで指定）。
  - news_nlp.score_news()、regime_detector.score_regime() を利用して DuckDB 接続経由で書き込みできます。
  - 大量 API 呼び出しのため API レートや課金に注意してください。

---

## プロセス制御とフラグ

- 停止要求（共通）
  - data/stop_requested.flag: run_execution/run_monitoring の起動ループがこのファイルを検知して安全に終了します。

- Kill Switch（実運用の強制停止）
  - monitoring の判定で `data/kill.flag` が書き込まれると ExecutionEngine 停止用の信号となります。
  - `KILL_FLAG_CLEAR_ON_START` を 1 に設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

- PID ファイル
  - execution は `data/execution.pid` へ PID を出力します（設定によりPath変更可）。

---

## ログ

- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - stdout（StreamHandler）と日次ローテーションファイル（logs/<app_name>.log）を設定します。
  - デフォルトログディレクトリ: logs/
  - ローテーションは日次、30 日分保持

---

## 主要ファイル / ディレクトリ構成

（プロジェクトルート: src/kabusys 以下を基準にしています）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（自動 .env ロード、Settings クラス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・CRUD ラッパー
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 複数モニターの定期実行ロジック
    - (その他: trade_monitor.py, alert_manager.py 等 を含む想定)
  - portfolio/
    - __init__.py
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・集計キャップ処理
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - utils/
    - __init__.py
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定（psutil 使用）
  - (その他のパッケージ: data/, execution/ 等が存在する想定)

---

## 環境変数 主要一覧

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境 / 動作制御
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - KILL_FLAG_CLEAR_ON_START: 0|1

- DB/ファイルパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - PAPER_FILL_MODE: instant | partial | never | reject

- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector 等で必要

- Monitoring
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

---

## 開発メモ / 注意点

- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離された専用 SQLite (`PAPER_TRADING_SQLITE_PATH`) を使用するよう設計されています。
- monitoring は「環境にかかわらず」本番 sqlite_path を参照するコード箇所があるため、運用時に DB パスの指定に注意してください（Settings に基づく挙動）。
- OpenAI の呼び出しにはレートリミットやエラー処理（リトライ）が組み込まれていますが、API 利用量には注意してください。
- ローカルでの開発時は KABUSYS_ENV=development を使用し、実際の発注が行われない設定にしておくことを強く推奨します。
- `.env` は絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも注意書きあり）。

---

必要であれば、README に追加するサンプル .env テンプレート、主要ユースケース（デモフロー：データロード → research → portfolio → execution）や、個別モジュールの API 仕様（関数シグネチャ）なども作成します。どの情報を優先して追記しましょうか？