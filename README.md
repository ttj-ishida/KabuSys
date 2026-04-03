# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）・データ品質チェック・ニュース収集・AI を使ったニュースセンチメントや市場レジーム判定・ファクター計算・監査ログなどの機能を提供します。

主な想定用途：
- データパイプライン（夜間ETL）による価格・財務・カレンダーの取得と品質管理
- ニュース収集と LLM を使った銘柄別センチメント算出
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- ファクター計算・研究ツール（モメンタム / バリュー / ボラティリティ 等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS 取得・前処理・raw_news への保存補助）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news：銘柄ごとの LLM センチメントを ai_scores に書込）
  - レジーム判定（score_regime：ETF MA とマクロニュースで bull/neutral/bear を判定）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - .env 自動読み込みと Settings（環境変数管理）
- audit
  - 監査ログ（signal_events / order_requests / executions）スキーマ定義と初期化ユーティリティ

（strategy / execution / monitoring 等の上位レイヤーはプロジェクト設計に含まれます）

---

## 前提・要件

- Python 3.10+（型アノテーションで | を使用しているため）
- 推奨パッケージ（プロジェクトで使用されるもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI API）
- J-Quants および（必要なら）OpenAI API の認証情報

requirements.txt がない場合は適宜インストールしてください。例：
pip install duckdb openai defusedxml

---

## 環境変数（主なもの）

必須または重要な環境変数：

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API のパスワード（必須、発注層を使う場合）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | ...)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH — 実行監視用ファイルパス
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読み込みを無効化

README 用の簡易 .env.example（プロジェクトルート）例：
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

config.Settings は .env（および .env.local）を自動読み込みします（プロジェクトルートを .git または pyproject.toml を基準に探索）。

---

## セットアップ手順（開発向け）

1. リポジトリを取得
   - git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt  （プロジェクトに requirements.txt がある場合）
   - または最低限:
     - pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境変数を設定
   - 例: .env に JQUANTS_REFRESH_TOKEN 等を記載

5. DuckDB データベース作成（任意）
   - data ディレクトリを作成: mkdir -p data
   - 初期化はコードから行う（下記参照）

---

## 使い方（主要な例）

以下はいくつかの主要なユースケースのサンプルです。実行は仮想環境内で Python を起動して行ってください。

- DuckDB 接続の作成（監査 DB 初期化）
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/kabusys_audit.duckdb")

- 日次 ETL の実行（J-Quants から差分取得）
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメント算出（ai.news_nlp.score_news）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    # OPENAI_API_KEY が環境変数に設定されているか、api_key を渡す
    written = score_news(conn, target_date=date(2026,3,20))
    print(f"書き込み銘柄数 = {written}")

- 市場レジーム判定（ai.regime_detector.score_regime）
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必須

- ファクター計算（research）
  - from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

    conn = duckdb.connect("data/kabusys.duckdb")
    mom = calc_momentum(conn, date(2026,3,20))
    vol = calc_volatility(conn, date(2026,3,20))
    val = calc_value(conn, date(2026,3,20))

- 設定の参照
  - from kabusys.config import settings
    print(settings.duckdb_path)
    print(settings.is_live)

注意：
- AI モジュール（score_news / score_regime）は OpenAI API を呼び出します。API キーは環境変数 OPENAI_API_KEY か、関数引数 api_key に渡してください。
- ETL / 保存関数は DuckDB のテーブルスキーマを前提とします。初回はスキーマ作成ユーティリティ（プロジェクト内にある schema 初期化関数等）を呼んでください（例: data.audit.init_audit_schema など）。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（.env 自動ロード・Settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント算出（LLM 呼び出し・バッチ処理・検証）
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / 認証 / rate limiter）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — カレンダー管理・営業日判定
  - news_collector.py — RSS 収集・前処理（SSRF 回避・XML 安全パース）
  - quality.py — データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - audit.py — 監査ログスキーマ（signal / order_request / executions）初期化
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - etl.py — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン, IC, 統計サマリー 等

（上位レイヤー）
- strategy/  (戦略ロジック)
- execution/ (発注ロジック)
- monitoring/ (プロセス監視、PID・kill flag 等)

---

## 運用上の注意・設計方針（抜粋）

- Look-ahead bias 回避：内部ロジックは基本的に date 引数を受け、datetime.today()/date.today() を直接参照しないよう設計されています。バックテスト等で未来情報を参照するリスクを低減しています。
- 冪等性：J-Quants から取得したデータは保存時に ON CONFLICT DO UPDATE を用いて冪等に保存します。
- フェイルセーフ：AI 呼び出しや外部 API の失敗はデフォルトでスコア 0.0 などにフォールバックし、パイプライン全体の致命的停止を防ぎます（ログ出力は行います）。
- セキュリティ：news_collector は SSRF 対策・XML インジェクション対策を実装しています（URL スキーム検証、プライベートIP検査、defusedxml の利用等）。

---

## 開発・テストのヒント

- 環境変数の自動読み込みは .git または pyproject.toml を基準にプロジェクトルートを探索します。テスト中は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI 呼び出し部分は内部で分離されており、ユニットテスト時には該当関数をモックすることが想定されています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB をインメモリ(":memory:") で使うとユニットテストが高速になります（監査 DB 初期化関数が対応）。

---

必要であれば、README に以下を追記できます：
- 詳細な .env.example（全キー一覧）
- DuckDB スキーマ初期化手順（テーブル DDL の適用例）
- CI / デプロイ手順（systemd ユニットやコンテナ化の例）
- strategy / execution 層のサンプルコード

追加で反映したい点があれば教えてください。