# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージです。ポートフォリオ構築、ポジションサイジング、ファクター計算、ニュースの NLP スコアリング、市場レジーム判定、監視エンジンや発注エンジンまでを含むモジュール群で構成されています。

以下はこのリポジトリの README（日本語）です。

---

## プロジェクト概要

KabuSys は主に以下の目的を持つコンポーネント群を提供します。

- ポートフォリオ構築（候補選定、重み計算、リスク調整、株数算出）
- ファクター・リサーチ（モメンタム、バリュー、ボラティリティ等）
- ニュースの LLM ベースのセンチメントスコアリング（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 発注エンジン（ExecutionEngine / OrderManager / Broker API 抽象化）
- 起動時リコンシリエーション（Reconciler）
- 監視機能（System / Trade / Risk の監視、LINE 通知、Streamlit ダッシュボード）
- 監視ログ永続化（SQLite ベースの MonitoringDB）

設計方針として、DB（DuckDB / SQLite）接続を外部から受け取る純粋関数・クラス分離、LLM 呼び出しはフェイルセーフにする、ルックアヘッドバイアスを避ける（内部で date.today() を直接参照しない）などが採用されています。

---

## 主な機能一覧

- ポートフォリオ
  - select_candidates: BUY シグナルから上位候補選定
  - calc_equal_weights / calc_score_weights: 重み計算
  - apply_sector_cap / calc_regime_multiplier: セクター上限・レジーム乗数
  - calc_position_sizes: 株数（単元）算出（risk_based / equal / score）
- リサーチ
  - calc_momentum / calc_volatility / calc_value: ファクター計算（DuckDB を利用）
  - calc_forward_returns / calc_ic / factor_summary: 特徴量探索・IC 解析
- AI（OpenAI）
  - score_news: ニュース集約 → OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出して ai_scores に保存
  - score_regime: マクロ記事 + ETF MA を組み合わせて市場レジーム判定を実行し market_regime に保存
- 発注 / 実行
  - ExecutionEngine: シグナルループ + WebSocket ドレインによる発注制御
  - OrderManager / Reconciler: 発注フローと起動時リコンシリエーション
  - BrokerAPIProtocol（抽象）: ブローカークライアント実装を差し替え可能
- 監視
  - MonitoringDB: SQLite スキーマ作成 / 永続化 API
  - SystemMonitor / TradeMonitor / RiskMonitor: 各種チェックとリスクログ
  - AlertManager: LINE push による通知（cooldown 管理）
  - KillSwitch: ファイルによる強制停止シグナル（data/kill.flag）
  - streamlit_dashboard.py: 監視用ダッシュボード（Streamlit）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python の準備（推奨: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（最低限）
   - pip install --upgrade pip
   - pip install duckdb openai psutil requests streamlit

   ※ 実プロジェクトでは requirements.txt を用意しているかもしれません。存在する場合は
   - pip install -r requirements.txt

4. パッケージをインストール（ローカル開発）
   - pip install -e .

5. 環境変数 / .env の設定
   - プロジェクトルート（.git または pyproject.toml と同じ階層）に `.env` として各種設定を置くと自動で読み込まれます。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等）。

   例（.env）:
   ```
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - .env.local がある場合は .env の上書きとして読み込まれます（OS 環境変数は常に最優先で保護されます）。

---

## 使い方（よく使う操作例）

※ 以下は最小限の使用例です。各モジュールはライブラリ的に import して利用できます。

- DuckDB / SQLite 接続例
  ```python
  import duckdb, sqlite3
  conn = duckdb.connect("data/kabusys.duckdb")
  monitoring_conn = sqlite3.connect("data/monitoring.db")
  ```

- 監視 DB 初期化
  ```python
  import sqlite3
  from kabusys.monitoring.monitoring_db import init_monitoring_db
  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  ```

- Streamlit ダッシュボード起動
  - コマンド:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ニュース NLP（OpenAI を用いたセンチメント集約）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数または score_news(api_key=...)
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- リサーチ系関数（ファクター計算）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  result = calc_momentum(conn, date(2026, 3, 20))
  ```

