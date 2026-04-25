# KabuSys

日本株向けの自動売買システム（プロトタイプ）。バックエンドはローカル DB（SQLite / DuckDB）を中心に構成され、発注実行、監視、ポートフォリオ構築、リサーチ、AI ベースのニュース解析などの機能を備えます。

以下はリポジトリ内のコードベースに基づく README.md です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するモジュール群の集合です。主な目的は以下：

- 発注実行 (ExecutionEngine)
- 実行状況・システム状態の監視（Monitoring）
- ポートフォリオ構築（候補選定・配分・株数決定）
- ファクター計算・研究（DuckDB を用いた時系列解析）
- ニュースの NLP によるセンチメント評価（OpenAI API を利用）
- ペーパートレード用の分離された DB と検証レポート

設計上のポイント：
- 設定は .env（および .env.local）で管理。`.env` は自動読み込みされる（無効化可能）。
- Paper Trading（`KABUSYS_ENV=paper_trading`）時は本番 DB と分離された SQLite を使用。
- ログはコンソール + 日次ローテートファイル（`logs/<app>.log`）で出力。
- 実行停止はフラグファイル（`data/kill.flag`, `data/stop_requested.flag`）で制御。

---

## 機能一覧

- 実行（run_execution.py）
  - BrokerClientFactory 経由でブローカークライアントを生成
  - OrderManager / RiskManager / Reconciler を組み合わせて取引セッションを実行
  - Paper Trading 時に MockBroker を用いる（DB は `data/paper_trading.db`）

- 監視（run_monitoring.py, monitoring/）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態、データ鮮度を監視
  - TradeMonitor: 取引ログの整合性・滞留注文などをチェック
  - RiskMonitor: ドローダウン・ポジション上限を監視し、risk_logs に記録
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み、ExecutionEngine 停止を促す
  - AlertManager 経由でアラートを外部へ通知（LINE 等）

- ポートフォリオ（portfolio/）
  - 候補選定、等配分・スコア重み、リスク調整（セクターキャップ、レジーム補正）
  - position sizing（単元株丸め、アグリゲートキャップ）

- リサーチ（research/）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily/raw_financials）
  - 将来リターン計算、IC（Information Coefficient）や要約統計

- AI（ai/）
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に書込
  - regime_detector: ETF(ma200) とマクロニュースを組合せて市場レジーム判定

- ツール（tools/）
  - paper_verification_report: ペーパートレード検証レポート生成（稼働率・成功率・レイテンシ等）

- 設定支援
  - config_setup.py: .env を対話式に生成・更新
  - validate_config.py: 起動前チェック（必須環境変数・config/*.yaml・パス等）

---

## セットアップ手順

1. Python 仮想環境を作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール
   - 主な依存: duckdb, psutil, openai, PyYAML（任意：validate_config の YAML チェック）、その他標準ライブラリ
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```

   ※ requirements.txt がある場合はそれを利用してください（本リポジトリには含まれていません）。

3. .env を作成
   - 対話式ウィザードを使う：
     ```
     python -m kabusys.config_setup
     ```
   - あるいはリポジトリルートに `.env` を手動作成してください。主な環境変数は下記参照。

4. 設定検証（任意・必須項目の確認）
   ```
   python -m kabusys.validate_config
   ```
   警告も FAIL 扱いにしたい場合:
   ```
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ・DB は起動時に自動作成されます。必要に応じて `data/` 配下を作成してください。

---

## 主要な環境変数（抜粋）

- 必須（少なくとも設定が必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- システム / 実行
  - KABUSYS_ENV — 実行環境: development | paper_trading | live (default: development)
  - LOG_LEVEL — ログレベル（DEBUG/INFO/…）
  - LOG_DIR — ログ格納ディレクトリ（デフォルト: logs/）
  - PID_FILE_PATH — 実行時に作成する PID ファイル（default: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグ（default: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

- データベース
  - DUCKDB_PATH — DuckDB ファイル（default: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 SQLite（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（default: data/paper_trading.db）

- Paper Trading 関連
  - PAPER_FILL_MODE — mock ブローカーの約定モード: instant | partial | never | reject

- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

- その他
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、default: 60）
  - ※ stop / shutdown フラグ: `data/stop_requested.flag`（存在すると監視/実行ループが停止します）

---

## 使い方（例）

- .env の作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine の起動
  - 通常は次のモジュールを直接実行：
    ```
    python -m kabusys.run_execution
    ```
  - Paper Trading 環境で起動する例：
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実行中に停止したい場合は `data/stop_requested.flag` を作成するか、実行側は kill.flag 検知で停止します。

- Monitoring の起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パス指定:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- AI スコアリング（プログラム内から呼ぶ例）
  ```python
  import duckdb
  from kabusys.ai import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  from datetime import date
  cnt = score_news(conn, target_date=date(2026, 4, 15), api_key="sk-...")
  print("書き込んだ銘柄数:", cnt)
  ```

- レジーム判定（regime_detector）
  ```python
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 4, 15), api_key="sk-...")
  ```

---

## 停止・Kill Switch の扱い

- ExecutionEngine 停止シグナル:
  - kill.flag（`Settings.kill_flag_path`, default: `data/kill.flag`）が存在すると ExecutionEngine 停止条件として扱われます。
  - KillSwitch は RiskMonitor の結果に基づいて kill.flag を書き込むことがあります（ドローダウン等）。

- 全般停止:
  - `data/stop_requested.flag` を作成すると、run_execution / run_monitoring の起動ループが検知して終了します。
  - run_execution は起動時に `data/execution.pid` を作成します（PID ファイルの保存先は設定可能）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの `src/kabusys` 相当を抜粋した構成例：

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定の取得ロジック（Settings クラス）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト

  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py

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

  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py — 統一的なログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

- data/ — デフォルトの DB / flag / pid 保存場所（起動時に作成される）
  - monitoring.db (default)
  - paper_trading.db (paper trading 用)
  - kabusys.duckdb
  - kill.flag, stop_requested.flag, execution.pid

- logs/ — ログファイル（app ごとに日次ローテート）

---

## 開発上の注意・設計メモ

- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダにも注意書きあり）。
- Paper Trading は本番 DB と完全分離する設計（`KABUSYS_ENV=paper_trading`）。
- DuckDB 側のテーブル（prices_daily, raw_financials, raw_news 等）は外部データ取り込みパイプラインを想定。リサーチ・AI モジュールはこれらのテーブルに依存します。
- OpenAI API を使う機能は API 呼び出しの失敗に対してフェイルセーフ（ログ出力してスキップ）する設計です。ただしキーの未設定は例外になる場合あり。

---

必要であれば README に追記する内容（詳しい環境変数一覧、DB スキーマ、起動/運用手順のチェックリスト、サンプル .env など）を作成します。どの項目を拡張したいか教えてください。