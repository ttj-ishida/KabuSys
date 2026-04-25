# KabuSys

日本株向け自動売買システムの一部モジュール群。  
このリポジトリには、監視 (monitoring)、発注実行 (execution)、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）などのユーティリティが含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買や関連アナリティクスを支援するライブラリ／実行スクリプト群です。  
主な目的は以下のとおりです。

- ExecutionEngine による注文発行・オーダー管理（本番 / ペーパートレード切替）
- Monitoring によるシステム稼働監視、トレードログ・リスクイベントの永続化
- Portfolio 構築（候補選定・重み付け・ポジションサイズ計算）
- Research 用のファクター計算・特徴量分析
- AI モジュールによるニュースの NLP スコアリング、レジーム判定
- 各種 CLI ツール（設定ウィザード / 設定検証 / レポート生成）

設計方針として、DB は DuckDB（分析用）と SQLite（監視・発注履歴）を使い分け、実行環境（KABUSYS_ENV）に応じて動作を切り替えます。

---

## 機能一覧

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading 時は MockBroker を利用し、paper_trading 用の SQLite（data/paper_trading.db）へ記録して本番 DB と分離
- run_monitoring.py
  - SystemMonitor を定期ポーリングして system_status 等を記録
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- monitoring モジュール
  - MonitoringDB（SQLite）の初期化 / 永続化 API
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度）
  - TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine / AlertManager（監視・アラート）
- portfolio モジュール
  - 候補選定、等金額/スコア加重配分、ポジションサイズ決定、セクター上限・レジーム乗数
- research モジュール
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- ai モジュール
  - news_nlp: OpenAI（gpt-4o-mini 想定）を用いたニュースセンチメント集約 → ai_scores 書き込み
  - regime_detector: ETF MA とマクロニュースの LLM スコアを合成して market_regime を判定
- tools
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート生成
- 設定ユーティリティ
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: .env と config/*.yaml を事前検証

---

## 動作要件（推奨）

- Python 3.10+（typing の | 演算子などを使用）
- 必要パッケージ（pip でインストール）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML — validate_config の YAML 検証で使用
- SQLite（Python 標準 sqlite3 で利用）
- ネットワーク接続（kabuステーション API / OpenAI API を利用する場合）

例:
```bash
python -m pip install duckdb psutil openai PyYAML
```

（requirements.txt があればそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開

2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil openai PyYAML
   ```

4. .env の作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいはプロジェクトルートに `.env` を手動作成（.env.example を参照）  
     必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     推奨（または任意）:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - OPENAI_API_KEY（AI モジュールを使う場合）
     - LOG_LEVEL（DEBUG/INFO/...）

   サンプル（.env）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. 設定検証（起動前に実行推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする:
   python -m kabusys.validate_config --strict
   ```

6. ディレクトリ権限
   - デフォルトでログは `logs/`、DB は `data/` に作成されます。書き込み権限を確認してください。

---

## 使い方（起動例）

- ExecutionEngine を起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 実行中に data/stop_requested.flag が書き込まれると Graceful に停止します。
  - 実行時は `data/execution.pid`（デフォルト）に PID が書き出されます。

- Monitoring を起動（SystemMonitor のポーリング）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）。
  - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依存せず）。
  - 停止は data/stop_requested.flag を作成することで可能。

- ペーパートレード検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（ニューススコア／レジーム判定）
  - プログラム内から呼び出し:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは `OPENAI_API_KEY` 環境変数に設定するか、関数呼び出し時に `api_key` を渡す必要があります。

- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` を自動読み込みします。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 運用上のポイント

- ペーパートレードと本番データの分離
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用し、本番 sqlite_path と完全に分離します。

- Kill Switch / 停止フラグ
  - kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）は ExecutionEngine を停止させるためのフラグです（KillSwitch による自動書き込みや手動での作成が可能）。
  - stop_requested.flag（data/stop_requested.flag）は run_execution/run_monitoring の外部停止制御に使われます。

- ログ
  - ログは既定で `logs/<app_name>.log` に日次ローテートで保存されます（30日分保持）。
  - コンソール出力は stdout に送られます。ログ出力先は `LOG_DIR` 環境変数または setup_logging の引数で変更可能。

- プロセス優先度
  - 起動時にプロセスを "high" 優先度に設定する処理が含まれますが、権限不足により失敗する場合は警告が出ます。

- OpenAI 呼び出しのフェイルセーフ
  - AI モジュールは API エラー時やパースエラー時にフォールバック（スコア 0.0 など）して継続するよう設計されています。繁雑なエラーハンドリング（リトライ、バックオフ）を実装済みです。

---

## 主要ディレクトリ構成

以下は src/kabusys 以下の主要ファイル／ディレクトリ（抜粋）と簡単な説明です。

- src/kabusys/__init__.py
  - パッケージ初期化、バージョン定義

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（モジュール実行可能）

- src/kabusys/run_monitoring.py
  - SystemMonitor ポーリング実行スクリプト

- src/kabusys/config.py
  - 環境変数 / Settings 管理、自動 .env ロードロジック

- src/kabusys/config_setup.py
  - 対話式 .env 生成ウィザード

- src/kabusys/validate_config.py
  - 起動前の設定検証 CLI

- src/kabusys/monitoring/
  - monitoring_db.py : SQLite テーブル初期化 + MonitoringDB（永続化層）
  - system_monitor.py : システム状態・データ鮮度監視
  - risk_monitor.py : ドローダウン / ポジション上限監視
  - trade_monitor.py, alert_manager.py, kill_switch.py, monitoring_engine.py 等

- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など（発注ロジック）

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（ポートフォリオ構築）

- src/kabusys/research/
  - factor_research.py, feature_exploration.py（ファクター/分析）

- src/kabusys/ai/
  - news_nlp.py（ニューススコアリング）
  - regime_detector.py（市場レジーム判定）

- src/kabusys/tools/
  - paper_verification_report.py（ペーパートレード検証レポート）

- src/kabusys/utils/
  - logging_setup.py（統一ログ設定）
  - process_priority.py（プロセス優先度設定）
  - などユーティリティ

- data/
  - デフォルト DB / フラグファイル格納場所（data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag 等）

- logs/
  - ログファイル出力先（デフォルト）

---

## よくある質問 / 注意点

- Q: ペーパートレードは本番データベースを汚しますか？  
  A: いいえ。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、監視 DB とは分離されます。

- Q: OpenAI を使いたいが API キーは？  
  A: 環境変数 `OPENAI_API_KEY` を設定するか、該当関数に直接 `api_key` を渡してください。

- Q: MONITOR_POLL_INTERVAL はどこで設定？  
  A: 環境変数 `MONITOR_POLL_INTERVAL`（秒）。不正な値や 0 以下はデフォルト 60 秒にフォールバックします。

- Q: 起動時に既存の kill_flag を自動クリアしたくない（本番安全性）  
  A: `.env` の `KILL_FLAG_CLEAR_ON_START` を `0`（デフォルト：0）にしてください。`1` にすると起動時に kill.flag を自動でクリアします（開発時のみ推奨）。

---

## 開発 / テスト

- 単体関数群（portfolio/position_sizing, research/* など）は外部副作用を持たない純粋関数として設計されています。ユニットテストが書きやすく、DuckDB 接続はモック可能です。
- AI 呼び出しや psutil 周りは patch / mock してテストしてください（例: unittest.mock.patch）。

---

README は随時更新してください。特に config/*.yaml の仕様や ExecutionEngine の詳細、外部 Broker クライアントの実装（kabuステーション連携部分）は運用に合わせて追記する必要があります。