- ポートフォリオ構築・サイジングの使用例
  ```python
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

  buy_signals = [{"code":"1234","score":0.5,"signal_rank":1}, {"code":"2345","score":0.2,"signal_rank":2}]
  candidates = select_candidates(buy_signals, max_positions=5)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(
      weights=weights,
      candidates=candidates,
      portfolio_value=10_000_000,
      available_cash=1_000_000,
      current_positions={},
      open_prices={"1234":1500.0,"2345":800.0},
  )
  ```

- ExecutionEngine（本番セッション実行の概念）
  - 実行には Broker 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続など複数コンポーネントが必要です。実稼働用のブートストラップはアプリケーション固有です。
  - 起動時 kill.flag チェック・PID 書き出し・起動時リコンシリエーションなどの機能を内包しています。

---

## 環境変数（主なもの）

以下は Settings で参照される主要な環境変数（.env に設定）です。

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（既定: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN — LINE Push 用トークン（任意）
- LINE_USER_ID — LINE Push 先ユーザ ID（任意）
- DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB パス（既定: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading の模擬約定モード（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（既定: data/paper_trading.db）
- PID_FILE_PATH — 実行 PID ファイル（既定: data/execution.pid）
- KILL_FLAG_PATH — kill flag ファイル（既定: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" でクリア）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — environment (development|paper_trading|live)
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

.env のパースはプロジェクトルートの `.env` / `.env.local` を自動ロードします（OS 環境変数は保護されます）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ初期化（version 等）
- config.py — 環境変数 / Settings 管理（.env 自動ロード、検証）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数・資金配分算出
  - risk_adjustment.py — セクター上限・レジーム乗数
  - __init__.py
- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
  - __init__.py
- ai/
  - news_nlp.py — ニュース集約 + OpenAI による銘柄センチメント
  - regime_detector.py — レジーム判定（ETF MA + マクロニュース）
  - __init__.py
- monitoring/
  - monitoring_db.py — SQLite スキーマと DB API
  - system_monitor.py — システム / データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - alert_manager.py — LINE 通知（cooldown）
  - kill_switch.py — ファイルベースの停止シグナル処理
  - monitoring_engine.py — 監視ループ統合
  - streamlit_dashboard.py — Streamlit ダッシュボード
  - __init__.py
- execution/
  - broker_api.py — Broker API のデータモデル / Protocol / 例外
  - order_manager.py — 発注フロー（OrderManager）
  - reconciler.py — 起動時リコンシリエーション
  - execution_engine.py — Signal-driven 発注エンジン
  - その他関連モジュール（OrderRepository 等は別ファイルに存在する想定）
- monitoring、research、portfolio、ai などのサブパッケージで機能を分割

（上記はリポジトリ内の主要ファイルを抜粋しています。）

---

## 注意事項 / 運用メモ

- OpenAI キーは安全に管理してください。AI モジュールは API 呼び出し失敗時にフェイルセーフ（0.0 にフォールバック等）する設計ですが、キー漏洩は避けるべきです。
- .env の自動ロードはプロジェクトルートから行われます。パッケージ配布後も __file__ を起点として探索するため、CWD に依存しません。
- kill.flag による停止は冪等（既存なら追記しない）です。ExecutionEngine は起動時に PID ファイルを書き込み、終了時に削除します。
- DuckDB / SQLite のスキーマはコードに依存しているため、DB を直接編集する場合は注意してください。
- 本リポジトリは実際のブローカー API と接続する前提コードを含みます。実際の売買で利用する場合は、十分なテストと保険（paper_trading モード、リスク閾値設定）を行ってください。

---

## 開発・拡張のヒント

- BrokerAPIProtocol を実装することで各証券会社のクライアントを差し替え可能です。
- position sizing の lot_size を銘柄別に対応させる拡張や、価格のフォールバック（前日終値等）を実装する余地があります（TODO コメントあり）。
- AI モジュールは JSON モードを前提に堅牢なバリデーションを行っています。別モデルやプロンプト調整は _SYSTEM_PROMPT を変更してください。

---

以上が KabuSys の概要と利用手順です。必要に応じて README を補強（依存関係の固定、起動用スクリプト、実行例 repository 内のサンプル CLI などの追加）すると利用者に親切です。質問やドキュメントに追記したい箇所があれば教えてください。