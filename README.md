# KabuSys

日本株向け自動売買システムの参照実装です。  
このリポジトリは、売買実行エンジン、監視／アラート、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含むシステムです。

- シグナルに基づく注文生成とブローカーへの発注（Execution Engine）
- 注文・約定・ポジションの永続化とリコンシリエーション
- システム状態／注文状況／リスクの監視（Monitoring）
- ポートフォリオ構築（候補選定・配分・株数計算）
- リサーチ用ファクター計算・特徴量解析（DuckDB を用いたローカル解析）
- ニュース記事を LLM(OpenAI) で解析して銘柄ごとのスコアを計算
- Paper Trading 用の検証・レポート出力ツール
- Streamlit による監視ダッシュボード

設計方針の一部：
- 計算系（ポートフォリオ構築・リサーチ）は純粋関数で DB に依存しない箇所と、DuckDB を参照する箇所に分離。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離された専用 SQLite を使用。
- 環境変数は .env / .env.local を自動読み込み（必要に応じて無効化可）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine による注文セッション実行（ブローカー抽象化）
  - Reconciler による起動時の自動復旧（Order / Position 照合）
  - OrderManager / OrderRepository による状態遷移と永続化

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文（stale orders）、約定異常価格チェック
  - RiskMonitor: ドローダウン / ポジション上限の監視とリスクログ
  - KillSwitch: 条件を満たしたらファイルで ExecutionEngine に停止シグナルを送信
  - AlertManager: LINE PUSH によるアラート通知（クールダウン管理）
  - streamlit_dashboard: 監視ダッシュボード（read-only 接続）

- Portfolio construction
  - 候補選定、等重/スコア重み付け、リスク調整（セクターキャップ、レジーム乗数）、株数計算（単元丸め、aggregate cap）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等

- AI
  - news_nlp: raw_news を LLM に投げて銘柄ごとの ai_score を生成・保存
  - regime_detector: ETF（1321）MA とマクロニュースの LLM 評価を合成して市場レジーム判定

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・P95 レイテンシ等）

---

## 前提・依存関係

推奨 Python バージョン: 3.10+（型注釈や新しい標準ライブラリ機能を利用しているため）  

主な依存パッケージ（requirements.txt を用意する場合の例）:
- duckdb
- psutil
- requests
- openai
- streamlit

標準ライブラリ: sqlite3, logging, argparse, datetime, pathlib など

（プロジェクトに合わせて仮想環境を作成し、上記パッケージをインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主なもの）

Settings クラスで定義されている主要な環境変数とデフォルト:

- KABUSYS_ENV: 起動モード（development, paper_trading, live）デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）デフォルト: INFO
- SQLITE_PATH: 監視用 SQLite（monitoring）デフォルト: data/monitoring.db
- DUCKDB_PATH: DuckDB パス（分析）デフォルト: data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading DB）デフォルト: data/paper_trading.db
- PAPER_FILL_MODE: paper trading の約定モード（instant|partial|never|reject）デフォルト: instant
- PID_FILE_PATH: ExecutionEngine の pid ファイルデフォルト: data/execution.pid
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイルデフォルト: data/kill.flag
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API / 認証用（必須設定となるものあり）
- OPENAI_API_KEY: OpenAI を使う場合は必須（AI モジュール）

.env / .env.local の自動読み込み:
- プロジェクトルートに .env, .env.local があれば自動で読み込みます（OS 環境変数が優先されます）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境の作成・有効化
   - Linux / macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```

4. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を作成して必要なキーを設定してください。
   - 例 (.env):
     ```
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     ```
   - 自動読み込みを無効にしたい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
5. データディレクトリ作成
   ```bash
   mkdir -p data
   ```
   （各スクリプト起動時に必要なファイルを作成・更新します）

---

## 使い方（よく使うコマンド）

- ExecutionEngine を起動（本番/開発）
  ```bash
  # 標準モード（KABUSYS_ENV に従う）
  python -m kabusys.run_execution

  # Paper Trading モードの例
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動前に data/stop_requested.flag があれば起動しません（停止フラグ）。

- Monitoring (SystemMonitor の単独起動)
  ```bash
  # ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能、デフォルト60秒
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - Monitoring は KABUSYS_ENV に関係なく、本番 sqlite_path（Settings.sqlite_path）を使用します。

- Streamlit ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only で SQLite に接続し、Overview / Positions / Orders / System タブを提供します。

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report

  # 期間指定や DB パス指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI 系（ニューススコア / レジーム判定）
  - 必須: OPENAI_API_KEY を環境変数か引数で指定
  - 呼び出しは各モジュールの公開関数（kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）を使用

---

## 重要な挙動・運用メモ

- モニタリング関連（run_monitoring）は常に Settings.sqlite_path（監視 DB）を使用します。環境にかかわらず同じファイルを参照します。
- ExecutionEngine 起動時は data/execution.pid に PID を書き、PID が存在するかでプロセス生存を判断します。stale PID 検出時は PID ファイルを削除して警告を記録します。
- KillSwitch は条件を満たすと KILL_FLAG_PATH（デフォルト data/kill.flag）に理由を書き込んで ExecutionEngine に停止シグナルを与えます。冪等性あり（既存ファイルがあれば上書きしない）。
- Paper Trading は本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API 呼び出しでは 429 / ネットワークエラー / タイムアウト / 5xx に対して指数バックオフのリトライを実装しています。個別の API 呼び出し関数はテスト時に差し替え可能な設計です。
- process priority 設定: 起動時に set_process_priority("high") を行いますが、権限等で失敗する場合はログに警告を出してスキップします。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定 / .env 自動読み込み
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (存在する想定)
    - broker_factory.py (存在する想定)
    - broker_api.py (存在する想定)
    - order_record.py (存在する想定)
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
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
  - utils/
    - process_priority.py
  - data/ (実行時に利用されるファイル群: DB ファイル、pid/flag ファイル 等)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper trading 用)

（上記はコードベースに存在する主なモジュールで、詳細なサブモジュールやファイルは実装に依存します）

---

## 開発・拡張のヒント

- DuckDB を使ったリサーチ関数は純粋に SQL + Python の組合せで完結しており、データテーブル（prices_daily / raw_financials / raw_news 等）を準備すればローカルで高速に解析できます。
- AI モジュールは OpenAI SDK に依存しますが、各 API 呼び出しラッパーはテスト時に差し替え可能に実装してあり、モック化しやすい設計です（ユニットテストの容易化）。
- position_sizing 等は lot_size を銘柄別に拡張するなどの余地があります。コメントにも将来の拡張ポイントが記載されています。

---

## ライセンス・注意事項

- 実運用で使用する場合は法規制、取引所のルール、証券会社 API の利用規約を必ず遵守してください。
- 実運用時の資金リスクや API 認証情報の管理（安全なシークレット管理）には十分ご注意ください。
- 本リポジトリは教育目的の参照実装であり、そのまま実運用することは推奨しません。

---

README に不足している点や、実際に使う環境（例: broker 実装、ExecutionEngine の詳細、Dockerfile、CI 設定 など）について追記が必要であれば教えてください。必要に応じてサンプル .env.example や requirements.txt、起動例のユースケース（デモフロー）も作成します。