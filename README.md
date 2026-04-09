# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリです。  
ポートフォリオ構築、ポジションサイジング、ファクター計算、ニュースのLLMによるセンチメント評価、実行エンジン（発注・再同期・監視）などをモジュール化しています。

---

## プロジェクト概要

KabuSys は以下の用途を想定した Python モジュール群です。

- 定量ファクターの計算（Momentum / Value / Volatility / Liquidity）
- ポートフォリオ候補選定・配分計算・ポジションサイジング
- セクターキャップ・市場レジームによるリスク調整
- ニュース記事の LLM（OpenAI）を用いたセンチメントスコア付与
- 実行系（ExecutionEngine）による Signal → 発注、Push ドレイン、kill-switch
- 起動時リコンシリエーション（注文状態の突合せ）
- 監視（System / Trade / Risk）ログの永続化と Streamlit ダッシュボード

設計方針として、DBアクセス・API 呼び出し・純粋関数ロジックを分離しており、DuckDB／SQLite／外部 API（OpenAI / kabuステーション 等）を必要に応じて組み合わせられるようになっています。

---

## 主な機能一覧

- 環境設定管理（.env 自動読み込み / Settings）
- Portfolio:
  - 候補選定（select_candidates）
  - 等金額／スコア加重の重み計算（calc_equal_weights, calc_score_weights）
  - ポジションサイズ算出（calc_position_sizes） — risk_based / equal / score
  - セクター上限適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
- Research:
  - Momentum / Volatility / Value ファクター計算（DuckDB 使用）
  - 将来リターン計算、IC 計測、統計サマリ（feature_exploration）
- AI:
  - ニュースのセンチメントスコア付与（news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI API の呼び出しは再試行・バリデーション・フェイルセーフ設計
- Execution:
  - OrderManager（発注フローの永続化・状態遷移）
  - ExecutionEngine（Signal → 発注ループ、WebSocket push ドレイン、kill）
  - Reconciler（起動時の注文 / ポジション同期）
  - Broker API 抽象（Protocol）に依存する設計
- Monitoring:
  - SQLite ベースの永続層（MonitoringDB, init_monitoring_db）
  - System / Trade / Risk Monitor、AlertManager（LINE push）
  - Streamlit ダッシュボード（監視表示）

---

## 必要条件（概略）

- Python 3.10 以上（型注釈に `|` を使用しているため）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボードを使う場合)
- SQLite は標準ライブラリで使用
- OpenAI を利用する場合は API キーが必要

pip の requirements.txt が無い場合は例として以下をインストールしてください:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
```

---

## セットアップ手順（開発 / 実行の最小フロー）

1. リポジトリをクローンする
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作る / 有効化して依存ライブラリをインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # ある場合
   # requirements.txt がなければ:
   pip install duckdb openai requests psutil streamlit
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要な環境変数の例（.env）:
     ```
     OPENAI_API_KEY=sk-...
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_FILL_MODE=instant
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - `Settings` クラスで参照される環境変数を README 前半で必ず確認してください（未指定の必須変数は起動時に ValueError を投げます）。

4. 監視 DB 初期化（Monitoring）
   ```python
   from pathlib import Path
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   Path("data").mkdir(parents=True, exist_ok=True)
   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

5. DuckDB とテーブル
   - research / ai モジュールは DuckDB 上の特定テーブル（例: prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets など）を参照します。運用時はこれらのテーブルを適切に準備してください。
   - 開発・テストではモックや小さな DuckDB ファイルを用意して動作確認することを推奨します。

---

## 使い方（代表的な例）

- 設定を読み込む（Settings）
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  ```

- ポートフォリオ候補選定・重み計算
  ```python
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_equal_weights

  buy_signals = [{"code":"1234","score":1.2,"signal_rank":1}, {"code":"2345","score":0.5,"signal_rank":2}]
  candidates = select_candidates(buy_signals, max_positions=5)
  weights = calc_score_weights(candidates)  # or calc_equal_weights(candidates)
  ```

- ポジションサイズ計算（risk_based 例）
  ```python
  from kabusys.portfolio import calc_position_sizes
  sizes = calc_position_sizes(weights, candidates, portfolio_value=10_000_000, available_cash=1_000_000, current_positions={}, open_prices={"1234":1000.0})
  ```

- ファクター計算（DuckDB 接続を渡す）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  ```

- ニュース NLP スコア付与（OpenAI API キー必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, date(2026,3,20), api_key="sk-...")
  print(f"wrote {written} scores")
  ```

- 市場レジーム判定（AI を使う。duckdb に prices_daily/raw_news が必要）
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026,3,20), api_key="sk-...")
  ```

- 監視ダッシュボード起動（Streamlit）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- MonitoringEngine (ポーリング監視) の例
  ```python
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine
  # 必要なオブジェクト（DB コネクションや OrderRepository など）を作成してインスタンス化
  engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(...), alert_manager=AlertManager(...))
  engine.run()  # KeyboardInterrupt で停止
  ```

- ExecutionEngine の例（実運用は Broker 実装などが必要）
  ```python
  from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
  # broker, repo, risk_manager, order_manager, duckdb_conn を用意
  cfg = EngineConfig(target_date=date(2026,3,20))
  engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, cfg)
  engine.run_session()
  ```

---

## 自動 .env 読み込みの挙動

- モジュール起動時（kabusys.config）にプロジェクトルート（.git または pyproject.toml を親階層に持つディレクトリ）を基に `.env` / `.env.local` を自動読み込みします。
- 読み込み順序: OS 環境変数（優先） > .env > .env.local（.env.local が .env 上書き）
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

.env のパースはクォート・エスケープ、インラインコメントなどに対応しています。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要なモジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
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
    - broker_api.py
    - order_manager.py
    - reconciler.py
    - execution_engine.py
    - ...（注文レポジトリ・レコード等は別ファイルに実装）
  - その他: data/（デフォルト DB パス等）、tests/（存在する場合）

（実際のツリーはリポジトリの内容に依存します。上記はソースから抽出した代表的なファイル一覧です。）

---

## 注意点 / 運用上のヒント

- DuckDB 上の必要なテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets 等）は事前に準備してください。research / ai 機能はこれらを参照します。
- OpenAI を使う機能は API キーが未設定だと例外を投げます。フェイルセーフとして一部モジュールは API 失敗を無視して継続（macro_sentiment=0 など）しますが、想定動作を確認してください。
- ExecutionEngine は PID ファイル・kill.flag による制御を行います。運用環境ではこれらファイルの扱いに注意してください（Settings でパス指定可）。
- Logging レベルは環境変数 `LOG_LEVEL` で設定（INFO / DEBUG 等）。環境 `KABUSYS_ENV` は development / paper_trading / live のいずれかでバリデーションされます。
- 単体テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと .env の影響を受けずにテストできます。

---

## 貢献 / 拡張

- BrokerAPIProtocol を実装することで任意のブローカー（kabuステーション等）を接続できます。
- position_sizing の lot_size を銘柄別にする、コスト見積りの強化、ファクターパイプラインの追加など拡張余地が多くあります。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開ける URI を受け取るため、運用中の DB を安全に可視化できます。

---

もし README に追加したい「実際の DB スキーマ定義」や「テスト実行方法」「CI 設定例」などあれば教えてください。必要に応じてサンプル .env.example や duckdb schema のテンプレートも作成できます。