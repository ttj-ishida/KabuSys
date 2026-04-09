# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／リサーチ／監視フレームワークです。  
DuckDB / SQLite を用いたオンプレ（ローカル）データ処理と、必要に応じて OpenAI を利用したニュース NLP / レジーム判定機能、kabu station 相当のブローカー抽象層、発注エンジン、監視エンジン等を含みます。

この README ではプロジェクト概要、機能一覧、セットアップ手順、使い方（主要 API の例）、およびディレクトリ構成を日本語で説明します。

---

## 主要な機能概要

- 環境変数・.env の自動読み込み（.env / .env.local、ただし無効化可能）
- ポートフォリオ構築:
  - シグナル選定（スコア順ソート）
  - 等金額配分 / スコア加重配分
  - セクター上限適用、レジーム乗数算出
  - ポジションサイズ算出（リスクベース / 等分配 等）
- リサーチ / ファクター計算:
  - Momentum / Value / Volatility / Liquidity 等のファクター算出（DuckDB 経由、prices_daily/raw_financials）
  - 将来リターン（forward returns）, IC（Information Coefficient）, 統計サマリー
- AI（OpenAI）連携:
  - ニュース記事を LLM でセンチメント化し ai_scores へ書き込み（news_nlp.score_news）
  - マクロニュース + ETF MA 乖離を用いた市場レジーム判定（ai.regime_detector.score_regime）
  - API 呼び出しはリトライ・フォールバック・バリデーション実装済み
- 発注 / 実行:
  - ExecutionEngine（Signal Queue Pull 型）: 発注ゲート（Gate1/2/3）、WebSocket ドレイン、PID / kill.flag ハンドリング
  - OrderManager: DB 永続化を伴う安全な発注フロー（OrderCreated → OrderSent → OrderAccepted 等）
  - Reconciler: 起動時の自動リコンシリエーション（注文・ポジションの突合）
- 監視:
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard テーブル
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE 通知）
  - Streamlit ベースの監視ダッシュボード（read-only）

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.9+（型注釈の union 型や typing 等を使用）、git が利用可能。

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（最低限の依存）
   ```
   pip install duckdb openai requests psutil streamlit
   ```
   ※ プロジェクトに requirements.txt がある場合はそちらを利用してください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（起動時）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。

   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用）
   - KABU_API_PASSWORD — 必須（kabu station API 用パスワード）
   - KABU_API_BASE_URL — 任意（デフォルト: http://localhost:18080/kabusapi）
   - OPENAI_API_KEY — OpenAI API キー（ai 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE 通知）用
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — Monitoring DB（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE — Paper trading の挙動（instant|partial|never|reject）
   - その他: PID_FILE_PATH, KILL_FLAG_PATH, KABUSYS_ENV, LOG_LEVEL 等

   例（.env）:
   ```
   OPENAI_API_KEY=sk-xxxx
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

5. Monitoring DB 初期化（例）
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

---

## 使い方（主要な API と実行例）

ここでは代表的な利用例を示します。実際の運用ではブローカー実装やデータベースのスキーマ、エンジンパラメータ調整が必要です。

- Settings（環境変数取得）
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  dbpath = settings.duckdb_path
  ```

- ニュース NLP（OpenAI を使って ai_scores に書き込む）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → 環境変数参照
  print(f"書き込んだ銘柄数: {written}")
  ```

- レジーム判定（market_regime テーブル書込）
  ```python
  from kabusys.ai.regime_detector import score_regime
  written = score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- Monitoring DB / MonitoringEngine
  - MonitoringDB を初期化したら SystemMonitor / TradeMonitor / RiskMonitor 等を組み合わせて MonitoringEngine を作成できます。
  - 監視ダッシュボード（Streamlit）:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- ExecutionEngine（概要）
  - ExecutionEngine は BrokerAPIProtocol を実装したブローカークライアント、OrderRepository（SQLite）、RiskManager、OrderManager 等が必要です。
  - 起動時に Reconciler を使って自動リコンシリエーションを行い、指定セッション時間帯でシグナル処理と push ドレインを行います。
  - kill.flag / PID の管理や、Gate1/2/3 によるリスク制御が組み込まれています。

- ポートフォリオ／ポジション計算（ライブラリ関数）
  ```python
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

  candidates = select_candidates(buy_signals=[{"code":"7203","score":0.5,"signal_rank":1}, ...], max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value=10_000_000, available_cash=7_000_000, current_positions={}, open_prices={"7203":1000})
  ```

