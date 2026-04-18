# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群を含むリポジトリの README です。  
このドキュメントはローカル開発・ペーパートレード・本番運用を想定した基本的な使い方とセットアップ手順をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買（アルゴリズム取引）を支援する Python モジュール群です。  
主な目的は以下です。

- データ取得 / ファクター計算（research）
- ポートフォリオ構築・ポジションサイジング（portfolio）
- ExecutionEngine を通した発注処理（execution）
- システム・トレード状況の監視とアラート（monitoring）
- ニュース NLP / レジーム判定などの AI 補助機能（ai）
- 各種ユーティリティ（logging, process priority, config）

コードはモジュール化されており、CLI 風にモジュールを直接実行して起動する設計になっています（例: python -m kabusys.run_execution）。

---

## 主な機能一覧

- 設定管理（env/.env 自動ロード、Settings クラス）
- 環境設定ウィザード（config_setup.py）で .env を対話式生成
- 起動前チェック（validate_config.py）で必須環境変数や設定ファイルの検証
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、本番 DB と分離して `data/paper_trading.db` に記録
  - 停止フラグ（data/stop_requested.flag）や kill.flag を用いた安全停止機構
- Monitoring（run_monitoring.py / monitoring エンジン群）
  - SystemMonitor, TradeMonitor, RiskMonitor を組み合わせて監視
  - SQLite（監視ログ）/ DuckDB（分析データ）への書き込み
  - MONITOR_POLL_INTERVAL によるポーリング間隔の上書き
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- AI 機能
  - news_nlp: ニュース記事を LLM でスコアリングして ai_scores に格納
  - regime_detector: マクロ + 指標から市場レジームを判定
- ロギングユーティリティ（logs 日次ローテーション）
- プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 依存関係（代表）

主要な外部ライブラリ（抜粋）:

- python 標準ライブラリ: sqlite3, logging, threading, datetime, ...
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証を行う場合に任意）

（プロジェクトに requirements.txt がない場合は上記を環境にインストールしてください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成・有効化
2. 依存パッケージをインストール（上記参照）
3. .env ファイルの作成
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動で作成。最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV (development | paper_trading | live) — デフォルトは development
     - OPENAI_API_KEY（AI 機能を使う場合）
     - その他: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR, PAPER_FILL_MODE など
4. 設定検証（起動前に推奨）:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```
   --strict を付けると警告も失敗扱いになります。
5. データディレクトリ / ログディレクトリを確認・作成
   - デフォルト:
     - data/: SQLite DB（data/monitoring.db, data/paper_trading.db）や pid/flag ファイル
     - logs/: ログファイル（例: logs/execution.log, logs/monitoring.log）

---

## 使い方（起動例）

- 実行（ExecutionEngine）を起動
  - 本番/開発/ペーパーは KABUSYS_ENV で指定
  - 実行例:
    ```
    # development (デフォルト)
    python -m kabusys.run_execution

    # paper trading モード（実際の発注は行わず paper DB を利用）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 起動時、プロセス優先度を "high" に設定し、SQLite / DuckDB に接続して Engine を起動します。
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag が存在するとエンジンは起動しません。起動後にこのフラグを作れば Engine を停止します。

- 監視 (Monitoring) を起動
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定（デフォルト 60 秒）
  - 監視は本番 sqlite_path を常に使用します（KABUSYS_ENV に依らない）
  - 停止フラグ: data/stop_requested.flag

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  # デフォルト DB パス（環境変数 PAPER_TRADING_SQLITE_PATH を参照）
  python -m kabusys.tools.paper_verification_report

  # 期間指定・別 DB
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI 機能（プログラムから呼び出す例）
  - ニューススコア生成:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行モード（development | paper_trading | live）デフォルト: development
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading 用の fill 挙動（instant | partial | never | reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、production では 0 推奨）

.env の自動ロード:
- プロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ログ・データ・停止制御

- ログ:
  - setup_logging により stdout ストリームハンドラと日次ローテーションのファイルハンドラを設定します。
  - デフォルトログディレクトリ: logs/
  - 各アプリケーションは app_name を指定してファイル (logs/<app_name>.log) に出力します（例: execution, monitoring）。

- データ:
  - DuckDB（分析用）: data/kabusys.duckdb
  - SQLite（監視ログ）: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db

- 停止制御:
  - プロセス停止（外部からの強制停止）には以下フラグファイルを利用:
    - data/stop_requested.flag — run_monitoring/run_execution のループを終了させるために監視されるファイル
    - data/kill.flag — KillSwitch によって書き込まれると ExecutionEngine 側で検出して安全停止させる

---

## ディレクトリ構成（抜粋）

リポジトリ内の主なファイル／ディレクトリ構成の抜粋です:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (存在する想定)
    - kill_switch.py
    - alert_manager.py (存在する想定)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

補足: 実際のリポジトリでは execution パッケージやデータベース関連の追加モジュールが存在します（OrderManager, BrokerClientFactory 等）。

---

## 注意事項 / 運用上のポイント

- 本番運用時は KABUSYS_ENV=live を慎重に扱ってください。validate_config の実行で本番用のガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の設定など）を確認できます。
- Paper Trading と本番の DB は明確に分離する設計です。KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用します。
- OpenAI を利用する機能（news_nlp, regime_detector）は API キーと料金が発生します。鍵流出に注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで動作します。必要に応じて LOG_DIR を設定してください。
- init_monitoring_db は既存 DB に対するマイグレーション（列追加）を行いますが、完全なスキーマ移行が必要な変更は手動で対応してください。

---

## 開発者向け補足

- 各モジュールは単体テストが書きやすい設計（依存注入で DB 接続やクライアントを渡す）になっています。
- duckdb の接続は分析処理（research / ai）で使用し、sqlite は監視・注文ログ用に使い分けられています。
- ローカルでの簡易動作確認:
  - .env を作成（config_setup を使う）
  - validate_config を実行
  - python -m kabusys.run_monitoring を一度起動して run_once 相当の動作を確認（監視ログが data/monitoring.db に書き込まれる）

---

README はここまでです。必要に応じて以下を教えてください:
- 追加で README に載せたいコマンドやサンプル .env のテンプレート
- CI / デプロイ手順の追記
- 各モジュール（ExecutionEngine や OrderManager）の詳細な使用例・APIドキュメント

ご希望があれば README.md の Markdown 形式での整形（テーブルやサンプル .env ブロック追加）も行います。