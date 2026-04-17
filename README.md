# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + 実行 / 監視ユーティリティ群）

このリポジトリは、注文実行エンジン、監視（Monitoring）コンポーネント、ポートフォリオ構築ロジック、リサーチ / ファクター計算、AI を用いたニュースセンチメント評価などを含むモジュール群を提供します。

主な目的は以下の通りです。
- 注文作成・管理・ブローカー同期（Execution）
- 実行状況・システム状態の巡回監視とアラート（Monitoring）
- ポートフォリオ構築（候補選定・重み・銘柄別株数計算）
- DuckDB を用いたファクター計算・リサーチ
- OpenAI を使ったニュースセンチメント / レジーム検出（AI）

---

## 機能一覧

- Execution
  - ブローカークライアント生成（実口座 / Paper Trading 切替）
  - Order 管理（作成、同期、キャンセル等）
  - リコンシリエーション（起動時の注文／ポジション復元）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor: 滞留注文チェック、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch: 条件発生時に停止フラグ（data/kill.flag）を書き込み Execution を停止
  - AlertManager: LINE Push によるアラート送信（クールダウン付き）
  - Streamlit ダッシュボード用表示モジュール
- Portfolio
  - 候補選定、等ウェイト／スコア加重計算、セクター上限適用、位置サイズ計算（単元株丸め、リスク制約）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン、IC（Spearman）計算、特徴量サマリ
- AI
  - news_nlp: raw_news を集め OpenAI でセンチメント評価 → ai_scores に書込
  - regime_detector: ETF MA200 とマクロニュースを合成して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB から期間別の稼働率・成功率・レイテンシ等を出力

---

## 必要条件 / 依存パッケージ

推奨: Python 3.10 以上（typing に | 演算子等を使用）

主な依存パッケージ（requirements.txt は別途用意してください）:
- duckdb
- psutil
- requests
- openai
- streamlit

標準ライブラリ: sqlite3, logging, threading, datetime, pathlib, os, time など

備考:
- psutil によるプロセス優先度や CPU affinity 設定は環境によって権限が必要になることがあります（root/管理者権限）。
- OpenAI を使う機能は OPENAI_API_KEY の設定が必要です。

---

## セットアップ手順

1. リポジトリをクローン、任意の仮想環境を作成・有効化

   ```bash
   git clone <このリポジトリのURL>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール

   ```bash
   pip install duckdb psutil requests openai streamlit
   ```

3. 環境変数の設定
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（優先順位: OS env > .env.local > .env）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用）。

   重要な環境変数（代表的なもの）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - OPENAI_API_KEY (AI 機能用)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (AlertManager 用)
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
   - PID_FILE_PATH (デフォルト: data/execution.pid)
   - KILL_FLAG_PATH (デフォルト: data/kill.flag)
   - MONITOR_POLL_INTERVAL (監視ループの秒数、デフォルト: 60)

4. 必要ならデータディレクトリ作成

   ```bash
   mkdir -p data
   ```

---

## 使い方（主要コマンド）

実行スクリプトはパッケージ内のモジュールとして実行できます。

- Monitoring の起動

  - 簡易（デフォルトポーリング間隔 60 秒）:

    ```bash
    python -m kabusys.run_monitoring
    ```

  - ポーリング間隔を環境変数で上書き:

    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

  - 停止方法:
    - run_monitoring はプロジェクトルートの data/stop_requested.flag を検知すると終了します（ファイルを作成して停止を依頼）。
    - キーボード割込み (Ctrl+C) でも停止します。

  備考:
  - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（Settings.sqlite_path）を使います。

- Execution エンジンの起動

  - 本番（デフォルト）:

    ```bash
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```

  - Paper Trading（MockBroker を使い、data/paper_trading.db に記録）:

    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

  - 実行はデーモンスレッドで行われ、data/stop_requested.flag を作成すると停止シグナルとなります。実行時に data/execution.pid に PID が書き込まれます。

- Paper Trading 検証レポート

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  デフォルト DB: data/paper_trading.db。別 DB を指定する場合は `--db PATH` または環境変数 PAPER_TRADING_SQLITE_PATH を使用。

- Streamlit ダッシュボード

  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 機能（news_nlp / regime_detector）
  - 実行には OPENAI_API_KEY が必要です（引数で渡すことも可能）。
  - news_nlp.score_news / regime_detector.score_regime を呼んでデータベースへ書き込みます（ライブラリ API）。

---

## 監視・停止フラグ / PID / Kill Switch

- 停止フラグ: data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルがあるとループを終了・停止します。
- Kill flag（Execution 強制停止用）: data/kill.flag
  - KillSwitch により条件発生時に書き込まれ、Execution 側で検出して停止処理を行います。
- PID ファイル: data/execution.pid
  - Execution 起動時に書き込まれ、SystemMonitor はこの PID を確認して実行プロセスの生存を監視します。

---

## 設定読み込みルール（.env の自動読み込み）

- 自動読み込みの挙動:
  - OS 環境変数 > .env.local (override=True) > .env (override=False)
  - プロジェクトルートは `.git` または `pyproject.toml` を探索して判定
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを停止

- .env のパースは Bash 風の簡易フォーマットをサポートしています（export キーワード、シングル/ダブルクォート、行末コメント等）。

---

## 重要な設計・運用上の注意

- Monitoring は常に Settings.sqlite_path（monitoring DB）を使います。Paper Trading を使っていても監視は別 DB を参照しません（監視は本番状態の判断に使われる想定）。
- Execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH を使い、本番 DB と分離します。
- OpenAI を使う処理は API 失敗時のフォールバックが入っていますが、API キー未設定なら明示的に例外を出す箇所もあります。AI 機能を使う場合は OPENAI_API_KEY を設定してください。
- プロセス優先度設定は psutil を通じて行います。権限により設定できない場合は警告ログを出してスキップします。

---

## ディレクトリ構成（主要ファイルのみ）

以下は src/kabusys 以下の主要ファイル・サブパッケージの抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite 永続化層（監視用）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py     (実装ファイル群: エンジン本体等)
    - broker_factory.py
    - ...
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/                      — 実行時に生成されるファイル（DB・PID・フラグ等）

（実装の詳細なファイルはコードベースを参照してください）

---

## 開発・デバッグのヒント

- ログレベルは環境変数 LOG_LEVEL で制御できます。
- .env.local を用いることで開発用設定をローカルだけ上書きできます（CI / 本番とは分離）。
- Monitoring の単体テストや手動検査には MonitoringEngine.run_once() を使うと個々のチェックを1回だけ実行できます。
- Streamlit ダッシュボードは監視 DB を read-only で開きます。MonitoringEngine を先に起動して DB を作成／更新しておく必要があります。

---

必要であれば、README にサンプル .env.example や requirements.txt、docker-compose 例などを追加で作成します。追加希望があれば教えてください。