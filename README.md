# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群。  
ETL（J-Quants からのデータ取得）、ニュース収集・AIベースのニュースセンチメント、ファクター計算、監査ログ（トレーサビリティ）、マーケットカレンダー管理などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータプラットフォームとリサーチ・自動売買の基礎機能をまとめたパッケージです。主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダー取得（ETL）
- RSS からのニュース収集と記事の前処理 / 保存
- OpenAI（LLM）を使ったニュースセンチメント・市場レジーム判定
- ファクター（モメンタム、ボラティリティ、バリュー等）の計算と特徴量探索
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注・約定までの監査ログ（トレーサビリティ）テーブル定義・初期化
- マーケットカレンダー管理（営業日判定／次営業日取得等）

設計上の特徴：
- DuckDB を主な永続ストアとして利用
- Look-ahead bias を避ける設計（日時の取得やクエリはバックテストで安全に使えるよう配慮）
- API 呼び出しに対する堅牢なリトライ・レート制御
- .env / 環境変数による設定管理（自動ロード機能あり）

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env / 環境変数の読み込み、Settings によるアクセス
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 + DuckDB への保存）
  - pipeline: 日次 ETL（run_daily_etl、個別 ETL ジョブ）
  - news_collector: RSS 取得・テキスト前処理・raw_news 保存
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - quality: データ品質チェック
  - audit: 監査ログ用テーブル定義・初期化（init_audit_db / init_audit_schema）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM に送って銘柄ごとの ai_score を生成し ai_scores に保存
  - regime_detector.score_regime: ma200 とマクロ記事の LLM センチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: forward return / IC / factor summary 等

---

## 要件（推奨）

- Python 3.10+
- DuckDB
- openai (OpenAI Python SDK)
- defusedxml
- （実行時）インターネットアクセス（J-Quants / RSS / OpenAI）
- 追加パッケージ: urllib（標準）、その他標準ライブラリ

例（最低限の pip インストール例）:
pip install duckdb openai defusedxml

プロジェクトでは pyproject.toml / requirements.txt がある想定ですが、無い場合は上記を参考に必要パッケージを追加してください。

---

## セットアップ手順

1. リポジトリをクローンしてインストール（開発モード推奨）
   - git clone <repo>
   - cd <repo>
   - python -m pip install -e .

2. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API のパスワード
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時）
   - デフォルトのデータベースパスは settings.duckdb_path（デフォルト "data/kabusys.duckdb"）および settings.sqlite_path（"data/monitoring.db"）です。

例 .env（テンプレート）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

3. DuckDB 初期化（任意）
   - 監査ログ用 DB を初期化する場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - または既存の DuckDB に接続してスキーマを作る:
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)

---

## 使い方（短いサンプル）

注意: すべての関数は Look-ahead バイアスを避ける設計になっています。target_date を明示して実行することを推奨します。

- 基本的な接続と設定取得
  python
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())

- ニュースセンチメント（AI）スコアリング
  python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を None にすると環境変数 OPENAI_API_KEY を使用
  print(f"scored {n} codes")

- 市場レジーム判定（MA200 + マクロニュース）
  python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB 初期化（別ファイル）
  python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")

- ファクター計算例
  python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  recs = calc_momentum(conn, date(2026, 3, 20))
  # recs は { "date":..., "code":..., "mom_1m":..., ... } のリスト

- カレンダー関連
  python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  is_trading = is_trading_day(conn, date(2026,3,20))
  next_day = next_trading_day(conn, date(2026,3,20))

---

## 重要な注意点 / 実運用向けヒント

- OpenAI 利用部分（news_nlp / regime_detector）は API キーが必須。API 呼び出し時はレートや課金に注意してください。
- J-Quants API 呼び出しはレート制限とトークンリフレッシュを組み込んでありますが、認証情報（リフレッシュトークン）は安全に管理してください。
- DuckDB による executemany に関してバージョン依存の挙動（空リスト不可など）があるため、ETL 内では空パラメータの扱いに注意しています。ライブラリ組み込みの関数をそのまま使うことを推奨します。
- テスト時に自動 .env ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ニュース収集の RSS 処理は SSRF 対策や受信サイズ上限、XML パースの安全対策（defusedxml）を組み込んでいます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py            # ニュースセンチメント（AI）スコアリング
  - regime_detector.py     # 市場レジーム判定（MA200 + マクロLLM）
- data/
  - __init__.py
  - jquants_client.py      # J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py            # ETL パイプライン（run_daily_etl など）
  - etl.py                 # ETLResult の再エクスポート
  - news_collector.py      # RSS 収集・記事整形
  - calendar_management.py # 市場カレンダー管理（営業日判定等）
  - quality.py             # データ品質チェック
  - stats.py               # 統計ユーティリティ（zscore_normalize）
  - audit.py               # 監査ログテーブル（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py     # モメンタム・バリュー・ボラティリティ計算
  - feature_exploration.py # 将来リターン・IC・統計サマリーなど

---

## 開発 / テストについて

- OpenAI 呼び出しはモジュール内部の _call_openai_api をモックしてテスト可能です（news_nlp / regime_detector の各関数で patch 可能）。
- network I/O（J-Quants, RSS）もモック可能なように設計されています（jquants_client._request や news_collector._urlopen 等）。
- 自動 .env ロードはプロジェクトルートの .env / .env.local を対象に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。

---

必要に応じて README に追記できます（例: 詳細な API リファレンス、SQL スキーマ、バックテストでの注意点、運用フロー図など）。追加したい項目があれば教えてください。