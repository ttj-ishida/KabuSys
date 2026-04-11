# KabuSys

日本株向け自動売買システムのモジュール群。シグナルに基づく発注エンジン、監視コンポーネント、リサーチ／ファクター計算、AI を使ったニュース解析などを含みます。

以下はこのリポジトリの README（日本語）です。イントロダクション、機能一覧、セットアップ、使い方、ディレクトリ構成をまとめています。

注意: この README はソースコード（src/kabusys 以下）を元に作成しています。

---

目次
- プロジェクト概要
- 機能一覧
- 必要要件
- 環境変数（主要）
- セットアップ手順
- 使い方（起動・運用）
- Paper Trading（試験／分離実行）
- 監視ダッシュボード（Streamlit）
- 主要コンポーネントの説明（短評）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買を想定したモジュール群です。以下の主要な関心事を分離して実装しています。
- シグナル→注文発行（ExecutionEngine、OrderManager）
- ブローカーとの同期・リコンシリエーション（Reconciler）
- 発注リスク管理（RiskManager）とポジション大きさ決定（portfolio モジュール）
- 監視（SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager）
- リサーチ（ファクター計算、特徴量解析）
- AI 活用（ニュースセンチメント、レジーム判定。OpenAI API を使用）
- ローカル永続化: SQLite（監視ログ等） + DuckDB（価格データ／リサーチ用）

設計方針のポイント:
- モジュールは可能な限り純粋関数／副作用を限定している（テスト容易性）
- 本番用 DB と Paper Trading は分離（紙上／モックの挙動を保持）
- LLM 呼び出しはリトライやレスポンス検証等、実運用に配慮した実装

---

## 機能一覧

- Execution
  - Signal を読み取り発注（OrderManager、ExecutionEngine）
  - 再起動・クラッシュ後の自動復旧（Reconciler）
  - 注文状態の永続化・同期（OrderRepository / order_record）

- Monitoring
  - システムリソース監視（CPU / Memory / Disk）
  - データ鮮度チェック（DuckDB の prices_daily）
  - 注文滞留・約定価格異常の検出
  - ドローダウン／ポジション上限のアラート
  - Kill switch（flag ファイル）による安全停止シグナル
  - LINE 通知によるアラート配信（AlertManager）

- Portfolio / Risk
  - 候補選定・スコアベース/等分配の重み計算
  - 単元株丸め・リスクベースの株数計算（lot size を考慮）
  - セクター集中上限適用・レジーム乗数

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI
  - ニュース記事を LLM（OpenAI）でセンチメント解析して ai_scores に書き込み
  - マクロニュース + ETF MA200 を合成して市場レジーム判定

- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ (psutil 使用)
  - Monitoring 用 Streamlit ダッシュボード（読み取り専用）

---

## 必要要件

- Python 3.10+（ソースで `| None` などの記法が使われているため）
- ライブラリ（最低限、下記が必要）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード用)
  - openai (AI 機能を使う場合)
  - sqlite3（標準ライブラリ）

pip でのインストール例:
```
pip install duckdb psutil requests streamlit openai
```

（プロジェクト用の requirements.txt / pyproject.toml がある場合はそれを利用してください）

---

## 環境変数（主要）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。主な環境変数:

必須（実行する機能により）:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（research 等で必要）
- KABU_API_PASSWORD — kabu ステーション API パスワード（ブローカー接続時）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）

運用・挙動制御:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant / partial / never / reject）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch 用フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値

.env のパースはシェルライクな記法をサポート（export の有無、クォート、コメントなど）。

例: .env（抜粋）
```
KABUSYS_ENV=paper_trading
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
```

---

## セットアップ手順（ローカル）

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   または最低限:
   ```
   pip install duckdb psutil requests streamlit openai
   ```
4. プロジェクトルートに .env を配置して必要な環境変数を設定
   - 自動読み込みが有効なら .env が自動で読み込まれます
   - テスト時に自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB と SQLite の初期データを用意（prices_daily / raw_financials などが必要な機能を使う場合）。

---

## 使い方（起動例）

プロジェクトはモジュールとして実行できるようにスクリプト（run_execution.py / run_monitoring.py）を用意しています。パッケージを `PYTHONPATH` に通すか、インストールしてから実行してください。

実行例（開発環境でパッケージを直接参照する場合）:
```
python -m kabusys.run_monitoring
python -m kabusys.run_execution
```

