# KabuSys

日本株向け自動売買システムのリポジトリ。発注エンジン、監視/アラート、ポートフォリオ構築、リサーチ、AI を用いたニュースセンチメント/レジーム判定などのコンポーネントで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買運用を想定したモジュール群です。主要な役割は次のとおりです。

- ExecutionEngine：ブローカークライアントを通じた注文発行・注文管理・リスク管理
- Monitoring：システム稼働状態・注文状態・リスク監視および Kill Switch（停止フラグ）発動
- Portfolio：銘柄選定・重み付け・株数計算（単体で純粋関数的に動作）
- Research：DuckDB を利用したファクター計算・特徴量探索
- AI：OpenAI（gpt-4o-mini など）を利用したニュースセンチメント / レジーム判定
- CLI ユーティリティ：.env ウィザード、設定検証、ペーパートレード検証レポート生成 等

設計上、Paper Trading（疑似発注）は本番 DB と分離されるようになっており、安全に検証できます。

---

## 機能一覧

- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV による paper/live の切替）
  - run_monitoring.py：SystemMonitor をポーリングで定期実行
- 設定関連
  - config_setup.py：対話式 .env 生成ウィザード
  - validate_config.py：環境変数・config/*.yaml の事前検証 CLI
- 監視・アラート
  - system_monitor, trade_monitor, risk_monitor：各種チェックとログ永続化（SQLite）
  - KillSwitch：条件を満たすと data/kill.flag を書き出して ExecutionEngine を停止
  - MonitoringEngine：監視を束ねてポーリング実行
- ポートフォリオ構築
  - 候補選定、等配分 / スコア加重、リスク調整（セクター制限・レジーム補正）、株数決定（単元丸め、aggregate cap）
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー
- AI
  - news_nlp：ニュース記事を LLM でスコアリングし ai_scores に保存
  - regime_detector：ETF とマクロニュースを使って市場レジーム判定
- ツール
  - paper_verification_report.py：ペーパートレード DB を解析して PASS/FAIL レポートを生成

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10+（型注釈に Union | を使用）
- SQLite（Python 標準ライブラリに同梱）
- 推奨ライブラリ: duckdb, psutil, openai, pyyaml（設定検証時に YAML を検証する場合）

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows PowerShell
   ```

3. 必要パッケージのインストール
   ここでは最低限の例を示します（requirements.txt があればそちらを利用してください）。
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. ディレクトリ作成（logs / data）
   ```
   mkdir -p data logs
   ```

5. 環境変数設定（.env）
   - 初期設定はウィザードで作成できます:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env を手動作成してください（.env は Git にコミットしないでください）。
   - 主要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB のパス）
     - LOG_LEVEL（デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能を使う場合）

6. 設定検証（必須ではないが推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

注意: .env 自動読み込みはデフォルトで有効。テストまたは特殊用途で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方

起動スクリプト（パッケージとして実行）
- 実行エンジンを起動（本番/ペーパーは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```

  - KABUSYS_ENV=paper_trading の場合:
    - MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録します。
  - 実行中の制御:
    - 停止要求はプロジェクトルート/data/stop_requested.flag によって検知されます。
    - ExecutionEngine の PID は data/execution.pid に記録されます。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
  - 監視は Settings に指定された sqlite_path（monitoring DB）を使用します（監視は環境に依らず本番 sqlite_path を使用する実装）。
  - 停止フラグ（stop_requested.flag）を検知するとループを終了します。

ツール
- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB パス: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ログ
- logging_setup で統一的に設定されます:
  - コンソール出力（stdout）および日次ローテートされたファイル出力（logs/<app_name>.log）
  - LOG_DIR 環境変数でログ保存先を変更可能

Kill Switch / 停止フラグ
- KillSwitch は risk_monitor 等の結果に応じて data/kill.flag を書き込みます。ExecutionEngine は Settings.kill_flag_path（デフォルト data/kill.flag）をチェックして停止する設計です。
- 起動時に kill flag を自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）がありますが、本番では 0（クリアしない）を推奨します。

AI 機能
- news_nlp, regime_detector は OpenAI API を利用します。OPENAI_API_KEY を設定してください。
- API 呼び出しは堅牢化（リトライ・フォールバック）されていますが、鍵・料金に注意してください。

---

## 監視 DB（SQLite）スキーマ概要

monitoring/init_monitoring_db() により以下テーブルが作成されます（冪等）:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - 単一行（id=1）で dashboard 集計を保持（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value など）

init_monitoring_db は既存 DB に不足カラム（例: latency_ms, peak_value）がある場合の簡易マイグレーション処理も行います。

---

## ディレクトリ構成（主要ファイル）

（ルート）  
├─ data/                      # 実行時に生成する DB / flag / pid など  
├─ logs/                      # ログ出力先（デフォルト）  
├─ src/kabusys/                # パッケージ本体  
│  ├─ __init__.py              # パッケージ定義（__version__ 等）  
│  ├─ config.py                # Settings（環境変数読み込み・ヘルパ）  
│  ├─ config_setup.py          # .env 対話ウィザード CLI  
│  ├─ validate_config.py       # 設定検証 CLI  
│  ├─ run_execution.py         # ExecutionEngine 起動スクリプト  
│  ├─ run_monitoring.py        # SystemMonitor ポーリング起動スクリプト  
│  ├─ utils/                   # 汎用ユーティリティ  
│  │  ├─ logging_setup.py      # ログ設定ユーティリティ  
│  │  └─ process_priority.py   # プロセス優先度設定ユーティリティ  
│  ├─ monitoring/              # 監視関連コンポーネント  
│  │  ├─ monitoring_db.py      # SQLite 永続化 API  
│  │  ├─ system_monitor.py     # システム状態・データ鮮度監視  
│  │  ├─ trade_monitor.py      # 発注 / 約定の監視（ファイル参照等）  ※実装詳細あり  
│  │  ├─ risk_monitor.py       # ドローダウン・ポジション上限監視  
│  │  ├─ kill_switch.py        # Kill Switch 実装  
│  │  └─ monitoring_engine.py  # 各監視を束ねるエンジン  
│  ├─ execution/               # 発注関連（Engine / BrokerFactory / OrderManager 等）  
│  ├─ portfolio/               # ポートフォリオ構築（builder / sizing / risk_adjustment）  
│  ├─ research/                # リサーチ・ファクター計算  
│  ├─ ai/                      # AI 関連（news_nlp, regime_detector）  
│  └─ tools/                   # 補助ツール（paper_verification_report 等）  
└─ pyproject.toml / setup.cfg  # パッケージ設定（存在する場合）

---

## 開発上の注意点 / 運用上の注意

- .env は機密情報を含むため Git 管理しないでください（config_setup も README に警告を書き込みます）。
- KABUSYS_ENV を live に設定すると本番発注が行われます。設定と権限を十分確認のうえ慎重に運用してください。
- Monitoring は sqlite_path を使用して監視ログを永続化します。Paper Trading 時も監視は本番 sqlite_path を参照する点に注意してください（監視 DB は環境にかかわらず本番パスを使う設計）。
- AI（OpenAI）利用時は API キーと利用料金に注意。失敗時はフォールバックする実装ですが、意図せぬコスト発生を防ぐため本番キーの扱いは慎重に。

---

必要であれば、導入・運用手順をスクリプト化したサンプル systemd ユニットや Dockerfile、requirements.txt の例も作成できます。どの形式が必要か教えてください。