# KabuSys

KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装したモジュール群です。本リポジトリは以下の領域をカバーします：データパイプライン、ファクター計算・研究、ポートフォリオ構築、発注実行（実環境 / ペーパートレード）、監視・アラート、LLM を使ったニュース解析など。

バージョン: 0.1.0

---

## プロジェクト概要

- Python モジュール群として設計され、CLI（python -m kabusys.…）で主要なワークフローを起動できます。
- DuckDB を分析用 DB として、SQLite を監視／発注ログ用 DB（軽量永続化）として利用します。
- 実際の発注は kabuステーション API を経由する想定。ペーパートレード環境（KABUSYS_ENV=paper_trading）の場合は MockBrokerClient を利用して本番 DB と分離します。
- OpenAI（gpt-4o-mini など）を用いたニュース NLP / レジーム判定機能を一部提供（API キー必須）。
- 監視（Monitoring）や Kill Switch により安全停止・アラートを行う仕組みを備えています。

---

## 主な機能一覧

- 環境設定
  - 対話式 .env 作成 / 更新ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行 / 監視
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV に応じて本番 / ペーパートレードを切替
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）対応
  - SystemMonitor ポーリング（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き
    - system_status / trade_logs / risk_logs / dashboard の永続化

- モニタリング・リスク管理
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度チェック
  - TradeMonitor: 発注ログの異常検知（長時間未更新注文、約定異常など）
  - RiskMonitor: ドローダウンやポジション上限監視、ログ記録と KillSwitch トリガー
  - MonitoringEngine: これらをまとめて定期実行、アラート通知連携

- ポートフォリオ構築（純粋関数）
  - 候補抽出、等金額 / スコア加重重み、セクター制約、レジーム乗数、建玉サイズ計算

- リサーチ / ファクター計算（DuckDB）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン、IC（Information Coefficient）、統計サマリ

- AI 関連
  - ニュース NLP による銘柄ごとのセンチメント計算（OpenAI）
  - マクロ記事を使った市場レジーム判定（OpenAI + ETF MA200）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を用意（推奨: 3.10+）
2. 依存ライブラリをインストール
   - 必須（主要）:
     - duckdb
     - psutil
     - openai
   - オプション:
     - PyYAML（config/*.yaml の内容検証を行う場合）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. リポジトリルートに移動して .env を作成
   - 対話式で作る:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env.example を参照して手動作成（.env を Git にコミットしないこと）

4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ / ログディレクトリの準備
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
   - 必要なら環境変数で上書き:
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR

注意: Settings モジュールは自動でプロジェクトルートの .env をロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
- LOG_LEVEL（DEBUG/INFO/...）
- LOG_DIR（ログ保存先）
- OPENAI_API_KEY（AI 機能利用時）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数, デフォルト 60）
- PAPER_FILL_MODE（ペーパートレードの成行・部分約定挙動: instant/partial/never/reject）

---

## 使い方（主なコマンド）

- 環境ウィザード / .env 作成
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（実際の発注/ペーパートレードを含む）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します。
  - 停止は data/stop_requested.flag を作成すると検知してシャットダウンします（または kill.flag により運用停止トリガー）。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）

- Monitoring 起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に関わらず）。

- Paper Trading 検証レポート生成
  ```
  # デフォルト DB (= env または data/paper_trading.db)
  python -m kabusys.tools.paper_verification_report

  # 期間指定 / DB 指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（ライブラリ呼び出し例）
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date, APIキーを受け取ります。例:
    ```
    from openai import OpenAI
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10), api_key="sk-...")
    ```

---

## 停止 / Kill Switch の挙動

- run_execution / ExecutionEngine:
  - 起動中にプロセス外から停止したい場合、プロジェクトの data/stop_requested.flag（run_execution が参照する場所）を作成すると、安全に停止処理が行われます。
  - Kill Switch（監視側）で条件を満たすと data/kill.flag が書き込まれ、次回起動時に検出されます。KILL_FLAG_CLEAR_ON_START 設定で起動時に自動クリアすることができますが、本番では推奨されません（デフォルト 0）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理 (.env 自動ロード含む)
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）と ai_scores 書き込み
    - regime_detector.py     — マクロ + ETF MA200 によるレジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・単純 DB ラッパー
    - system_monitor.py      — CPU/メモリ/データ鮮度監視
    - trade_monitor.py       — （発注ログ監視; コードベースに依存）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねる

  - execution/               — 発注関連コンポーネント群（Engine, BrokerFactory, OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py     — ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン, IC, 統計
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ（コンソール + 日次ローテーション）
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

- data/                      — デフォルトの DB / フラグ / PID が想定される場所（自動作成されることが多い）
- logs/                      — ログ出力先（LOG_DIR で変更可）

---

## ログ設定

- 共通のセットアップ関数: kabusys.utils.logging_setup.setup_logging(app_name="…")
  - stdout に StreamHandler を出力し、日次ローテーションで logs/<app_name>.log に出力（デフォルト 30 日保持）。
  - LOG_LEVEL / LOG_DIR 環境変数で挙動を変更できます。

---

## 注意事項・運用上のメモ

- .env ファイルは機密情報を含みうるため、絶対に VCS にコミットしないでください。
- KABUSYS_ENV=live の場合は本番用設定です。LINE 通知や kill switch の設定などを事前に確認してください。
- AI 機能を使うには OPENAI_API_KEY を設定する必要があります。API 利用料やレート制限に注意してください。
- run_monitoring は監視用 DB（SQLite）のみを書き込みますが、Execution と同一の本番 SQLite を参照します（監視は環境にかかわらず本番 sqlite_path を使用する設計）。
- ペーパートレードは本番 DB とは別の PAPER_TRADING_SQLITE_PATH に書き込まれるようになっています（分離設計）。

---

## 開発上の補足

- DuckDB クエリは prices_daily / raw_financials / raw_news 等のテーブルを前提としています。テーブルがない場合は関連機能はエラーまたは空結果になります。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定すると自動で .env を読み込む挙動を抑制できます。
- 一部の内部 API 呼び出し（OpenAI など）はモック化してテスト可能な設計になっています（例: _call_openai_api を patch）。

---

README に書かれているコマンドや設定を参照し、まずは .env を作成 → 設定検証 → run_monitoring / run_execution を順に試してください。問題が発生した場合は logs/ 以下のログや .env の設定を確認してください。