- リサーチ / ファクタ分析
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

  rows_mom = calc_momentum(conn, target_date=date(2026,3,20))
  rows_vol = calc_volatility(conn, target_date=date(2026,3,20))
  rows_val = calc_value(conn, target_date=date(2026,3,20))
  fwd = calc_forward_returns(conn, target_date=date(2026,3,20))
  ic = calc_ic(factor_records=rows_mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

---

## 注意点 / 設計上のポリシー

- ルックアヘッドバイアス回避:
  - research / ai モジュールは `datetime.today()` / `date.today()` を参照しない実装方針（呼び出し側で target_date を渡す）。
  - DuckDB のクエリでは target_date 未満等の条件で未来データを参照しないよう配慮。

- OpenAI 利用:
  - API 呼び出しはリトライ・バックオフやレスポンスバリデーションを行い、失敗時はフェイルセーフ（0.0フォールバック）で継続します。
  - 出力は厳密な JSON を期待するプロンプトを使用していますが、念のためパース時に最外の {} を抽出する耐性を持ちます。

- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env と .env.local を自動読み込みします。
  - 読み込み順は OS 環境変数 > .env > .env.local（.env.local は override=True で上書き）です。
  - 自動読み込みを無効化するためには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットできます。

- DB への書き込み:
  - ai.score_news / regime_detector.score_regime / monitoring_db.init_monitoring_db 等はトランザクション制御や冪等性（DELETE→INSERT 等）を考慮した実装です。
  - DuckDB/SQLite のバージョン差分による制約（executemany の空リスト等）に配慮した実装が行われています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- __version__ = "0.1.0"

パッケージ別（主要モジュール）
- ai/
  - news_nlp.py         — ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py  — マクロ + ETF MA による市場レジーム判定
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py   — 株数算出 / スロットリング / aggregate cap
  - risk_adjustment.py   — セクターキャップ / レジーム乗数
- research/
  - factor_research.py   — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- monitoring/
  - monitoring_db.py     — SQLite ベースの永続層（テーブル作成・CRUD）
  - system_monitor.py    — システム / データ鮮度監視
  - trade_monitor.py     — 注文滞留 / 約定異常監視
  - risk_monitor.py      — ドローダウン・ポジション上限チェック
  - kill_switch.py       — kill.flag 管理
  - alert_manager.py     — LINE Push 通知
  - monitoring_engine.py — 複数モニタのポーリング統括
  - streamlit_dashboard.py — Streamlit ダッシュボード（起動コマンドはソース内参照）
- execution/
  - broker_api.py        — ブローカー API model / Protocol / 例外
  - order_manager.py     — 発注ステートマシン外向き API（create/send/sync/cancel）
  - execution_engine.py  — Signal 処理 + push ドレインの実行エンジン
  - reconciler.py        — 起動時の注文・ポジション突合作業
  - ...（order_repository, order_record, risk_manager 等は同階層に存在する想定）
- monitoring_db.py（上位で説明済）
- その他:
  - data/ (想定) — データファイル（DuckDB、SQLite、kill.flag 等）

（注）ここに示したのはコードベース中で主要なモジュールを抜粋した一覧です。実際のリポジトリにはさらに補助的なモジュールやテストが含まれます。

---

## よくある運用上のヒント

- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境依存を切ると良いです。
- OpenAI を用いる処理は API レートやコストに注意してバッチサイズ・トークン長を調整してください（news_nlp は1チャンク最大20銘柄に制限）。
- DuckDB のテーブル（prices_daily/raw_financials/raw_news/news_symbols/ai_scores/market_regime 等）はリサーチと AI 機能で参照されます。適切なマイグレーション・インポートパイプラインでデータを投入してください。
- ExecutionEngine は PID ファイル・kill.flag を使用します。運用スクリプト・監視ツールと連携する際はこれらのファイルを考慮してください。

---

必要であれば以下も提供できます:
- サンプル .env.example
- DuckDB / SQLite の最小スキーマ定義（テーブル CREATE 文）
- ExecutionEngine / OrderManager を動かすためのミニマルなサンプル（モック Broker 実装と DB 初期化を含む）

ご希望があれば、用途に合わせた README の拡張（運用手順、デプロイ手順、CI/CD、テストガイド等）を作成します。