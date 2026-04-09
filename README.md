# KabuSys

日本株向けの自動売買 / リサーチ / 監視フレームワーク（ライブラリ）。  
ポートフォリオ構築・ポジションサイジング・リスク制御・発注エンジン・監視ダッシュボード・AI（ニュースセンチメント / レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のアルゴリズムトレーディングに必要な典型的機能群をモジュール化したコードベースです。主な設計方針は以下です。

- 明確な責務分離（リサーチ / ポートフォリオ構築 / 実行 / 監視 / AI）
- DuckDB / SQLite を用いたローカルデータ処理・永続化
- OpenAI を利用したニュースセンチメント / レジーム判定
- 本番での安全性（kill フラグ、再起動時リコンシリエーション、リスクゲート）
- テスト容易性（副作用を限定、環境変数自動読み込みの無効化オプション等）

---

## 主な機能一覧

- 環境設定管理（.env 自動読み込み / Settings クラス）
  - OS 環境 > .env.local > .env の優先順位（自動読み込みは無効化可能）
- ポートフォリオ構築
  - 候補選定（スコア順ソート）
  - 等配分・スコア加重配分
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - 株数決定（risk_based / equal / score）と lot 整数化・aggregate cap 調整
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- AI（OpenAI）
  - ニュースを集約して銘柄ごとのセンチメントを算出し ai_scores に書き込み（score_news）
  - マクロニュース + ETF MA200 乖離から市場レジーム（bull/neutral/bear）判定（score_regime）
  - API 呼び出しは冪等・再試行・フェイルセーフ実装
- 発注系（Execution）
  - OrderManager（DB 永続化を伴う状態遷移、送信失敗の取り扱い）
  - ExecutionEngine（シグナル処理 + WebSocket プッシュ排水）
  - Reconciler（再起動時の注文・ポジション突合）
- 監視（Monitoring）
  - MonitoringDB（SQLite ベースの schema + helper）
  - System / Trade / Risk モニタ、KillSwitch、AlertManager（LINE Push）
  - Streamlit ベースの監視ダッシュボード（read-only 接続可）

---

## セットアップ手順

※ Python 環境（3.9 以上を想定）で作業してください。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（最低限）
   - pip install duckdb openai requests psutil streamlit

   ※プロジェクトで使う追加のライブラリがある場合は適宜追加してください。

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能）。
   - 代表的な環境変数（詳細は次節「環境変数一覧」を参照）:
     - JQUANTS_REFRESH_TOKEN（必須: J-Quants API 用）
     - KABU_API_PASSWORD（必須: kabu API 用）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知を使う場合）
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等（DB パス上書き）

6. Monitoring DB の初期化（SQLite）
   - Python スクリプトで初期化できます:

     from pathlib import Path
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db

     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN
  - J-Quants API のリフレッシュトークン（必須）

- KABU_API_PASSWORD
  - kabu station API のパスワード（必須）

- KABU_API_BASE_URL
  - kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）

- OPENAI_API_KEY
  - OpenAI API キー（AI 機能を使用するために必要）

- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - AlertManager（LINE 通知）に必要。両方が空だと通知は送信されずログ出力のみ

- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH
  - 監視 DB のパス（デフォルト: data/monitoring.db）

- PAPER_FILL_MODE
  - Paper Trading のモック約定挙動（instant/partial/never/reject）

- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - 実行制御用の PID ファイル / kill.flag のパスと起動時クリア設定

- KABUSYS_ENV
  - 実行環境（development / paper_trading / live）

- LOG_LEVEL
  - ログレベル（DEBUG/INFO/...）

その他、コード中に多くの tunable な環境変数やパラメータがあります。`.env.example` を参考にしてください（プロジェクトルートに置く想定）。

---

## 使い方（簡単な例）

以下は代表的なモジュールの簡単な呼び出し例です。

- Settings（環境変数の利用）
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token

- Monitoring DB 初期化（上記セクション参照）

- Streamlit 監視ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ニュースセンチメント評価を実行して ai_scores テーブルへ書き込む
  - Python から（DuckDB 接続を用意する必要あり）:

    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- マーケットレジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- ExecutionEngine（本番運用のエントリポイント）
  - ExecutionEngine は BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続、EngineConfig などを組み合わせて使います。実際の稼働時は Broker クライアント（kabu station 実装）等を渡して run_session() を呼びます。
  - 実行前に kill.flag の存在チェックや PID ファイル処理が行われます。

- ポートフォリオ関数（純関数で呼び出しやすい）
  - from kabusys.portfolio import (
        select_candidates,
        calc_equal_weights,
        calc_score_weights,
        calc_position_sizes,
        apply_sector_cap,
        calc_regime_multiplier,
    )

  - 例: 上位 N を選択して等配分の重みを計算
    candidates = select_candidates(buy_signals, max_positions=10)
    weights = calc_equal_weights(candidates)

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py          — ニュースセンチメント（OpenAI 経由）
  - regime_detector.py   — レジーム判定（ETF MA + マクロニュース）
- portfolio/
  - __init__.py
  - portfolio_builder.py  — 候補選定 / 重み計算
  - position_sizing.py    — 株数計算・スケーリング
  - risk_adjustment.py    — セクターキャップ・レジーム乗数
- research/
  - __init__.py
  - factor_research.py    — Momentum / Volatility / Value
  - feature_exploration.py— 将来リターン / IC / 統計
- monitoring/
  - __init__.py
  - monitoring_db.py      — SQLite テーブル定義・CRUD ユーティリティ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py         — Broker API の Protocol / Data Model / 例外
  - order_manager.py
  - order_repository.py   — （orders DB 取り扱い: 別ファイルだが同階層想定）
  - order_record.py
  - execution_engine.py
  - reconciler.py
  - risk_manager.py
- monitoring/ (上記)
- research/ (上記)

（注）上記は本 README に含まれるファイルの抜粋です。実際のプロジェクトではさらに data/、および orders DB 用モジュール等が存在します。

---

## 運用上の注意 / ベストプラクティス

- 環境変数管理は慎重に行ってください。APIキーは Git 等にコミットしないでください。
- AI 関連機能は API 料金やレイテンシを考慮してバッチ処理・リトライ設計が組まれていますが、実運用ではレート制限やコストに注意してください。
- kill.flag / PID ファイルでエンジンの制御を行います。運用時は監視プロセスが正しく動作しているか確認してください。
- Reconciler は再起動時の安全性確保に重要です。Broker API の実装と DB の一貫性をテストしておいてください。
- DuckDB / SQLite のファイルパスは環境変数で上書き可能です。バックアップを取りながら運用してください。

---

## 参考・トラブルシューティング

- 環境変数の自動読み込みを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
- OpenAI 呼び出しで JSON パースエラーが出る場合:
  - モデルのレスポンスが期待 JSON 形式でないことが原因です。API キー・モデルの応答形式／プロンプトを再確認してください。
- Streamlit で DB を読み込めない場合:
  - streamlit はデフォルトでファイルロック等の制限に当たるため、read-only モード URI (file:///... ?mode=ro) を使うか、MonitoringEngine 側で DB を開いているか確認してください。

---

必要であれば、使い方の具体的なスニペット（ExecutionEngine の起動スクリプト例、OrderRepository の初期化方法、DuckDB にデータをロードする手順など）を追記します。どの部分の例を追加しますか？