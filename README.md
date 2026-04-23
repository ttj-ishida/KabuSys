# KabuSys

日本株向け自動売買システムのモジュール群。戦略・ポートフォリオ構築、発注エンジン、監視・アラート、研究用ファクター計算、LLM を使ったニュースセンチメント評価などを含みます。

---

## 概要

KabuSys は以下の主要機能を備えた自動売買プラットフォームのコンポーネント群です。

- 戦略・ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine（発注・注文管理・リスク制御） — 本番 / ペーパー取引をサポート
- 監視（System / Trade / Risk）と Kill Switch（停止フラグ発行）
- DuckDB/SQLite を用いたデータ格納・分析
- OpenAI を利用したニュースセンチメント評価・市場レジーム判定
- 設定ウィザード (.env 作成) と検証 CLI
- ペーパートレード検証用レポート生成ツール

設計上、研究・バックテスト用の処理は本番発注フローから独立しており、DB 接続を介してデータを参照します。

---

## 主な機能一覧

- 設定管理
  - .env 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- 実行コンポーネント
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - Paper trading モードでは MockBroker を使用し、data/paper_trading.db に記録
- 監視コンポーネント
  - SystemMonitor ポーリングループ起動スクリプト: python -m kabusys.run_monitoring
  - Kill Switch：条件を満たすと data/kill.flag を書き込み ExecutionEngine 停止を促す
  - MonitoringDB: SQLite に監視ログ（system_status / trade_logs / risk_logs / positions / dashboard）を永続化
- 研究・分析
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索・IC 計算
- AI（OpenAI）
  - ニュース記事のセンチメント評価（ai_scores へ書き込み）
  - 市場レジーム判定（ma200 + マクロニュースの LLM 評価）
- ユーティリティ
  - ロギング設定（console + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - ペーパートレード検証レポート生成ツール

---

## 要求環境（目安）

- Python 3.9+
- 必要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合に必要）
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワーク接続（OpenAI を使用する場合）

※ 正確な requirements.txt はリポジトリに合わせて作成してください。

例（インストール）:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動。

2. 依存パッケージをインストール（上記参照）。

3. 環境変数設定 (.env) を作成
   - 対話式ウィザードを推奨:
     ```
     python -m kabusys.config_setup
     ```
   - .env を作成したら設定を検証:
     ```
     python -m kabusys.validate_config
     ```

4. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI 呼び出しを行う場合は必須
   - KABUSYS_ENV — 実行環境（development / paper_trading / live）
   - DUCKDB_PATH / SQLITE_PATH — デフォルトは data/kabusys.duckdb / data/monitoring.db

5. データディレクトリの作成（必要に応じて）
   - ログ: logs/
   - DB / flag: data/

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
  - paper_trading: 発注はモック（paper DB に記録）
  - live: 本番
- JQUANTS_REFRESH_TOKEN: J-Quants API
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパー注文の約定挙動（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: SystemMonitor ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（default: data/execution.pid）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

注意:
- Monitoring（run_monitoring）は KABUSYS_ENV にかかわらず監視用 DB 接続に settings.sqlite_path（デフォルト / 本番 path）を使用します。
- paper_trading の実行（run_execution）では settings.is_paper の場合に paper_sqlite_path を使用し、本番 DB と分離されます。

---

## 使い方

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  # strict モード: 警告も失敗扱いにする
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 通常（デフォルト DB を使用 / KABUSYS_ENV による挙動）
  ```
  python -m kabusys.run_execution
  ```
  - ペーパートレードの場合:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - 実行中は data/execution.pid が使用されます。stop は stop フラグや kill.flag により制御されます。

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - 監視ループを終了するにはプロジェクトルート/data/stop_requested.flag を作成します（存在検知で終了）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB を指定する場合:
  ```
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコア / レジーム判定
  - news_nlp.score_news, ai.regime_detector.score_regime は DuckDB 接続・日付・API キーを与えて呼び出します（ライブラリ API）。
  - 例（ライブラリ呼び出し）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

---

## 停止・Kill Switch

- stop_requested.flag
  - run_monitoring / run_execution が監視するファイル。ループ内で存在をチェックし、見つかると安定終了します。
  - パス例: project_root/data/stop_requested.flag

- kill.flag
  - KillSwitch（監視）によって書き込まれる停止フラグ。ExecutionEngine はこれを受けて安全に停止する仕組みを持ちます。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアされます（本番では推奨しません）。

---

## ロギング・DB

- ログ
  - デフォルト出力先: stdout（コンソール）＋ 日次ローテーションで logs/<app_name>.log（30日分保持）
  - ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。

- DB
  - DuckDB: 分析用（prices_daily, raw_financials 等）
  - SQLite:
    - 監視データ: data/monitoring.db（MonitoringDB が管理）
    - ペーパートレード: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
  - monitoring_db.init_monitoring_db はテーブル作成・簡易マイグレーションを行います。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings 管理（.env 自動ロード機能含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュース記事の LLM センチメント評価 / ai_scores 書き込み
  - regime_detector.py — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py — SQLite 永続化レイヤー（system_status, trade_logs, risk_logs, positions, dashboard）
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度 / プロセス監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — Kill Switch（flag 書込み）
  - (その他: trade_monitor, alert_manager 等が関連）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け（等重み / スコア重み）
  - position_sizing.py — 発注株数決定・集約上限処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - __init__.py
- research/
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - __init__.py
- portfolio/
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

（実際のファイルや補助モジュールはリポジトリ内を参照してください）

---

## 開発・運用上の注意

- .env は機密情報を含むため Git 等にコミットしないこと（config_setup も README に警告を出します）。
- 本番（KABUSYS_ENV=live）では LINE 通知等の設定を必ず確認してください。
- Monitoring は settings.sqlite_path（監視用 DB）を使用します。paper_trading モードでも監視 DB は production path を使う設計です（監視データは本番 DB に記録されるため運用時は注意）。
- OpenAI 呼び出しは API 制限・失敗を考慮したリトライ・フォールバック実装がありますが、API キーや利用量に注意してください。
- ローカル・CI での自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます（テスト用途）。

---

この README はリポジトリに含まれる主要ファイル群に基づいて作成しています。詳細な実装や追加の CLI、外部モジュールとの統合については各モジュールのドキュメント（ソースの docstring）を参照してください。