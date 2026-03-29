# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）

短い概要:
KabuSys は日本株のデータプラットフォーム・リサーチ・戦略実行のための内部ライブラリ群です。J-Quants API や RSS ニュースを取得して DuckDB に保存する ETL、データ品質チェック、監査ログ（トレーサビリティ）機能、ファクター計算・特徴量解析、さらに OpenAI を用いたニュースセンチメント／市場レジーム判定などを提供します。

主なユースケース:
- 日次 ETL（株価・財務・カレンダー）と品質チェックの自動化
- ニュース収集と AI によるセンチメントスコアリング
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算と研究
- 発注フローの監査テーブル初期化（監査/トレーサビリティ）
- J-Quants / OpenAI を利用した定期バッチ処理、研究・検証

---

## 機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で必須環境変数を取得

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants API クライアント（kabusys.data.jquants_client）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データ品質管理（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合チェック
  - QualityIssue オブジェクトで問題を集約

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / next/prev_trading_day / get_trading_days / SQ判定
  - JPX カレンダー同期ジョブ

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、前処理、SSRF 対策、トラッキングパラメータ除去
  - raw_news / news_symbols への冪等保存対応想定

- AI（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースを合成して市場レジームを判定

- リサーチ（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize を含む統計ユーティリティ

- 監査・トレーサビリティ（kabusys.data.audit）
  - 監査テーブル DDL / インデックス定義、init_audit_schema / init_audit_db

---

## 前提（Prerequisites）

- Python 3.10+
  - 型注釈や | ユニオンなどを使用しているため Python 3.10 以上を推奨
- 必要な外部ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API / OpenAI / RSS などへのアクセス権

（プロジェクトの requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 開発用インストール / 必要パッケージをインストール
   - pip install -e .
   - または最低限:
     - pip install duckdb openai defusedxml

3. 環境変数を設定
   - プロジェクトルートに .env（および任意で .env.local）を置くと自動読み込みされます。
   - 自動読み込みを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注系で使用）
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI 呼び出しに使用（各関数へ引数で渡すことも可能）
   - 省略可能・デフォルト:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト development
     - LOG_LEVEL — デフォルト INFO
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

4. データディレクトリ作成
   - デフォルトで data/ 以下にデータベースファイルが想定されています。必要に応じて作成します:
     - mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトからの呼び出し例です。各例では DuckDB 接続を渡します。

- 日次 ETL を実行する:
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(<Path to duckdb>))  # 例: "data/kabusys.duckdb"
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

- ニュースに基づく銘柄センチメントをスコアリングする:
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026,3,20))
    print(f"scored {count} codes")

- 市場レジーム（bull/neutral/bear）を判定する:
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))  # OpenAI API KEY は環境変数か引数で渡す

- リサーチ関数の利用例:
  - from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect("data/kabusys.duckdb")
    mom = calc_momentum(conn, date(2026,3,20))
    vol = calc_volatility(conn, date(2026,3,20))
    val = calc_value(conn, date(2026,3,20))

- 監査データベースを初期化する:
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn は初期化済み DuckDB 接続

- 設定値を参照する:
  - from kabusys.config import settings
    print(settings.duckdb_path)
    print(settings.is_live)

注意点:
- OpenAI を用いる関数は api_key 引数を受け取ります。引数を省略する場合は環境変数 OPENAI_API_KEY が使われます。
- ETL / AI 呼び出しは外部 API にアクセスするため、ネットワークや API 制限（レートリミット）に注意してください。
- 多くの書き込み処理は DuckDB 上で冪等に設計されています（INSERT ... ON CONFLICT DO UPDATE 等）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール（src/kabusys）を抜粋して示します。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP（センチメント）スコアリング
    - regime_detector.py     # 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - etl.py                 # ETL の公開ラッパー（ETLResult）
    - calendar_management.py # 市場カレンダーの管理 / 更新
    - news_collector.py      # RSS ニュース収集（SSRF 対策等）
    - quality.py             # データ品質チェック
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - audit.py               # 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py     # モメンタム / バリュー / ボラティリティ算出
    - feature_exploration.py # 将来リターン / IC / ランク / サマリー
  - monitoring/              # （監視用 DB 連携等を想定：src に定義あり）
  - strategy/                # （戦略実装層: シグナル生成等を想定）
  - execution/               # （発注実装層: ブローカーAPI連携 等）

（上記はコードベースから抽出した主なモジュール群です。詳細な関数・クラスは各ファイルの docstring をご参照ください。）

---

## 環境変数 / .env の扱い

- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を自動検出して .env / .env.local を読み込みます。
- 読み込み順:
  - OS 環境変数（優先） > .env.local（上書き） > .env（未設定キーのみ）
- 自動読み込みを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- .env の書式は一般的な KEY=VALUE を想定。export KEY=VAL 形式やクォート付き値、コメント行に対応しています。
- 重要: 必須トークン（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）が未設定の場合、該当機能実行時に ValueError が発生します。

---

## 開発・テスト上の注意

- DuckDB を利用する関数は外部接続を直接行わず DB 接続を引数で受け取る設計です。テスト時はインメモリ ":memory:" 接続を利用できます。
- AI / ネットワーク呼び出し（OpenAI、J-Quants、RSS）はリトライやフェイルセーフ（失敗時にゼロやスキップ）を実装している箇所が多いですが、実行環境での鍵・レート制限に注意してください。
- news_collector は SSRF や XML 攻撃対策（defusedxml、ホスト検証、最大受信サイズ）を実装しています。RSS フィード処理の堅牢性に配慮しています。

---

## 参考（主な公開 API）

- kabusys.config.settings — 環境設定アクセスオブジェクト
- kabusys.data.pipeline.run_daily_etl(conn, target_date=...)
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- kabusys.data.news_collector.fetch_rss / preprocess_text
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn)
- kabusys.research.factor_research.calc_momentum / calc_value / calc_volatility
- kabusys.data.stats.zscore_normalize(records, columns)

---

もし README に追加してほしい具体的な実行コマンド、Dockerfile / systemd ジョブの例、CI 設定やより詳しい API 仕様（関数ごとの引数説明・戻り値例）が必要であればお知らせください。必要に応じてサンプル .env.example も作成します。