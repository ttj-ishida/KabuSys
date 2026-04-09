# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした小型のソフトウェアライブラリ／実装群です。本リポジトリにはポートフォリオ構築・ポジションサイジング、ファクター計算、ニュースの LLM によるセンチメント評価、市場レジーム判定、発注エンジン、監視ダッシュボードなどの主要コンポーネントが含まれます。

以下はこのコードベースの README です。

---

## プロジェクト概要

- 目的: 日本株向けに設計された自動売買パイプラインのコンポーネント群を提供する。
- 主な設計方針:
  - DuckDB / SQLite を用いたローカルデータ操作（外部取引所や本番 API への直接アクセスは分離）。
  - 純粋関数（副作用を持たない）で実装されるポートフォリオ計算・リスク調整ロジック。
  - OpenAI（gpt-4o-mini 等）を用いたニュース／マクロセンチメント計算（フォールバック設計あり）。
  - 監視/アラート（LINE プッシュ）、kill flag による安全停止、起動時のリコンシリエーション等の運用機能。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルートを .git や pyproject.toml で探索）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（スコア順）
  - 等配分 / スコア加重の重み計算
  - ポジション数（株数）決定（リスクベース or weight ベース）、単元株丸め
  - セクター上限適用、レジーム乗数計算

- リサーチ（kabusys.research）
  - Momentum / Volatility / Value などのファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（kabusys.ai）
  - ニュース記事の銘柄別センチメント評価（OpenAI）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（OpenAI 半自動）

- 実行系（kabusys.execution）
  - OrderManager / ExecutionEngine：シグナル取り込み → 発注 → push-drain（WebSocket）で約定同期
  - Broker API プロトコル定義、再起動時の Reconciler（自動復旧）
  - リスクゲート（Gate1/2/3）統合

- 監視（kabusys.monitoring）
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE への通知）
  - Streamlit ベースの監視ダッシュボード（read-only）

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションで | を使用）
- 仮想環境の使用を推奨

1. 仮想環境作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   （requirements.txt が無い場合は最低限の依存を手動で入れてください）
   ```
   pip install duckdb openai psutil requests streamlit
   ```
   - 運用（kabu API）やテストに応じてさらにパッケージが必要になる可能性があります。

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードはコード実行時に有効）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数（例とデフォルト）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - LINE_CHANNEL_ACCESS_TOKEN (AlertManager 用)
     - LINE_USER_ID (AlertManager 用)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development|paper_trading|live) デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト: INFO
     - PAPER_FILL_MODE (instant|partial|never|reject) デフォルト: instant
     - PID_FILE_PATH / KILL_FLAG_PATH / その他多数（settings を参照）

4. モニタリング DB の初期化（SQLite）
   - Python で init_monitoring_db を呼ぶか、簡易スクリプトを実行してください:
     ```py
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db

     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()
     ```

---

## 使い方（主要ユースケース）

- Streamlit 監視ダッシュボード起動（read-only）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - オプション `--db` で監視 DB パスを指定できます（省略時は data/monitoring.db）。

- ニュース NLP スコアリング（プログラム的に呼び出す）
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
  print("書き込み件数:", n_written)
  ```
  - OPENAI_API_KEY を環境変数に設定している場合は api_key 引数は不要です。
  - score_news は ai_scores テーブルへ結果を書き込みます。

- 市場レジーム判定（プログラム的に呼び出す）
  ```py
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")
  ```

- リサーチ / ファクター計算
  ```py
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- ポートフォリオ構築 & ポジションサイズ計算
  ```py
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

  buy_signals = [{"code": "1234", "score": 0.8, "signal_rank": 1}, ...]
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value=10_000_000, available_cash=2_000_000, current_positions={}, open_prices={"1234": 1500.0})
  ```

- 実行エンジン（簡易フロー）
  - ExecutionEngine は BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続などを組み合わせて動作します。実運用では concrete implementation（kabu station client 等）を用意してください。
  - 高レベルの流れ:
    1. 起動時に Reconciler で未確定注文を整合
    2. signal_send_start（デフォルト 8:50）にシグナルを読み込み発注
    3. push (WebSocket) を受けて約定同期
    4. Gate3（ドローダウン等）で kill_flag を作成して安全停止

  - 実行の呼び出し例（概念）:
    ```py
    from datetime import date, time
    engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=date.today()))
    engine.run_session()
    ```

- 監視（MonitoringEngine）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせて定期実行（ポーリング）し、AlertManager（LINE）や KillSwitch と連携します。
  - テスト用に `MonitoringEngine.run_once()` を使って一回だけ評価できます。

---

## 自動 .env 読み込みについて

- 実行時にプロジェクトルート（src/kabusys/config.py の親ディレクトリの上位を探索）を `.git` または `pyproject.toml` で特定し、そこにある `.env` → `.env.local` を順に読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - .env.local は .env の上書き（override=True）になりますが、既に OS にあるキーは保護されます。
- 自動ロードを無効化する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

.env のパースは Bash ライクな記法（export キーワード、クォート、コメント）にある程度対応しています。詳細は src/kabusys/config.py を参照してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理
- portfolio/
  - __init__.py
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数計算、上限・aggregate cap
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - __init__.py
  - factor_research.py — momentum/volatility/value ファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — ETF MA200 + マクロセンチメントによるレジーム判定
- monitoring/
  - __init__.py
  - monitoring_db.py — SQLite スキーマ + MonitoringDB クラス
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - alert_manager.py — LINE 通知
  - kill_switch.py
  - monitoring_engine.py
  - streamlit_dashboard.py — Streamlit UI
- execution/
  - broker_api.py — Broker インターフェース定義 / データモデル / 例外
  - order_manager.py
  - order_repository.py (参照されるが今回リストには未提示)
  - order_record.py (参照されるが今回リストには未提示)
  - reconciler.py
  - execution_engine.py
  - risk_manager.py (参照されるが今回リストには未提示)
- その他: data/（DB 等を置く想定）

（注）上記はリポジトリ内の主要モジュールを抜粋したものです。実際にはさらに補助的なモジュールやテストが含まれる場合があります。

---

## 運用上の注意 / ベストプラクティス

- OpenAI を利用する機能は API コスト・レイテンシが発生します。API キー管理・レート制御・リトライ挙動は各モジュールで対処していますが、運用前に十分な検証を行ってください。
- kill.flag による停止、監視 DB の risk_logs/ dashboard によるアラートは重要な安全弁です。PID ファイル / kill flag の取り扱いは設定（Settings）に依存します。
- 実ブローカ連携（kabu station 等）を行う場合、BrokerAPIProtocol 実装を正確に用意し、OrderManager / Reconciler の動作を理解した上でテストしてください。
- DuckDB / SQLite のスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets など）は外部処理で用意する必要があります。research/ai モジュールはこれらのテーブルを前提としています。

---

## 参考（開発者向け）

- 設定オブジェクト: `from kabusys.config import settings` で各種設定にアクセスできます（例: settings.duckdb_path, settings.kabu_api_base_url）。
- ログレベルは環境変数 `LOG_LEVEL` で制御します。
- テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、環境影響を抑えてください。
- OpenAI 呼び出しは内部で再試行ロジックを持ちますが、テストでは関連関数をモック化してください（例: unittest.mock.patch）。

---

必要であれば、README をプロジェクト固有の詳細（requirements.txt、例の .env.example、スキーマ定義 SQL、実際の Broker 実装のリンクなど）で拡張します。どの情報を追加したいか指示ください。