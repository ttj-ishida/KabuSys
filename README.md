# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ。  
J-Quants からのデータ取得、ETL、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定トレース）などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下の目的をもつ内部ライブラリです。

- J-Quants API から株価・財務・市場カレンダー等を差分取得し DuckDB に保存する ETL パイプライン
- RSS を用いたニュース収集と LLM を使ったニュースセンチメントの算出（OpenAI）
- ETF（1321）等を用いた市場レジーム（bull/neutral/bear）判定
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order_request → executions）のスキーマ・初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計面では「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API 失敗時はゼロフォールバック等）」を重視しています。

---

## 主な機能一覧

- データ取得・ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API を扱うクライアント（kabusys.data.jquants_client）
- ニュース処理
  - RSS フィード取得・前処理（kabusys.data.news_collector）
  - ニュースを銘柄ごとにまとめ LLM（OpenAI）でスコア化（kabusys.ai.news_nlp.score_news）
- レジーム判定
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントの合成による市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等の計算（kabusys.research）
  - Z スコア正規化ユーティリティ（kabusys.data.stats.zscore_normalize）
  - IC 計算・統計サマリ（kabusys.research.feature_exploration）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック（kabusys.data.quality）
- 監査ログ（Audit）
  - 監査テーブル定義の初期化・専用 DB 作成（kabusys.data.audit.init_audit_schema / init_audit_db）

---

## セットアップ

前提
- Python 3.10 以上（型注釈に | 表記を使用）
- DuckDB を利用（ローカルファイル or インメモリ）

手順の一例:

1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 必要な代表パッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （リポジトリに requirements.txt があれば pip install -r requirements.txt を使用してください。）

3. 環境変数の設定
   - .env または .env.local をプロジェクトルートに配置すると自動読み込みされます（デフォルト）。  
     自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須の環境変数（主要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（使用する場合）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（使用する場合）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（news/regime 等で使用）
   - たとえば .env.example:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

4. DuckDB ファイルの準備（任意）
   - デフォルトの DuckDB パスは `data/kabusys.duckdb`（settings.duckdb_path で変更可）
   - 監査専用 DB 初期化:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要 API の例）

以下は簡易的なコード例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続の作成例:
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL の実行:
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())

- ニュースをスコアリングして ai_scores に保存:
  from kabusys.ai.news_nlp import score_news
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {count}")

- 市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算（モメンタム等）:
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

- 監査スキーマ初期化（既存接続に適用）:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- 設定読み取り:
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env)

注意点
- OpenAI を利用する関数は api_key 引数で上書き可能（テスト時に差し替えられる設計）。
- LLM 呼び出しは gpt-4o-mini（レスポンスを JSON mode で期待）を想定しています。API エラーは内部でリトライし、失敗時はフォールバック値（通常 0.0）を使って継続する実装です。
- 日付処理は「ルックアヘッドバイアス防止」を意識しており、内部で date.today() 等を直接参照しない実装箇所が多数あります（target_date を明示して使用してください）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for NLP/regime)
- KABU_API_PASSWORD — kabuステーション連携で使用する場合
- KABU_API_BASE_URL — kabu API base URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知
- DUCKDB_PATH — DuckDB ファイルパス (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 開発環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に `1` を設定

.env ファイルの自動ロード順序:
- OS 環境変数 > .env.local > .env
- 自動ロードはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を基準に行います。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（LLM 呼び出し、ai_scores 書き込み）
  - regime_detector.py — 市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py — マーケットカレンダー管理
  - etl.py — ETL 公開インターフェース
  - pipeline.py — 日次 ETL パイプライン
  - stats.py — 統計ユーティリティ（zscore 正規化）
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマ / 初期化
  - jquants_client.py — J-Quants API クライアント（取得/保存/認証）
  - news_collector.py — RSS 収集・前処理
- research/
  - __init__.py
  - factor_research.py — モメンタム / バリュー / ボラティリティ 等
  - feature_exploration.py — 将来リターン / IC / 統計サマリ 等

ドキュメントや設計参照は各モジュールの docstring（DataPlatform.md / StrategyModel.md に準拠した設計注記）を参照してください。

---

## 開発・テスト時のヒント

- LLM 呼び出し関数は内部で _call_openai_api のようなラッパーを使っているため、ユニットテストでは該当関数を patch / mock して外部 API を呼ばないようにできます。
- DuckDB はインメモリ接続（":memory:"）でテスト可能。audit.init_audit_db(":memory:") で簡単に初期化できます。
- .env の自動読み込みはテストで不要な場合 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- jquants_client 内はネットワークリトライやトークン自動リフレッシュのロジックがあるので、エンドツーエンドテストではモック化を推奨します。

---

## ライセンス・貢献

（ここにライセンス情報・貢献手順を追加してください）

---

この README はソースコードの docstring と実装に基づいて作成しています。運用や本番環境で使用する前に、必須環境変数・API キーの管理、接続先・パーミッション設定、監査・安全対策（例: SSRF・XML パース保護・レスポンスサイズ制限等）を確認してください。