# KabuSys

日本株向け自動売買システムのライブラリ / 実行スクリプト群です。  
このリポジトリは、バックテスト用のリサーチユーティリティ、ポートフォリオ構築ロジック、Execution エンジン起動スクリプト、監視（Monitoring）周りのコンポーネント、および AI を使ったニュース NLP / レジーム判定モジュールなどを含みます。

---

## プロジェクト概要

- 目的: 日本株の自動売買（本番/ペーパートレード）を支援するコンポーネント群を提供する。
- 構成:
  - ExecutionEngine（発注・リスク管理・注文管理）
  - Monitoring（システム監視・取引監視・リスク監視・Kill Switch）
  - Portfolio（銘柄選定、重み付け、ポジションサイズ計算、リスク調整）
  - Research（ファクター計算、特徴量探索）
  - AI（ニュースのセンチメント評価、レジーム判定）
  - ユーティリティ（ログ設定、プロセス優先度等）
  - CLI ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - Broker クライアントの抽象化（Mock を含む）
  - 注文履歴の永続化（SQLite）
  - RiskManager によるドローダウン・利用率等の制御
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存確認 / データ鮮度監視
  - TradeMonitor：注文の滞留・約定異常検出（trade_logs 参照）
  - RiskMonitor：ドローダウン・ポジション上限監視（dashboard / positions 参照）
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）出力
  - MonitoringEngine：定期ポーリング & アラート送信
- Portfolio
  - 候補選定、等金額・スコア加重配分
  - セクター制約適用、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め、aggregate cap、コストバッファ）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI
  - news_nlp: OpenAI を用いたニュースセンチメント評価（ai_scores テーブルに保存）
  - regime_detector: ETF の MA とマクロニュースを合成して市場レジーム判定（market_regime テーブルに保存）
