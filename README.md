# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログなどの機能を持ち、DuckDB をデータ層に用いる設計になっています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の用途を想定した Python モジュール群です。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と OpenAI を用いた銘柄別センチメント（ai_score）生成
- ETF（1321）やマクロニュースを組み合わせた市場レジーム（bull/neutral/bear）判定
- リサーチ用途のファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 発注 / 約定フローの監査ログ（監査テーブル初期化ユーティリティ）
- データ品質チェック（欠損・重複・スパイク・日付整合性）

設計面では「ルックアヘッドバイアスの排除」「冪等性（idempotency）」「フェイルセーフ（API 失敗時の安全な継続）」を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（取得 / 保存 / レートリミット / トークン自動リフレッシュ）
  - カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS → raw_news、SSRF / Gzip / トラッキングパラメータ対策）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ初期化（signal_events / order_requests / executions テーブル）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - ニュース NLP（gpt-4o-mini を想定した JSON mode で銘柄ごとスコア取得）
  - レジーム判定（ETF 1321 の MA200 乖離とマクロニュースセンチメントの合成）
- research/
  - ファクター計算（モメンタム/バリュー/ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、ファクターサマリ
- config.py
  - 環境変数管理（.env / .env.local 自動ロード、必須設定チェック）
- audit / execution 等の監査/実行用ユーティリティ

---

## 必要条件（依存関係）

主な依存パッケージ（抜粋）:

- Python 3.10+（typing の「|」などを使用）
- duckdb
- openai（OpenAI Python SDK v1 系想定）
- defusedxml
- （標準ライブラリ: urllib, json, logging など）

プロジェクトに付随する正確な requirements ファイルがある場合はそれに従ってください。

---

## インストール

リポジトリのルート（pyproject.toml / setup.cfg 等がある場所）で開発インストールする例:

- ローカルインストール（編集しながら使う場合）
  - python -m pip install -e .

- 依存パッケージのみをインストールする例
  - python -m pip install duckdb openai defusedxml

---

## 設定（環境変数）

KabuSys は .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索して決定）から自動読み込みします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須は README 中で明示）:

- JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン（get_id_token に使う）
- OPENAI_API_KEY         (必須 for NLP) — OpenAI API キー（score_news / score_regime の既定）
- KABU_API_PASSWORD      (必須) — kabuステーション API のパスワード（strategy/execution 実装想定）
- KABU_API_BASE_URL      （任意）デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN        (必須) — Slack 通知用トークン（monitoring 用）
- SLACK_CHANNEL_ID       (必須) — Slack の投稿先チャンネル ID
- DUCKDB_PATH            （任意）デフォルト: data/kabusys.duckdb
- SQLITE_PATH            （任意）デフォルト: data/monitoring.db
- KABUSYS_ENV            （任意）one of development, paper_trading, live（デフォルト development）
- LOG_LEVEL              （任意）DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## クイックスタート（使い方の例）

下記は主要なユースケースの簡単な利用例です。実際にはログ設定や例外処理を適切に行ってください。

- DuckDB 接続の取得例:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL の実行（株価・財務・カレンダー・品質チェック）:
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

- ニュース NLP（銘柄別 ai_score）を作成:
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を環境に設定済みなら None で可
    print("written:", n_written)

- 市場レジームスコア算出:
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査 DB 初期化（監査ログ用 DuckDB）:
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")
    # conn_audit を使って監査テーブルに書き込みが可能

- ファクター計算（研究用）:
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect("data/kabusys.duckdb")
    mom = calc_momentum(conn, target_date=date(2026,3,20))

注意点:
- OpenAI 呼び出しを含む関数（score_news, score_regime）は実行時に API キーが必要です。api_key 引数で明示するか、環境変数 OPENAI_API_KEY を設定してください。
- ETL は J-Quants API のトークン（JQUANTS_REFRESH_TOKEN）を利用します。

---

## 自動 .env 読み込みの挙動

- プロジェクトルート（.git または pyproject.toml を探索して発見）にある `.env` と `.env.local` を自動的に読み込みます。
  - 読み込み順: OS 環境 > .env.local > .env
  - `.env.local` は .env の上書きに使えます（override=True）。
- 自動ロードを無効にする: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- .env のパースは POSIX 風の形式（export 対応、コメントなど）に対応しています。

---

## ロギング / 環境モード

- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかを指定します。無効な値を設定すると例外になります。
- LOG_LEVEL は標準的なログレベル（DEBUG, INFO, ...）を指定できます。

---

## ディレクトリ構成

プロジェクトの主要なファイル/モジュール構成（src/kabusys 配下の代表）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # ニュースセンチメントの取得・検証・書き込み
    - regime_detector.py    # 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント（取得 / 保存）
    - pipeline.py          # ETL（run_daily_etl 等）
    - etl.py               # ETLResult の再エクスポート
    - news_collector.py    # RSS 収集・前処理・保存
    - calendar_management.py # 市場カレンダー管理（営業日判定等）
    - quality.py           # データ品質チェック
    - stats.py             # 汎用統計ユーティリティ（zscore_normalize）
    - audit.py             # 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py   # momentum/value/volatility 計算
    - feature_exploration.py # forward returns, IC, factor_summary, rank
  - ai/, data/, research/ のテスト／ユーティリティ群がさらに存在

（上記は抜粋です。実装は更に細分化された関数群を含みます）

---

## 開発・テスト時の補助情報

- テストでは環境自動読み込みをオフにしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants 呼び出しは外部 API を叩くため、ユニットテスト時はモック（unittest.mock.patch）で _call_openai_api や jquants_client._request 等を差し替える設計になっています。
- DuckDB を使っているためテスト用に ":memory:" を渡してインメモリ DB を使用可能です。

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス対策: 日付参照は基本的に引数の target_date を使い、date.today() を直接参照しない設計の関数が多いです（backtest / 監査の整合性確保）。
- 冪等性: J-Quants から取ったデータの保存は ON CONFLICT DO UPDATE 等で上書き/更新を行います。
- フェイルセーフ: 外部 API（OpenAI, J-Quants）失敗時は例外を全体に波及させず部分スキップする設計の箇所があります（ログを残しつつ継続）。
- セキュリティ: news_collector は SSRF 対策、XML 外部実行攻撃対策（defusedxml）等を実装しています。

---

## さらに詳しく / 貢献

- モジュール内部には詳細な docstring と設計方針コメントがあります。実装の理解や拡張は各モジュールの docstring を参照してください。
- バグ報告や機能追加、パッチは Pull Request で歓迎します。

---

README に書ききれない細かな挙動（パラメータの詳細、戻り値の厳密なスキーマ等）は各モジュールの docstring を参照してください。必要であれば README に追加したいサンプルや CLI（例: daily_etl を cron / Airflow で回す方法）を追記します。