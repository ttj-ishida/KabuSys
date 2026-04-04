# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI 経由）、リサーチ用ファクター計算、監査ログ、マーケットカレンダー管理、監視ユーティリティなどを含むモジュール群です。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計）
- DuckDB を中心としたローカルデータレイク
- 外部 API はリトライ・レート制御・フェイルセーフを備える
- DB 書き込みは冪等性（ON CONFLICT / upsert）を重視

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分取得・保存（jquants_client / data.pipeline）
  - 日次 ETL パイプライン（run_daily_etl）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集 / NLP
  - RSS 収集（news_collector）と raw_news / news_symbols への冪等保存
  - OpenAI を用いたニュースセンチメント算出（news_nlp.score_news）
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュース（LLM）を組み合わせた日次レジーム判定（ai.regime_detector.score_regime）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ（research.feature_exploration）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルの初期化と運用用ユーティリティ（data.audit）
- マーケットカレンダー管理（data.calendar_management）
- 各種ユーティリティ
  - 設定管理（環境変数読み込み、自動 .env ロード）（config）
  - 統計ユーティリティ（z-score 正規化等）（data.stats）
  - データ品質チェック（data.quality）

---

## 動作要件（推奨）

- Python 3.10+
- 必須ライブラリ例:
  - duckdb
  - openai
  - defusedxml
- その他（用途に応じて）:
  - requests 等（現コードは urllib を中心に実装）
- 実行環境でのネットワーク・API キー（J-Quants / OpenAI など）が必要

（注）プロジェクト配布に requirements.txt / pyproject.toml がある想定です。環境に合わせて依存をインストールしてください。

例:
pip install duckdb openai defusedxml

または（プロジェクトルートで）
pip install -e .

---

## セットアップ手順

1. ソースを取得（例: git clone）
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）
3. 依存をインストール
   - pip install -r requirements.txt
   - もしくは手動: pip install duckdb openai defusedxml
4. 環境変数設定
   - プロジェクトルートに `.env` を作成（`.env.example` を参照）
   - 主な必須変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う際に必要）
     - KABU_API_PASSWORD — kabu ステーション API を使う場合
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV ∈ {development, paper_trading, live}（default: development）
     - LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL}（default: INFO）
   - 自動 .env 読み込み:
     - パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）から `.env`、`.env.local` を読み込みます。
     - テスト等で無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（短いコード例）

事前に J-Quants / OpenAI のキーなど環境変数を設定してください。

- DuckDB に接続して日次 ETL を実行する
  - 目的: prices / financials / calendar を差分取得して保存、品質チェックを実行
  - 例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    res = run_daily_etl(conn, target_date=date(2026,3,20))
    print(res.to_dict())

- ニュースセンチメント（ai.news_nlp.score_news）
  - OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026,3,20))
    print(f"scored {n} symbols")

- 市場レジーム判定（ai.regime_detector.score_regime）
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))

- 監査 DB 初期化（data.audit）
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # テーブルが作成され、UTC timezone が設定されます

- 設定値の参照（kabusys.config）
    from kabusys.config import settings
    print(settings.duckdb_path, settings.env, settings.jquants_refresh_token[:4] + "...")

---

## 環境変数一覧（主なもの）

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - OPENAI_API_KEY (news / regime で必要)
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- 通知
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB / ファイル
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視DB, デフォルト: data/monitoring.db)
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- 監視しきい値
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- 実行環境 / ログ
  - KABUSYS_ENV ∈ {development, paper_trading, live}
  - LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL}
- 自動 .env 読み込みを無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

（詳細は kabusys.config.Settings のプロパティ参照）

---

## ディレクトリ構成（主要モジュール）

src/kabusys/
- __init__.py — パッケージエントリ（__version__）
- config.py — 環境変数 / .env 自動読み込み・設定ラッパ
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント算出（OpenAI）
  - regime_detector.py — ETF MA とマクロニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETL 型の再エクスポート（ETLResult）
  - news_collector.py — RSS 収集・前処理・保存
  - calendar_management.py — JPX カレンダー管理・営業日ロジック
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログテーブルの DDL / 初期化
- research/
  - __init__.py
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ等

（上記は主要ファイルの一覧。プロジェクトに応じてさらにモジュールが存在する可能性があります）

---

## 注意事項 / 運用メモ

- Look-ahead バイアス対策: バックテストや日次処理で厳密に過去時点の情報のみを用いる設計思想があります。内部関数は target_date ベースで動作し、現在時刻を暗黙に使用しないように実装されています。
- 冪等性: ETL の保存処理は ON CONFLICT / upsert を用いて同一データの上書きを防ぎつつ最新情報を保存します。
- エラーハンドリング: 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフ（例: LLM 失敗時は中立スコアにフォールバック）を取り入れています。
- テスト: OpenAI 呼び出しなどは内部の _call_openai_api を patch してモック可能に実装されています。

---

最小限の README ですが、具体的な使い方や運用フロー（定期 ETL ジョブ・監視・本番とペーパーの切り替え等）については運用要件に合わせて追記してください。質問や追加で記載してほしい項目があれば教えてください。