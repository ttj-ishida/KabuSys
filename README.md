# KabuSys

日本株向けの自動売買 / リサーチ / 監視ツール群のコアライブラリ。  
このリポジトリは、ポートフォリオ構築、ポジションサイジング、ファクター計算、LLM を使ったニュースセンチメント評価、市場レジーム判定、監視・アラート機能、発注エンジンの主要ロジックを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を主目的とするモジュール群の集合です。

- ファクター計算（モメンタム／バリュー／ボラティリティ等）とリサーチ支援
- ポートフォリオ候補選定・重み計算・株数決定（単元丸め、リスク制約含む）
- ニュースを LLM（OpenAI）で解析して銘柄ごとのセンチメントを算出し DB に保存
- マクロ + ETF の MA を組み合わせた市場レジーム判定（LLM を利用）
- 実行エンジン（ExecutionEngine）による発注ワークフロー（再コンシリエーションや Kill Switch を含む）
- 監視（Monitoring）モジュール：システム状態、注文滞留、リスクイベントの永続化・アラート送信（LINE）
- DuckDB / SQLite によるデータ永続化を想定

設計方針として、本番の取引 API への直接呼び出しを行う箇所（broker client 等）と、純粋関数／DB 層を明確に分離しています。LLM 呼び出しは外部 API（OpenAI）を用いますが、失敗時はフォールバックする構成になっています。

---

## 主な機能一覧

- portfolio
  - select_candidates（スコア順で候補選定）
  - calc_equal_weights / calc_score_weights（配分重み計算）
  - calc_position_sizes（株数決定、aggregate cap、lot 単位で丸め）
  - apply_sector_cap（セクター集中制限）
  - calc_regime_multiplier（レジームに応じた投下資金乗数）
- research
  - calc_momentum / calc_volatility / calc_value（DuckDB を用いたファクター算出）
  - calc_forward_returns / calc_ic / factor_summary（特徴量探索・IC 計算）
- ai
  - score_news（raw_news を LLM でセンチメント判定して ai_scores に書き込み）
  - score_regime（ETF + マクロニュースで市場レジーム判定）
- monitoring
  - init_monitoring_db / MonitoringDB（SQLite への永続化）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - AlertManager（LINE Push）
  - streamlit_dashboard（簡易ダッシュボード）
- execution
  - ExecutionEngine（Signal Queue ベースの発注エンジン）
  - OrderManager / Reconciler（注文状態管理・起動時リコンシリエーション）
  - broker_api（API レイヤーの型・Protocol・例外定義）

---

## 前提条件 / インストール

推奨 Python バージョン: 3.10+

主な依存パッケージ（抜粋）:
- duckdb
- openai (OpenAI Python SDK)
- requests
- psutil
- streamlit

例（仮の requirements.txt がある場合）:
```bash
python -m pip install -r requirements.txt
```

もしくは個別インストール:
```bash
python -m pip install duckdb openai requests psutil streamlit
```

開発環境として編集する場合:
```bash
python -m pip install -e .
```
（セットアップファイルがある場合）

---

## 環境変数 / 設定

設定は環境変数または .env / .env.local（プロジェクトルート）から読み込まれます。プロジェクトルートは `.git` または `pyproject.toml` の存在から自動検出されます。自動ロードを禁止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API リフレッシュトークン
- KABU_API_PASSWORD（必須）: kabu ステーション API 用パスワード
- KABU_API_BASE_URL（任意）: デフォルト `http://localhost:18080/kabusapi`
- OPENAI_API_KEY（LLM 呼び出し用）: OpenAI API キー
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意）: 監視アラート用
- DUCKDB_PATH（任意）: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH（任意）: 監視用 SQLite（デフォルト `data/monitoring.db`）
- PAPER_FILL_MODE（任意）: paper trading の挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH（任意）
- PID_FILE_PATH（任意）: デフォルト `data/execution.pid`
- KILL_FLAG_PATH（任意）: デフォルト `data/kill.flag`
- KILL_FLAG_CLEAR_ON_START（0/1）: 起動時に kill.flag を自動クリアするか
- KABUSYS_ENV（development|paper_trading|live）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL）

