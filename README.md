# KabuSys README

日本株自動売買システム（KabuSys）の簡易ドキュメントです。  
この README ではプロジェクト概要、主な機能、セットアップ手順、使い方、およびディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのコンポーネント群です。  
主な設計方針は次の通りです。

- モジュール化された実装（ExecutionEngine / Monitoring / Research / Portfolio / AI / Tools）
- 本番とペーパートレードを明確に分離（ペーパートレードは専用 SQLite DB を使用）
- DuckDB を使った分析・ファクター計算、SQLite を使った監視・トレードログ
- OpenAI を用いたニュース NLP / レジーム検出（任意）
- ロギングとプロセス優先度管理のユーティリティを同梱

バージョン: 0.1.0（パッケージ定義: src/kabusys/__init__.py）

---

## 機能一覧

- Execution
  - ExecutionEngine による発注処理（kabuステーション API 連携）
  - Paper trading モード（MockBrokerClient を利用、DB を分離）
  - リスク管理（RiskManager）や注文管理（OrderManager）
- Monitoring
  - SystemMonitor: CPU/MEM/DISK、プロセス生存、データ鮮度の監視
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウンなど
  - Kill Switch：条件により `data/kill.flag` を作成して Execution を停止
  - Monitoring DB（SQLite）：system_status / trade_logs / positions / risk_logs / dashboard 等
- Portfolio
  - 候補選定、重み計算、ポジションサイズ算出、セクター制約適用などの純粋関数群
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（情報係数）計算、統計サマリー等
- AI
  - News NLP（OpenAI を使った銘柄ごとのセンチメント算出）
  - Regime Detector（マクロニュース + ETF MA200 で市場レジーム判定）
- Tools
  - paper_verification_report: ペーパートレード結果の検証レポート生成
- ユーティリティ
  - 環境変数読み込み・ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - 統一ログ設定（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）

---

## セットアップ手順

前提:
- Python 3.9+（実際の要件は pyproject.toml 参照）
- 必要ライブラリ: duckdb, psutil, openai (AI 機能を使う場合), PyYAML（validate_config の詳細検査で使用）

1. リポジトリをチェックアウト / クローン
2. 仮想環境を作成して依存をインストール
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     ```
     （requirements.txt が無い場合は duckdb / psutil / openai / PyYAML 等を個別にインストール）

3. .env の作成（対話式ウィザード推奨）
   - ウィザード実行:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限設定するもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（デフォルト値あり）
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - OPENAI_API_KEY — AI 機能利用時に必要

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   警告も含めて厳密にチェックしたい場合:
   ```
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ（data）とログディレクトリ（logs）の作成は自動で行われますが、権限やマウントに注意してください。

---

## 使い方

基本的な起動コマンドはモジュールを直接実行します。

- ExecutionEngine を起動
  - 本番 / 開発モードは KABUSYS_ENV で制御
  - ペーパートレード:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    ペーパートレードでは MockBrokerClient を使用し、DB は `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
  - 本番:
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - 実行中のプロセスは `data/execution.pid` に PID を書きます。
  - 停止: `data/stop_requested.flag` を作成すると実行エンジンに停止シグナルが送られます（monitoring からも検知して停止する仕様）。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒単位に上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番用の `SQLITE_PATH` を使用して監視ログを書きます。
  - 停止: プロジェクトルートの `data/stop_requested.flag` を検知すると監視ループを終了します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで DB パスを指定可能（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）。

- OpenAI を使う AI 機能
  - 環境変数 `OPENAI_API_KEY` を設定してください。関数呼び出し時に引数で渡すことも可能。
  - AI 呼び出しは外部 API のため失敗時はフェイルセーフ（ゼロやスキップ）で継続する設計ですが、API キー未設定時はエラーになります。

- ログ
  - ログはデフォルトで `logs/<app_name>.log` に日次ローテートで出力されます（30 日分保持）。
  - `LOG_DIR` 環境変数でログディレクトリを変更可能。
  - ログレベルは `LOG_LEVEL` 環境変数（または setup_logging の引数）で設定します。

- Kill Switch / フラグ操作
  - Kill Switch が作動すると `data/kill.flag` が作成されます（内容は理由テキスト）。
  - `KILL_FLAG_CLEAR_ON_START=1` を .env に設定すると起動時に自動で kill.flag を削除します（本番では推奨しません）。
  - Execution の即時停止には `data/stop_requested.flag` を作成してください（run_execution/run_monitoring が検知して終了します）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — development | paper_trading | live（default: development）
- DUCKDB_PATH — 分析用 DuckDB（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（default: data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
- LOG_DIR — ログ保存ディレクトリ（default: logs）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必須）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" でクリア）

---

## よくある操作・トラブルシュート

- 設定チェックを行ってから起動する:
  ```
  python -m kabusys.validate_config
  ```
- .env を対話式で作る／更新する:
  ```
  python -m kabusys.config_setup
  ```
- 監視プロセスの停止（強制）:
  - `data/stop_requested.flag` を作成すると run_execution/run_monitoring は終了処理を行います
- kill.flag を手動でクリア:
  ```
  rm -f data/kill.flag
  ```
  （運用判断でのみ実行してください）
- ログが出力されない／ファイル作成に失敗する:
  - アプリは起動時にログディレクトリ作成を試みます。権限やマウントを確認してください。標準出力には必ず StreamHandler が出ます。

---

## ディレクトリ構成（主要ファイル）

リポジトリの `src/kabusys` 以下の主なモジュールを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / CRUD ラッパー
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/                — Execution に関する実装群（Engine / OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py

（上記のうち run_* / tools / config_* / utils / monitoring / portfolio / research / ai が主要機能）

---

## 開発メモ / 注意点

- DB マイグレーションは簡易的に実装されています（monitoring_db.init_monitoring_db が冪等にスキーマ作成および簡易カラム追加を行います）。
- AI 呼び出し（OpenAI）は外部依存でありレート制限や API 障害があり得ます。モジュールはリトライやフォールバックを備えていますが、API キー管理やコストに注意してください。
- 本番運用時は KABUSYS_ENV=live に設定し、Kill Switch / LINE 通知設定等を必ず確認してください。
- ペーパートレード時は本番 DB に影響を与えないよう PAPER_TRADING_SQLITE_PATH を利用してください。

---

追加で README に書いてほしい項目（例: デプロイ手順、CI、より詳細な設定ファイルの説明、API ドキュメントなど）があれば指示してください。