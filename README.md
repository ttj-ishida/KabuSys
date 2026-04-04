# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリセットです。  
ETL（J-Quants からの株価・財務・カレンダ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント分析）、リサーチ用ファクター計算、監査ログ（発注→約定までのトレーサビリティ）などを提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの日次株価（OHLCV）・財務データ・市場カレンダーの差分取得・保存（DuckDB）
  - 差分取得／バックフィル／品質チェックを含む日次パイプライン（run_daily_etl）
- ニュース収集・NLP
  - RSS フィード収集と前処理（URL 正規化・SSRF 対策・XML 安全パース）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント計算（score_news）
  - マクロニュース＋ETF（1321）の MA200乖離を組み合わせた市場レジーム判定（score_regime）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）・統計サマリ、Zスコア正規化など
- データ品質チェック
  - 欠損・異常スパイク・重複・日付不整合検出（QualityIssue を返す）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブル作成・初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注を防止
- 環境設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ラッパー（settings）

---

## 動作環境・依存

- Python 3.10 以上（typing の union 演算子 `|` を利用）
- 主な依存パッケージ（実行環境に応じてインストールしてください）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで実装されている部分も多いです）
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

必要な環境変数（主要）
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD：kabuステーション API のパスワード（必須）
- OPENAI_API_KEY：OpenAI API キー（score_news / score_regime 実行時に必要）
- KABU_API_BASE_URL：kabu API の base URL（省略可、デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID：通知用（省略可）
- DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH 等：各種ファイルパスは設定可能

※詳細は kabusys.config.Settings のプロパティを参照してください。

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従ってください）

3. リポジトリのクローン（プロジェクトルートに .git または pyproject.toml があると自動で .env を読み込みます）
   - git clone <repo>
   - cd <repo>

4. 環境変数を設定（.env をプロジェクトルートに配置することを推奨）
   - 例: .env
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_password
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb

   - サポートされる .env の書式：
     - KEY=VAL、export KEY=VAL、シングル/ダブルクォート、行頭の # はコメント
     - 複雑なクォートやエスケープにも対応（kabusys.config._parse_env_line）

   - 自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定

---

## 使い方（簡単な例）

以下はライブラリを Python REPL / スクリプトから利用する例です。

- DuckDB 接続を準備して日次 ETL を実行する
  - Python スクリプト例:
    - from datetime import date
      import duckdb
      from kabusys.data.pipeline import run_daily_etl
      conn = duckdb.connect("data/kabusys.duckdb")
      result = run_daily_etl(conn, target_date=date(2026, 3, 20))
      print(result.to_dict())

- ニュースセンチメント（銘柄別）を計算する
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print("written:", n_written)

  - 注意: OPENAI_API_KEY が必要。引数 api_key に直接渡すことも可能。

- 市場レジームをスコア化して書き込む
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログ用の DuckDB を初期化
  - from pathlib import Path
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db(Path("data/audit.duckdb"))
    # conn を使って以後の監査テーブルが利用可能になります

- ニュース RSS を取得（単体テストやカスタム実行）
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
    articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
    for a in articles[:5]:
        print(a["id"], a["datetime"], a["title"])

---

## .env の自動読み込みについて

- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に
  - .env を先に読み込み（既存 OS 環境変数を上書きしない）
  - 次に .env.local を読み込み（上書き許可）
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須の環境変数が参照された場合は kabusys.config._require が ValueError を投げます（例: JQUANTS_REFRESH_TOKEN が未設定のとき）。

.env の小さな例:
- JQUANTS_REFRESH_TOKEN=your_refresh_token
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- KABU_API_PASSWORD=...

---

## ディレクトリ構成（概要）

リポジトリは src レイアウトになっています。主要なモジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # ニュースセンチメント（銘柄別）処理
    - regime_detector.py    # マクロ + ETF(MA) を用いた市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py                 # ETLResult エクスポート
    - pipeline.py            # 日次 ETL パイプライン
    - stats.py               # Zスコア正規化など統計ユーティリティ
    - quality.py             # データ品質チェック群
    - audit.py               # 監査ログテーブル初期化ユーティリティ
    - jquants_client.py      # J-Quants API クライアント + DuckDB 保存ロジック
    - news_collector.py      # RSS 収集・前処理・保存ロジック
  - research/
    - __init__.py
    - factor_research.py     # Momentum/Value/Volatility ファクター計算
    - feature_exploration.py # 将来リターン計算 / IC / 統計サマリ

---

## 開発者向けメモ / 注意点

- Look-ahead バイアス対策: 多くの関数は内部で datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を渡す設計です。バックテスト等で使用する際は target_date を明示的に指定してください。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定したプロンプトと JSON mode を利用
  - レート制限・再試行（指数バックオフ）を実装済み。API 失敗時はフェイルセーフ動作（多くのケースで 0 や空スコアを返す）をする設計です
- J-Quants クライアント:
  - レートリミッタ（120 req/min）と 401 → トークン自動リフレッシュ、ページネーション対応を実装
- ニュース収集:
  - SSRF 対策、受信サイズ上限、defusedxml による安全パースなどセキュリティ考慮済み
- DuckDB への INSERT は ON CONFLICT DO UPDATE（冪等保存）を用いています

---

この README はコードベースの概要をまとめたものです。各モジュールの詳細な挙動やパラメータは、該当する Python ファイル（kabusys/data/*.py、kabusys/ai/*.py、kabusys/research/*.py）内のドキュメンテーションストリング（docstring）を参照してください。問題や改善点があれば issue を立ててください。