設定は `kabusys.config.settings` からアクセスできます（例: settings.jquants_refresh_token）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 環境を準備（仮想環境推奨）
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成（.env.example を参照して必要項目を設定）
5. DuckDB / SQLite の初期化（データスキーマ作成等は別途スクリプトを利用）
   - 監視 DB の初期化例（SQLite conn を作って実行）:
     ```python
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db

     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()
     ```

---

## 使い方（代表的なユースケース）

- 設定を読み込む（自動ロード済みが通常）:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB を利用したファクター計算（例: モメンタム）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  # records: [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
  ```

- ポートフォリオ候補選び＆重み計算:
  ```python
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_equal_weights

  buy_signals = [
      {"code": "1234", "signal_rank": 1, "score": 0.8},
      {"code": "2345", "signal_rank": 2, "score": 0.6},
      ...
  ]
  candidates = select_candidates(buy_signals, max_positions=5)
  weights = calc_score_weights(candidates)
  ```

- 株数決定（position sizing）:
  ```python
  from kabusys.portfolio import calc_position_sizes

  sizes = calc_position_sizes(
      weights=weights,
      candidates=candidates,
      portfolio_value=10_000_000,
      available_cash=7_000_000,
      current_positions={},
      open_prices={"1234": 1500.0, "2345": 800.0},
      allocation_method="score",
      lot_size=100,
  )
  # sizes: {"1234": 100, ...} など
  ```

- ニュースセンチメントのスコアリング（ai.score_news）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # 必要: OPENAI_API_KEY を環境変数か引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"wrote {written} ai_scores rows")
  ```

- 市場レジーム判定（ai.score_regime）:
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監視ダッシュボード起動（Streamlit）:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ExecutionEngine（本番的な実行）は多数の依存 (broker, order_repo, risk_manager, order_manager, duckdb_conn, reconciler) を必要とします。テスト時は各依存をモックして run_session / run_once を呼んでください。

---

## 注意点 / 実運用メモ

- OpenAI を使う機能は API コストと過剰呼び出しに注意してください。score_news/score_regime はリトライやフェイルセーフを入れていますが、API キーや使用量は運用で管理してください。
- .env の自動読み込みはプロジェクトルートの検出に依存します。パッケージ化・配布後など CWD が変わる状況でも動作するよう設計されていますが、必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を使って手動で読み込むこともできます。
- ExecutionEngine は kill.flag（設定でパス指定）を用いた安全停止ロジックを持ちます。運用時は PID ファイル / flag ファイルの扱いに注意してください。
- DuckDB に期待されるテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets 等）は外部処理で投入される前提です。データスキーマはモジュール内 SQL から追えます。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP / OpenAI スコアリング
  - regime_detector.py — 市場レジーム判定（ETF + マクロ）
- portfolio/
  - __init__.py
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクター上限・レジーム乗数
  - position_sizing.py — 株数決定・aggregate cap
- research/
  - __init__.py
  - factor_research.py — モメンタム/ボラ/バリュー等
  - feature_exploration.py — forward returns, IC, summary
- monitoring/
  - __init__.py
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py — データモデル・Protocol・例外
  - order_manager.py
  - order_repository.py (参照されるがここでは省略)
  - order_record.py (参照されるがここでは省略)
  - reconciler.py
  - execution_engine.py
  - risk_manager.py (参照されるがここでは省略)
- monitoring/ (上記)
- research/ (上記)
- data/ (別途実装されるユーティリティ群、例: pipeline, stats — 一部モジュールで参照)

（この README はリポジトリ内の doc ファイルや PortfolioConstruction.md / StrategyModel.md 等の補助ドキュメントと合わせて読むと理解が深まります）

---

## 貢献 / 開発メモ

- モジュールは純粋関数部分（リサーチ・ポートフォリオ計算など）と副作用を伴う部分（DB 書込み、API 呼び出し、ファイル操作）で明確に分かれています。単体テストは純粋関数に集中させ、外部依存はモックで差し替えてください。
- OpenAI 呼び出し部分はテスト用に `_call_openai_api` を patch して差し替えることを想定しています。
- DuckDB の SQL クエリは日付範囲の指定でルックアヘッドを避ける実装になっています（実運用でのデータ投入手順に注意）。

---

README に含めてほしい追加情報（例: 実際の起動スクリプト、docker 構成、CI/CD 設定など）があれば教えてください。必要に応じてサンプル .env.example も作成します。