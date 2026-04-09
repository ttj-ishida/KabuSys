# KabuSys

日本株アルゴリズム売買プラットフォームのコンポーネント群（ライブラリ/ツール群）。  
ポートフォリオ構築、シグナル実行エンジン、監視・アラート、リサーチ・ファクター計算、LLM を用いたニュース NLP 等の機能を提供します。

> 注意: これはプロジェクトコードの README です。実際の運用ではテスト・シミュレーション・十分なガード（資金管理・ kill-switch 等）を行ってください。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- ポートフォリオ構築（候補選定、重み計算、リスク補正、ポジションサイジング）
- シグナルを受けてブローカーへ発注する ExecutionEngine（再起動時のリコンシリエーション含む）
- ブローカー API 抽象（Protocol / データモデル / 例外）
- リサーチ（ファクター計算、将来リターン・IC 計算、統計サマリー）
- AI（ニュースのセンチメント評価、マクロニュースから市場レジーム判定）
- 監視（システム稼働状況・注文滞留・価格異常の監視、LINE への通知、Streamlit ダッシュボード）
- 設定管理（.env 自動読み込み / 環境変数）

設計上、主要な計算ロジックは純粋関数（副作用なし）または DB 接続を受ける形で実装されており、本番 API 呼び出し部分（ブローカー / OpenAI 等）は抽象化されています。

---

## 主な機能一覧

- portfolio
  - select_candidates: BUY シグナルをスコア順に選択
  - calc_equal_weights / calc_score_weights: 重み計算
  - calc_position_sizes: 各銘柄の発注株数決定（リスクベース / weight ベース）
  - apply_sector_cap: セクター集中制限適用
  - calc_regime_multiplier: 市場レジームに応じた投下資金乗数
- research
  - calc_momentum / calc_value / calc_volatility: DuckDB の prices_daily / raw_financials を使ったファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank: ファクター有効性検証ユーティリティ
- ai
  - score_news: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に書き込む
  - score_regime: ETF（1321）MA 乖離とマクロニュースセンチメントを合成し market_regime を更新
- execution
  - ExecutionEngine: シグナル読み込み→Gate チェック→発注→WebSocket ドレイン等の実行フロー
  - OrderManager / Reconciler: 注文状態管理、再起動後の突合
  - broker_api: ブローカー用データモデルと Protocol（差し替え実装可能）
- monitoring
  - MonitoringDB: SQLite ベースの永続化レイヤ
  - SystemMonitor / TradeMonitor / RiskMonitor: 定期チェック／アラート記録
  - AlertManager: LINE Push での通知（クールダウン付）
  - KillSwitch: フラグファイルによる停止シグナル
  - Streamlit ダッシュボード（データ閲覧用）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成してアクティベート（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール  
   コードベースから依存ライブラリ（例）:
   - duckdb
   - openai
   - requests
   - psutil
   - streamlit

   インストール例:
   ```
   pip install duckdb openai requests psutil streamlit
   ```

   （プロジェクトに requirements.txt / extras があればそちらを使用してください）

4. データディレクトリの作成
   ```
   mkdir -p data
   ```

5. 環境変数の設定  
   ルートプロジェクトに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1で無効化可）。

   主要な環境変数（一部）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な機能のみ）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - KABU_API_BASE_URL: kabu API エンドポイント（デフォルト: http://localhost:18080/kabusapi）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時必須）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: Monitoring DB（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等（Paper trading 用設定）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / KABUSYS_ENV / LOG_LEVEL

   例（.env）:
   ```
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=passwd
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

6. Monitoring DB 初期化（SQLite 接続を作って init を呼ぶ）
   Python スクリプト例:
   ```py
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

---

## 使い方（代表例）

- DuckDB を使ったファクター計算（calc_momentum）
  ```py
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

- ニュース NLP によるスコア生成（OpenAI API キーが必要）
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
  ```

- 市場レジーム判定（regime_detector）
  ```py
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")
  ```

- ポートフォリオ構築の流れ（候補選定 → 重み → 発注株数）
  ```py
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

  buy_signals = [
      {"code": "7203", "signal_rank": 1, "score": 1.2},
      {"code": "6758", "signal_rank": 2, "score": 0.8},
  ]
  candidates = select_candidates(buy_signals, max_positions=5)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value=10_000_000, available_cash=1_000_000, current_positions={}, open_prices={"7203": 2000, "6758": 1500})
  ```

- Streamlit ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ExecutionEngine（実運用向け、ブローカー実装が必要）
  ExecutionEngine を動かすにはブローカー実装（BrokerAPIProtocol 準拠）、OrderRepository（SQLite）やリスクマネージャ等を組み合わせてインスタンス化してください。  
  実行は `ExecutionEngine.run_session()` を呼びます。コード内のコメントでフローが説明されています。

---

## 自動 .env ロードの挙動

- 実行時にプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を探し、見つかればルートの `.env` を読み込み、次に `.env.local` を上書き読み込みします。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェルライク（export プレフィックス、クォート、インラインコメントなど）に対応しています。

---

## ディレクトリ構成（主なファイル）

（ルート: src/kabusys 以下）

- config.py
- __init__.py
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
  - risk_monitor.py
  - system_monitor.py
  - trade_monitor.py
  - alert_manager.py
  - kill_switch.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py
  - order_manager.py
  - order_repository.py (参照あり、実装想定)
  - order_record.py (参照あり、実装想定)
  - reconciler.py
  - execution_engine.py
  - risk_manager.py (参照あり、実装想定)
- monitoring データベース用スキーマ定義は monitoring_db.init_monitoring_db で作成

（実際のリポジトリには上記以外にも data / strategy / execution 関連ファイルやマスタ・ユーティリティが含まれる想定です）

---

## 注意事項・運用上のヒント

- OpenAI を使う機能（ai.news_nlp, ai.regime_detector）は API キーが必須です。API 呼び出しはネットワークエラーやレート制限に対してリトライを行う設計ですが、必ず費用・レート管理を行ってください。
- ExecutionEngine / OrderManager 周りは発注の「正しさ」と「クラッシュ時の頑健性」を重視しており、DB 保存・2相コミットに留意しています。実ブローカー接続前にローカルテスト（モック）で動作確認を行ってください。
- monitoring は LINE 通知や kill.flag を用いた自動停止など運用向けの仕掛けがあります。運用時は KILL_FLAG の扱いや PID ファイル連携を適切に設定してください。
- DuckDB 内のテーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime など）はリサーチ・AI モジュールが前提としています。必要なスキーマ・データの準備が必要です。

---

README に記載のない詳細や、実際のブローカー／DB スキーマ等についてはソースコード内の docstring とコメント（各モジュールの冒頭）を参照してください。質問があれば使用例や README の追加項目（API 仕様、DB スキーマ、設計ドキュメント参照リンクなど）を用意します。