run_monitoring:
- SystemMonitor のポーリングループを起動します。
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
- Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使う実装です（監視は本番 DB を参照することを想定）。

run_execution:
- ExecutionEngine を起動して 1 セッション（当日分）を実行します。
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用して paper_trading 用 SQLite（data/paper_trading.db 等）に記録します（本番 DB と厳密に分離）。

例（環境変数を指定して実行）:
```
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

Process priority:
- 起動スクリプトは最初に set_process_priority("high") を呼んでプロセス優先度を上げます（psutil が使われます。権限不足の場合は警告でスキップ）。

Kill flag:
- KillSwitch は監視側で条件を満たすと kill.flag を書き込み、ExecutionEngine 側は起動時/ループ内でこれを検出して安全停止します。
- kill.flag の場所は Settings.kill_flag_path（デフォルト data/kill.flag）で設定可能です。

---

## Paper Trading（試験運用）

- KABUSYS_ENV=paper_trading にすると run_execution は MockBrokerClient を利用（実ブローカーと完全に分離）し、デフォルトで PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録します。
- PAPER_FILL_MODE 環境変数でモックの約定挙動を制御できます（instant / partial / never / reject）。

---

## 監視ダッシュボード（Streamlit）

監視データを可視化する簡易ダッシュボードが用意されています。

起動方法:
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- ダッシュボードは監視 DB を読み取り専用で開きます（URI の mode=ro を利用）。
- MonitoringEngine を実行していないとデータが存在しないため、先に run_monitoring で監視を開始してください。

---

## 主要コンポーネントの説明（短評）

- kabusys.config.Settings
  - .env 自動読み込み（.env / .env.local）
  - 必須環境変数チェック用ユーティリティ
  - DB パス、PID/kill flag パス、Paper 設定などを集約

- kabusys.execution
  - execution_engine.py: Signal を読み発注／push ドレイン／Gate チェック
  - order_manager.py: 注文の状態遷移とブローカー API 呼び出しの二相永続化戦略
  - reconciler.py: 再起動時の注文・ポジション同期

- kabusys.monitoring
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 各種チェックとログ記録
  - monitoring_db.py: SQLite スキーマ初期化・CRUD
  - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py: LINE Push 通知（クールダウン制御）

- kabusys.portfolio
  - portfolio_builder / position_sizing / risk_adjustment: 候補選定・配分・単元丸め・セクター/レジーム調整

- kabusys.research
  - factor_research / feature_exploration: DuckDB を使ったファクター計算・IC 解析等

- kabusys.ai
  - news_nlp.py: raw_news を LLM でセンチメント化して ai_scores に書き込み
  - regime_detector.py: MA200 + LLM マクロセンチメントを用いたレジーム判定

- kabusys.utils.process_priority
  - psutil を使って cross-platform にプロセス優先度や CPU affinity を設定するユーティリティ

---

## ディレクトリ構成

（src/kabusys 以下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定の読み込み・管理
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度・CPU affinity 設定
  - execution/
    - execution_engine.py
    - order_manager.py
    - reconciler.py
    - order_repository.py    — （省略：DB 操作）
    - order_record.py        — 注文状態モデル
    - broker_api.py          — ブローカー API の抽象プロトコル
    - broker_factory.py      — 実装・Mock の切替
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - data/                    — データファイル（例: data/kabusys.duckdb, data/monitoring.db）

---

## 注意点 / 運用メモ

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成し、既存 DB に `peak_value` カラムがなければ追加する処理があります。

- LLM（OpenAI）使用時:
  - API 呼び出しはリトライ・レスポンス検証を実装していますが、API キーが必須です。
  - レスポンスの JSON 抽出やクリッピング等、実運用を想定した頑健化が入っています。

- ログと権限:
  - set_process_priority はプラットフォームや権限によって失敗する可能性があります（警告が出ます）。
  - psutil を使うため、実行環境に psutil のインストールが必要です。

- テスト・デバッグ:
  - 各種外部呼び出し（OpenAI、ブローカー）はテスト時にモックが差し替えられるよう設計されています（private 関数を patch）。

---

問題・拡張案や README に追加したい点があれば教えてください。セットアップ手順や実行例をあなたの環境（OS / Python バージョン / 仮想環境の有無）に合わせて調整したドキュメントを作成できます。