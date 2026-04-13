# KabuSys

日本株向け自動売買システムのコアライブラリ/ユーティリティ群です。  
このリポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI ベースのニュースセンチメント評価などを含んでいます。

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール群から構成されます。

- 実売買向けの ExecutionEngine（broker 経由の発注・リコンシリエーション）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE）
- Paper Trading（疑似ブローカー）と検証ツール
- ポートフォリオ構築（候補選定・重み付け・株数決定・リスク調整）
- リサーチ（ファクター計算 / 将来リターン / IC など）
- AI モジュール（ニュースセンチメント → ai_scores、レジーム判定）
- 管理ユーティリティ（プロセス優先度、Streamlit ダッシュボード 等）

設計の要点：
- DB は SQLite（監視／paper_trading 用）と DuckDB（時系列・ファクタ計算用）を併用
- 環境切替（development / paper_trading / live）を Settings で管理
- Paper Trading は本番 DB と分離（デフォルト: data/paper_trading.db）
- OpenAI を用いる処理は API キーが必要（フェイルセーフでスコア 0 等にフォールバックする実装あり）

---

## 主な機能一覧

- Execution
  - OrderManager：注文作成・送信・同期（クラッシュ耐性を考慮した2相永続化等）
  - Reconciler：起動時の注文・ポジション照合

- Monitoring
  - SystemMonitor：CPU/メモリ/Disk/データ鮮度/プロセス生存を定期ログ化
  - TradeMonitor：滞留注文・約定価格異常を検出
  - RiskMonitor：ドローダウン監視・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件により ExecutionEngine の停止フラグ（data/kill.flag）を書き込み
  - AlertManager：LINE Push による通知（クールダウン管理）

- Portfolio
  - 候補選定、等金額/スコア加重、リスクベース株数決定、セクター上限適用、レジーム乗数

- Research
  - ファクター（Momentum/Volatility/Value）計算（DuckDB + SQL）
  - 特徴量探索（forward returns / IC / summary）

- AI
  - news_nlp.score_news：ニュース記事をまとめて OpenAI に投げ、銘柄別センチメントを ai_scores に書込
  - regime_detector.score_regime：ETF MA とマクロ記事センチメントを合成して market_regime を書込

- ツール
  - tools.paper_verification_report：Paper Trading データから検証レポートを生成
  - monitoring/streamlit_dashboard.py：Streamlit ベースの監視ダッシュボード

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成（推奨: venv / pyenv-virtualenv 等）

   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール

   以下は本リポジトリで参照されている主要な外部依存です。実プロジェクトでは requirements.txt を用意してください。

   ```
   pip install duckdb psutil openai requests streamlit
   ```

   - duckdb: factor / research / ai 用の分析 DB
   - psutil: プロセス/リソース情報取得・優先度設定
   - openai: ニュース NLP / レジーム判定（API 呼出し）
   - requests: LINE API 通信
   - streamlit: 監視ダッシュボード

3. データディレクトリの準備

   デフォルトで使用されるパス（必要に応じて設定で上書き）:

   - monitoring SQLite: data/monitoring.db
   - paper trading SQLite: data/paper_trading.db
   - duckdb: data/kabusys.duckdb
   - pid file: data/execution.pid
   - kill flag: data/kill.flag

   例:

   ```
   mkdir -p data
   ```

4. 環境変数設定（.env をプロジェクトルートに置くか環境に設定）

   必須（実運用・一部機能）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   OpenAI を使う機能:
   - OPENAI_API_KEY

   その他よく使う例（省略可能だが動作に影響）:
   - KABUSYS_ENV = development | paper_trading | live
   - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
   - PAPER_FILL_MODE = instant | partial | never | reject
   - PID_FILE_PATH, KILL_FLAG_PATH
   - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

   注意:
   - Settings モジュールは自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - Settings.require による必須チェックで未設定だと起動時に例外が発生します。

---

## 使い方（主要な実行例）

- 監視ループを起動（本番監視プロセス）

  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。  
  監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

  ```
  python -m kabusys.run_monitoring
  # または
  python src/kabusys/run_monitoring.py
  ```

- ExecutionEngine を起動（実取引 / Paper Trading）

  KABUSYS_ENV によって挙動が変わります:

  - paper_trading: MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録。実ブローカーへは接続しません。
  - live: 実ブローカークライアントを生成して実取引を行います。

  起動例:

  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  # または
  python src/kabusys/run_execution.py
  ```

- Paper Trading 検証レポート生成

  data/paper_trading.db を入力にレポートを標準出力へ出します。

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または指定 DB
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- Streamlit ダッシュボード起動（監視 DB の読み取り専用）

  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI スコアリング / レジーム判定（プログラム呼出し）

  モジュール関数として利用できます。例（簡易）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026, 4, 10), api_key="sk-...")
  score_regime(conn, date(2026, 4, 10), api_key="sk-...")
  ```

  注意: OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定してください。

---

## 設定（環境変数の例）

例 .env（プロジェクトルート）:

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=yyy
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
LOG_LEVEL=INFO
```

主要な設定項目（抜粋）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API 用（必須）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- KABUSYS_ENV — development / paper_trading / live
- PAPER_FILL_MODE — paper_trading 時の約定挙動（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

---

## 注意点 / 運用メモ

- run_monitoring は監視用 DB（monitoring.db）を使用し、init_monitoring_db() が起動時に必要なテーブル作成・マイグレーションを行います。
- run_execution は paper_trading モードで paper_sqlite_path を使い、本番の monitoring.db と分離します（安全な検証が可能）。
- Process priority の設定（set_process_priority("high")）を起動時に行います。権限不足や未対応 OS の場合は警告ログが出てスキップされます。
- KillSwitch は data/kill.flag を生成して ExecutionEngine に停止シグナルを送信します。Execution 側はこのフラグを検出して安全停止する設計になっている想定です。
- LINE アラートは channel token / user id が未設定の場合は送信せずログのみに留めます。
- OpenAI API 呼び出しはリトライ・パース耐性・部分成功時の局所的 DB 更新など、フェイルセーフ設計が施されていますが、API キーの管理・利用料には注意してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                         — 環境変数/設定の読み込み
    - run_monitoring.py                 — SystemMonitor ポーリングループ起動
    - run_execution.py                  — ExecutionEngine 起動（paper/live 切替）
    - utils/
      - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - __init__.py
      - monitoring_db.py                — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他 broker / engine / repository 関連ファイル)
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
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py

---

## 開発 / テストについて

- Settings は自動でプロジェクトルートの .env / .env.local を読み込みますが、テスト時に自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のクエリやファクタ計算は副作用がない純粋関数的な実装を目指しているため、ユニットテストが書きやすくなっています。OpenAI 呼出し部分は外部依存なのでモック化してテストしてください（既に _call_openai_api は patchable になる設計）。

---

## 追加情報・貢献

- バグ報告、機能要望、改善提案は Issue を立ててください。
- 新機能や破壊的変更はプルリクエストでレビューをお願いします。コードスタイルや型注釈の一貫性を保つことを推奨します。

---

README はこのリポジトリの現状実装に基づいて作成しました。実運用時は broker 実装、ExecutionEngine の起動・監視ポリシー、外部 API キーの厳格な管理などを十分に設計・監査してください。