- ツール
  - config_setup: 対話式に .env を生成
  - validate_config: 起動前チェック（環境変数・config/*.yaml 等）
  - paper_verification_report: ペーパー取引ログからの検証レポート生成

---

## 前提・依存

- Python 3.10+
- 主な依存ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検査に任意）
- DB: SQLite（監視/ペーパートレード用）、DuckDB（価格データ / リサーチ用）
- 環境変数で挙動が多く制御されます（下記参照）

※ requirements.txt はリポジトリに含めてください（例: duckdb, psutil, openai, pyyaml）。

---

## セットアップ手順（ローカル開発用）

1. 仮想環境を作成・有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

3. 必要ディレクトリを作成
   ```
   mkdir -p data logs
   ```

4. 初期設定（.env の作成）
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env を手動で作成する（下記に例を掲載）

5. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   ```

---

## 環境変数（.env の例）

最低限必要（必須項目）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

例（.env）:
```
# 実行環境: development | paper_trading | live
KABUSYS_ENV=development

# API / トークン
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# ログ
LOG_LEVEL=INFO
LOG_DIR=logs

# Kill Switch
KILL_FLAG_CLEAR_ON_START=0

# OpenAI (AI 機能を使う場合)
OPENAI_API_KEY=sk-...
```

- 自動読み込み: プロジェクトルートにある `.env` / `.env.local` は起動時に自動読込されます（OS 環境変数より優先度低）。
- 自動ロードを無効化する場合:
  ```
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 実行方法（主要スクリプト）

- ExecutionEngine（発注エンジン）起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。data/stop_requested.flag を作成すると停止します。

- Monitoring（監視ループ）起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は常に本番 sqlite_path を使用して監視テーブルを初期化します（init_monitoring_db）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成すると完了します。

- 設定ウィザード（.env 作成）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db（`--db` または PAPER_TRADING_SQLITE_PATH で指定可）

- AI 機能（ニューススコア / レジーム判定）:
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API を利用します。OPENAI_API_KEY を設定してください。
  - これらは DuckDB 接続を渡して呼び出す関数 API です（CLI ラッパーはなし。独自スケジュール実行を想定）。

---

## 主要ファイルと動作上のポイント

- kabusys/config.py
  - .env 自動ロードロジック、Settings クラス。KABUSYS_ENV による切替や各種パスを取得。
- kabusys/run_execution.py
  - ExecutionEngine の起動スクリプト。プロセス優先度を上げ、PID ファイルを書き、スレッドで実行。
- kabusys/run_monitoring.py
  - SystemMonitor を使ったポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔を制御。
- kabusys/monitoring/monitoring_db.py
  - monitoring 用の SQLite スキーマ初期化（冪等）・永続化ロジック。テーブル:
    - system_status, trade_logs, positions, risk_logs, dashboard
- kabusys/utils/logging_setup.py
  - Stream + TimedRotatingFileHandler（デフォルト logs/）を設定する共通ユーティリティ。全起動スクリプトで利用。
- kabusys/utils/process_priority.py
  - psutil を使いプラットフォーム差を吸収して nice / priority を調整するユーティリティ。
- kabusys/portfolio/*
  - select_candidates, weight 計算, position sizing, sector cap, regime multiplier 等の純粋関数群。
- kabusys/research/*
  - DuckDB を用いたファクター計算・将来リターン・IC 計算等。
- kabusys/ai/*
  - news_nlp: OpenAI API を用いた銘柄別ニュースセンチメント評価（batching、リトライ、レスポンス検証を含む）
  - regime_detector: ETF MA とマクロニュースを用いた市場レジーム判定
- kabusys/tools/paper_verification_report.py
  - ペーパートレードのログを読み取り PASS/FAIL 判定のレポートを出力

---

## 使い方の例

1. .env を作成して（config_setup で）必要な値を設定する
2. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
3. DuckDB / SQLite / logs ディレクトリを準備
4. 監視を起動（別プロセスで常駐推奨）:
   ```
   python -m kabusys.run_monitoring
   ```
5. ExecutionEngine を起動（本番 or paper を .env の KABUSYS_ENV で切替）:
   ```
   python -m kabusys.run_execution
   ```
6. ペーパー取引検証:
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```

停止フロー:
- data/stop_requested.flag を作成すると run_execution/run_monitoring は検知して終了します。
- kill.switch（KillSwitch）は data/kill.flag を書き込み、ExecutionEngine 側で取り扱われます（Settings.kill_flag_path により位置を制御）。

ログ:
- デフォルト logs/<app_name>.log（日次ローテート、30 日保存）および stdout に出力されます。
- setup_logging() を全起動スクリプトで最初に呼び出しています。

---

## ディレクトリ構成

以下は主要なファイル・フォルダの一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/
    - broker_factory.py (参照あり)
    - execution_engine.py (参照あり)
    - order_manager.py (参照あり)
    - order_repository.py (参照あり)
    - reconciler.py (参照あり)
    - risk_manager.py (参照あり)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/ (上記)
  - data/ (実行時に使用するデータディレクトリ: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid 等)
  - logs/ (ログ出力先)

（実際のツリーはリポジトリのファイルに従ってください）

---

## 注意事項 / 運用上のヒント

- KABUSYS_ENV が `live` の場合は本番設定になります。LINE 通知等の設定不備に注意してください（validate_config の警告を参照）。
- paper_trading 用 DB は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- .env は機密情報を含むため Git 等にコミットしないでください（config_setup でも注意喚起あり）。
- OpenAI API を利用する機能は API キーの消費とレスポンス不安定性に注意。retry/backoff が組み込まれていますが、運用上の考慮が必要です。
- DuckDB のテーブル構造（prices_daily, raw_financials, raw_news 等）を準備しておく必要があります（データ供給パイプラインは別途実装想定）。

---

## 開発者向け

- 各モジュールはできるだけ純粋関数／副作用を最小にする設計を目指しています（特に portfolio/*, research/*）。
- テストしやすいように、DB 接続や API 呼び出しは外部から注入する（dependency injection）形になっています。ユニットテストではモックを渡してください。
- クラスや関数のドキュメントストリング（日本語）を参照すると振る舞いがわかります。

---

必要であれば README に次の内容も追加できます:
- requirements.txt / poetry/poetry.lock による依存管理手順
- systemd / supervisor 用のサービス定義例（監視・実行プロセスの常駐化）
- DuckDB / SQLite のスキーマ生成スクリプト例
- さらに詳しい設定リファレンス（各環境変数の説明を一覧化）

ほかに追記したい項目があれば教えてください。