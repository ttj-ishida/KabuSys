# KabuSys — README (日本語)

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。戦略の研究、ポートフォリオ構築、発注・実行、監視、AI ベースのニュース評価などの主要コンポーネントを含みます。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動例）
- 環境変数 / 設定の説明
- 運用上の注意
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けのモジュール群です。主な責務は以下の通りです。

- 市場データ（DuckDB）を用いたファクター計算・研究機能
- ポートフォリオ構築（候補選定、重み付け、単位株丸め、リスク調整）
- 発注・Execution Engine（ブローカーラッパー、OrderManager、Reconciler 等）
- 監視機能（システム状態、注文滞留、ドローダウン監視、アラート）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

コードは (ほとんど) ピュア Python で書かれており、外部ライブラリ（duckdb, psutil, openai, requests, streamlit 等）に依存します。

---

## 主な機能一覧

- portfolio
  - 銘柄候補選定（select_candidates）
  - 等金額・スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- research
  - モメンタム / ボラティリティ / バリュー系ファクター計算（DuckDB 利用）
  - 将来リターン計算、IC 計算、統計サマリー
- execution
  - ExecutionEngine（起動・セッション管理）
  - OrderManager、OrderRepository、Reconciler
  - RiskManager（発注前の制約チェック等）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
  - MonitoringEngine（ポーリング、Kill Switch 判定、アラート送信）
  - AlertManager（LINE Push による通知）
  - Streamlit ベースの監視ダッシュボード
- ai
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメント付与（ai_scores テーブルへ書込）
  - regime_detector: ETF + マクロニュースを用いた市場レジーム判定（market_regime テーブルへ書込）
- tools
  - paper_verification_report: Paper Trading DB を解析して検証レポートを出力

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows (PowerShell 等)
   ```

3. 依存パッケージをインストール  
   （requirements.txt がない場合は下記を参考に必要なパッケージをインストールしてください）
   ```
   pip install duckdb psutil openai requests streamlit
   ```

   補足（開発用）:
   - duckdb: データ解析・ファクター計算用
   - psutil: プロセス・システム情報取得、優先度設定
   - openai: ニュース NLP / レジーム判定（OpenAI API）
   - requests: LINE API 呼び出し
   - streamlit: 監視ダッシュボード

4. プロジェクトルートに `.env` / `.env.local` を置く（任意）  
   - `.env` の自動読み込みは既定で有効。CWD ではなくソースツリーからプロジェクトルートを検出して読み込みます。
   - 自動読み込みを無効化する場合: `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 起動環境
  - 値: `development`（デフォルト） / `paper_trading` / `live`
  - `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録されます（実口座と分離）。
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合に必須）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（`instant` / `partial` / `never` / `reject`、デフォルト: `instant`）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: `data/monitoring.db`）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: `data/paper_trading.db`）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: `data/execution.pid`）
- KILL_FLAG_PATH: Kill Switch が書き込むフラグ（デフォルト: `data/kill.flag`）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）。無効値は無視されデフォルトにフォールバック。

環境変数は `.env` / `.env.local` に定義可能（`.env.local` は `.env` 上書き）。既に OS 環境変数にあるキーは上書きされません（上書きしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD 等を利用）。

---

## 使い方（起動例）

※ 下記はプロジェクトルートから実行する想定です。

### 1) 監視ループを起動（Monitoring）
監視専用のプロセスを起動します。MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（デフォルト 60 秒）。

```
python -m kabusys.run_monitoring
```

- 監視は設定にかかわらず本番用の sqlite_path（`SQLITE_PATH`）に記録します。
- 停止方法:
  - プロセスに Ctrl+C（KeyboardInterrupt）
  - またはプロジェクトルート `data/stop_requested.flag` を作成するとループが検知して終了します。

### 2) ExecutionEngine を起動（発注エンジン）
ExecutionEngine を起動します。KABUSYS_ENV に `paper_trading` を設定すると MockBrokerClient が使われ、paper_trading 用の独立した SQLite に記録されます。

```
# 本番（live / development）
python -m kabusys.run_execution

# Paper trading の例
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

- 起動時、PID ファイル（デフォルト `data/execution.pid`）を作成します。
- ExecutionEngine 側の停止:
  - `data/stop_requested.flag` を作成 → 監視プロセスと同様に安全に停止します。
  - Kill Switch（監視側）が `data/kill.flag` を書き込むと安全に停止シグナルとなります。
- 起動前に既存の kill flag をクリアしたい場合は KillSwitch の設定（`kill_flag_clear_on_start`）や手動で `data/kill.flag` を削除してください。

### 3) Streamlit ダッシュボード（監視 UI）
ローカルで監視 DB を参照するダッシュボードを起動します。

```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- DB を読み取り専用で開きます。MonitoringEngine が書き込んでいる状態で参照してください。

### 4) Paper Trading 検証レポート
Paper Trading DB（デフォルト: `data/paper_trading.db`）の集計レポートを出力します。

```
# デフォルト DB を使う
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パスを直接指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- レポートでは稼働率（uptime）、注文成功率、送信率、P95 レイテンシ等を評価し PASS/FAIL を出力します。

### 5) AI 機能（ニューススコア / レジーム判定）
news_nlp.score_news / regime_detector.score_regime は OpenAI API を使用します。API キーは OPENAI_API_KEY 環境変数か関数引数で指定してください。実行例（スクリプトから呼び出す想定）:

- 注意: OpenAI API キーと使用量に注意。リトライやエラーハンドリングは実装されていますがコストが発生します。

---

## 運用上の注意

- Paper Trading と Live は DB が分離されるよう設計されています（`KABUSYS_ENV=paper_trading` の場合、`PAPER_TRADING_SQLITE_PATH` を使用）。
- 監視処理はモジュール単位で個別例外を吸収して継続するようになっています（可能な限りフェイルセーフ）。
- Process priority（優先度）は起動時に `High` に設定されます。権限不足等で設定できない場合は警告が出ます。
- kill.flag / stop_requested.flag の運用ルールを定めて安全に停止できるようにしてください。`kill.flag` は監視側が自動で生成するため、エンジン起動時に `KILL_FLAG_CLEAR_ON_START` の挙動を考慮してください。
- 外部 API（kabu/API、OpenAI 等）に対するレート制限やエラーを考慮し、運用監視とログ収集を強化してください。

---

## ディレクトリ構成

以下は主要なソース配置の抜粋です（src/kabusys 配下）。

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数読み込み・Settings
    - run_monitoring.py        # SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
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
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - (ExecutionEngine, order_manager, reconciler, order_repository 等 — 一部ファイルは抜粋)
    - utils/
      - __init__.py
      - process_priority.py

- data/  (ランタイム生成 / デフォルト DB パス)
  - monitoring.db (デフォルト SQLite)
  - paper_trading.db (paper trading 用)
  - kabusys.duckdb (DuckDB)
  - execution.pid, stop_requested.flag, kill.flag などのフラグ / PID ファイル

---

以上が README の要点です。追加で README に記載したい詳細（例えば各 API の仕様、DB スキーマの詳細、テスト手順、CI 設定、サンプル .env.example のテンプレートなど）があれば指示してください。必要に応じて README を拡張します。