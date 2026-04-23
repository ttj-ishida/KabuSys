# KabuSys — 自動売買プラットフォーム（README）

このリポジトリは日本株の自動売買システム（KabuSys）のコードベースです。ここではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

目次
- プロジェクト概要
- 機能一覧
- 必要要件（依存パッケージ）
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数 / .env の主な設定
- 停止・Kill スイッチの取り扱い
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。主な役割は次のとおりです。
- 発注エンジン（ExecutionEngine）による注文管理とリスク管理
- 監視サブシステム（Monitoring）によるプロセス・システム状態・注文状況の常時監視
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算）
- リサーチ/ファクター計算（DuckDB 上の過去価格・財務データを用いた計算）
- AI を使ったニュース NLP（OpenAI API を利用したセンチメント算出）
- Paper Trading 用の検証レポート生成ツール

設計上、データベースは SQLite（監視・発注履歴）および DuckDB（分析用）を利用します。実行環境（development / paper_trading / live）に応じて挙動を切り替えます。

---

## 機能一覧
- Execution（発注）
  - Broker クライアントの抽象化（本番 / モック）
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - Paper Trading（KABUSYS_ENV=paper_trading）では MockBrokerClient と専用 DB を使用
- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度の監視
  - TradeMonitor：滞留注文・約定異常などの検出（trade_logs を参照）
  - RiskMonitor：ドローダウンやポジション上限の監視・アラート記録
  - KillSwitch：重大アラート時に `data/kill.flag` を書き込み ExecutionEngine 停止をトリガ
  - MonitoringEngine：上記を束ねてポーリング運転可能
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重配分、リスクベースの株数計算
  - セクターキャップ適用、レジーム乗数計算
- Research（リサーチ）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 特徴量探索・IC（Information Coefficient）計算ユーティリティ
- AI モジュール
  - news_nlp: ニュース記事を LLM で評価し ai_scores に書き込み
  - regime_detector: ETF ma200 乖離 + マクロニュースで市場レジーム判定（bull/neutral/bear）
- ツール
  - config_setup: 対話式で .env を作成・更新
  - validate_config: .env および config/*.yaml の起動前チェック
  - tools.paper_verification_report: Paper Trading の成績/稼働状況レポート生成

---

## 必要要件（主な依存）
以下はソース内の import から推測される主な依存パッケージです。プロジェクトに requirements.txt があればそちらを優先してください。

- Python 3.9+（型アノテーション等を使用）
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証：任意だが推奨）
- sqlite3（標準ライブラリ）
- その他標準ライブラリ（logging, pathlib, datetime, threading, etc.）

インストール例（venv を作成した後）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存をインストール（上記を参照）

3. 環境変数の初期作成（対話ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - 対話式に .env を生成します（デフォルト: プロジェクトルートの .env）。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV は development / paper_trading / live のいずれか

4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告も失敗扱いになります

5. ログディレクトリの確認
   - デフォルトログディレクトリ: logs/
   - LOG_DIR 環境変数で変更可能
   - setup_logging が起動時に自動作成を試みます

6. DB の初期化
   - 実行スクリプト（run_monitoring/run_execution）が起動時に必要なテーブルを作成します（init_monitoring_db）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  # strict モード
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine（注文エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（data/paper_trading.db）へ記録されます（本番 DB と分離）。
  - PID ファイル: data/execution.pid（設定で変更可）
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします（停止フラグ）

- Monitoring（監視ループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数指定（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視テーブルを作成します（init_monitoring_db）。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成することで監視ループが検知して終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能。

- AI モジュール（プログラムから呼び出す）
  - OpenAI API を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY 環境変数または関数引数で API キーを渡す必要があります。
  - 例（プログラム内から）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="sk-...")

---

## 環境変数 / .env の主な設定

重要なキーとデフォルト値（.env 作成時に確認してください）:

- KABUSYS_ENV (default: development)
  - 値: development | paper_trading | live
  - paper_trading は発注をモックし DB を分離
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db) — Monitoring DB
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 用 DB
- LOG_LEVEL (default: INFO) — DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR (default: logs/)
- OPENAI_API_KEY — news_nlp / regime_detector 用
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading のフィルモード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）
- その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用）

.env は config_setup により安全に生成できます。生成後は必ず Git にコミットしないでください。

---

## 停止・Kill スイッチの取り扱い

- 停止フラグ（stop loop）
  - ファイル: data/stop_requested.flag（プロジェクトルート）
  - run_monitoring/run_execution はループ中にこのファイルの存在をチェックし、存在すれば安全に終了します。
  - 運用でサービスを停止したい場合はこのファイルを作成してください。

- Kill Switch（自動停止トリガ）
  - ファイル: data/kill.flag（Settings.kill_flag_path で変更可能）
  - RiskMonitor が重大閾値（ドローダウン超過、ポジション上限超過等）を検知した際に KillSwitch がこのファイルを書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine は起動中に kill.flag を検知して停止します）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動で消去します（本番環境では 0 を推奨）。

- PID 管理
  - ExecutionEngine は data/execution.pid に PID を書きます（設定可能）。モニタリングや運用スクリプトで参照できます。

---

## ロギング
- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name=...)
- 出力:
  - コンソール（stdout）
  - 日次ローテートファイル: logs/<app_name>.log（デフォルト）
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で設定可能

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュールとファイルです（抜粋・説明付き）。

- src/kabusys/
  - __init__.py
  - config.py                — .env 自動読み込み・Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ma200）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル定義・CRUD）
    - system_monitor.py      — システム／データ鮮度監視
    - trade_monitor.py       — （存在）注文関連監視（ソース参照）
    - risk_monitor.py        — ドローダウン・ポジション監視
    - kill_switch.py         — kill.flag 操作
    - monitoring_engine.py   — 各 monitor を束ねる
    - alert_manager.py       — 通知管理（LINE など）（実装参照）
  - execution/
    - execution_engine.py    — エンジン本体（run_session 等）
    - broker_factory.py      — Broker クライアント生成（本番/モック）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - data/                    — 実行時に使用する DB / flag / pid を置く想定ディレクトリ（プロジェクトルート）

（注）上記は本 README 作成時の主要ファイルの抜粋です。リポジトリの全ファイルは実際のツリーを参照してください。

---

## 運用上の注意 / Tips
- Monitoring は監視用 DB（SQLITE_PATH）を使用し、環境に依存せずデフォルトの sqlite_path を使う設計です。Execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用してデータ分離します。
- process priority / CPU affinity を設定するため psutil を使用します。権限不足で設定できない場合は警告を出してスキップします。
- OpenAI を利用する機能は API のレート制限や不安定時にリトライを行いますが、最終的に失敗した部分はフォールバック（スコア 0.0、処理スキップ）してシステム全体の停止を避ける設計になっています。
- DuckDB 操作時の互換性や executemany の空リスト挙動（DuckDB 0.10 での注意）に配慮してコードが書かれています。
- .env は決して Git にコミットしないでください（秘匿情報を含みます）。

---

必要に応じて README をプロジェクトに合わせてカスタマイズします。追加したいセクション（例えば詳細な API 仕様、設定例、運用チェックリスト、デプロイ手順など）があれば教えてください。