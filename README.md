# KabuSys

日本株向け自動売買システムのコアライブラリ（部分）。このリポジトリには発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ／ファクター計算、LLM ベースのニュース NLP / レジーム判定などの主要コンポーネントが含まれます。

---

## 概要

KabuSys は以下の機能を組み合わせて、データ駆動型の自動売買ワークフローを実現します。

- シグナルに基づく発注（ExecutionEngine）
- ブローカーとの同期・再整合（Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- システム監視・アラート（MonitoringEngine / AlertManager）
- ニュースの LLM センチメント解析（news_nlp）
- 市場レジーム判定（regime_detector）
- ファクター計算・リサーチユーティリティ（research）
- ポートフォリオ構築・ポジションサイジング（portfolio）
- 簡易な Streamlit ダッシュボード（監視用）

設計方針の例: ルックアヘッドバイアスを避ける、DB への冪等な書き込み、フェイルセーフ（API失敗時のフォールバック）など。

---

## 主な機能一覧

- Execution
  - Signal Queue Pull 型の発注エンジン（平常時とドレインループの処理分離）
  - 発注時の 2 相永続化（OrderSent の耐障害性を考慮）
  - 再起動後の自動リコンシリエーション（Order / Position 照合）
- Monitoring
  - system_status / trade_logs / positions / risk_logs / dashboard を持つ SQLite ベースの監視 DB
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在 / データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション上限アラート、kill flag 発行
  - AlertManager: LINE push 通知（クールダウン管理）
  - Streamlit ダッシュボード（監視用 UI）
- Research / Portfolio
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - ポートフォリオ候補選定、等金額・スコア加重、リスクベースの株数決定
  - セクター集中制限、レジーム乗数
- AI
  - news_nlp.score_news: OpenAI を使ったニュースの銘柄別センチメントスコア付与（ai_scores へ書き込み）
  - regime_detector.score_regime: ETF の MA とマクロニュースセンチメントを合成して日次レジーム判定
- ユーティリティ
  - process priority / cpu affinity 設定ユーティリティ（psutil利用）
  - Settings と .env 自動読み込み（プロジェクトルート検出）

---

## 必要要件

- Python 3.10 以上（PEP 604 の型表記などを利用）
- 必要な外部パッケージ（例）
  - duckdb
  - psutil
  - requests
  - streamlit
  - openai
※ 実際に使う機能や環境によって追加パッケージが必要になることがあります。

推奨: 仮想環境を作成して依存をインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests streamlit openai
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンし、ソースコードパスを PYTHONPATH に追加する（開発時）:
   ```bash
   git clone <repo-url>
   cd <repo-root>
   export PYTHONPATH=src:$PYTHONPATH
   ```

2. 仮想環境を作り依存をインストール（上記参照）。

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数優先）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
   - KABU_API_PASSWORD — kabuステーション API 用（必須）
   - OPENAI_API_KEY — OpenAI API を使う場合に必要
   - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
   - LOG_LEVEL — "DEBUG"/"INFO"/...
   - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE — paper_trading 時の fill モード ("instant" | "partial" | "never" | "reject")
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU/MEM/DISK 閾値 など

   .env の例:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. データディレクトリ作成:
   ```bash
   mkdir -p data
   ```

5. DuckDB に必要なテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）を準備してください。これらはリサーチ / AI 機能で参照されます（実データ投入はユーザー側で行います）。

---

## 使い方

実行方法は環境によって異なりますが、開発ルートからモジュールとして起動できます（PYTHONPATH=src を指定）。

- ExecutionEngine（発注エンジン）起動
  - production / live では本番 DB を使い、paper_trading では mock ブローカーと専用 SQLite を使います。
  ```bash
  # src を import できるようにして実行
  PYTHONPATH=src python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を指定すると paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient が使われます。

- MonitoringEngine（監視ループ）起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒、デフォルト 60）。
  ```bash
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```
  - 監視は常に本番用の sqlite_path を使用します（KABUSYS_ENV に依存しません）。

- Streamlit ダッシュボード（監視用）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 関連（プログラムから直接呼び出し）
  - ニューススコアリング（例）
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect('data/kabusys.duckdb')
    n_written = score_news(conn, date(2026, 3, 20), api_key='YOUR_OPENAI_KEY')
    print('written:', n_written)
    ```
  - レジーム判定
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026, 3, 20), api_key='YOUR_OPENAI_KEY')
    ```

注意点:
- ExecutionEngine は起動時に PID ファイルを書き、kill.flag を監視して安全停止を行います。kill.flag は KillSwitch により書き込まれます。
- Paper trading モードではデータベースとブローカーが本番から分離されます（安全設計）。
- OpenAI 呼び出しにはレート制限やネットワーク障害に対するリトライ実装がありますが、APIキーは必須です。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
- KABU_API_PASSWORD: 必須（kabuステーション）
- OPENAI_API_KEY: news_nlp / regime_detector を使う場合に必須
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring で使用）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理、.env 自動読み込みロジック
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor のポーリングスクリプト
  - utils/
    - process_priority.py — psutil を使ったプロセス優先度・CPU affinity 設定
  - execution/
    - execution_engine.py — ExecutionEngine（シグナル処理 / プッシュドレイン等）
    - order_manager.py — Order の作成 / 送信 / 同期 / キャンセルロジック
    - order_repository.py — （DB 層: orders 用）※実装は同リポジトリ内に存在する想定
    - reconciler.py — 再起動時の同期・位置照合
    - reconciler など他関連モジュール
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化と永続化 API
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 複数 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — 簡易 UI
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート等
    - position_sizing.py — 発注株数決定ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等の計算
    - feature_exploration.py — 将来リターン / IC / サマリー等
  - ai/
    - news_nlp.py — ニュースを LLM でスコア化して ai_scores に書き込む
    - regime_detector.py — マクロニュース + MA を合成してレジーム判定
  - data/ (想定)
    - kます: DuckDB/SQLite などのデータファイル（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）

---

## 開発メモ / 注意事項

- Settings はプロジェクトルート（.git または pyproject.toml）を基準に .env を探索して自動読み込みします。CI やテストで自動読み込みを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使ってください。
- DuckDB 側のテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）はリサーチ／AI モジュールで前提として参照されます。実運用では ETL によりこれらを投入してください。
- run_execution を paper_trading モードで動かすときは PAPER_FILL_MODE で約定挙動を制御できます（instant / partial / never / reject）。
- Monitoring は monitoring DB（sqlite）を使って監視データを永続化します。run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は常に本番対象想定）。
- OpenAI を利用する機能は APIキーを環境変数または関数引数で渡す必要があります。API呼び出しはリトライやパース保護済みですが、コストやレート制限に注意してください。

---

## サポート / 拡張案

- ブローカー実装の追加（kabuステーション以外）
- stocks マスタによる lot_size 銘柄別対応
- duckdb の初期データロードスクリプト（ETL）
- テストカバレッジの追加（integration tests / mocks）

---

この README はリポジトリ内の主要モジュールの説明と起動方法を簡潔にまとめたものです。詳細な挙動や各モジュールの内部設計（アルゴリズムの詳細、SQL スキーマ、外部 API の期待仕様など）はソースコード内の docstring を参照してください。