# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。  
データ取得・ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）による銘柄スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、データ品質チェック、監査ログ（約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local 自動ロード（必要に応じて無効化可能）
  - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_BOT_TOKEN 等）

- データプラットフォーム（data）
  - J-Quants API クライアント（レート制御、トークン自動更新、ページネーション、リトライ）
  - 日次 ETL パイプライン（株価・財務・カレンダーの差分取得と保存）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS 収集、SSRF 対策、本文前処理、記事ID正規化）
  - データ品質チェック（欠損、スパイク、重複、日付整合性）
  - 監査ログ（signal_events / order_requests / executions のスキーマと初期化）
  - DuckDB へ冪等保存するユーティリティ

- AI（ai）
  - ニュース NLP（複数記事を銘柄ごとにまとめて OpenAI に投げてセンチメントを取得）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 と LLM によるマクロセンチメントを合成）

- リサーチ（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ（data.stats）

- インフラ／運用
  - DuckDB ベースのストレージ（デフォルト path: data/kabusys.duckdb）
  - 監視向け設定（PID ファイル、CPU/MEM/DISK 閾値の設定項目）
  - Slack 通知用トークン設定（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）

---

## 前提（Prerequisites）

- Python 3.10 以上（型注釈に「|」演算子を使用）
- 推奨ライブラリ（必須）
  - duckdb
  - openai
  - defusedxml
- その他（用途に応じて）
  - urllib 等の標準ライブラリを使用
  - 実運用では J-Quants API の利用登録・トークン、OpenAI API キーが必要

requirements.txt がプロジェクトに含まれていない場合は上の主要パッケージをインストールしてください。

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または: pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（デフォルト）。  
   - 自動ロードを無効化する場合は environment に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注系で使用）
   - SLACK_BOT_TOKEN: Slack Bot トークン（通知用）
   - SLACK_CHANNEL_ID: 通知先チャネル ID
   - DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

5. データベース初期化（監査ログ）
   - Python から監査ログ DB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - 注: init_audit_db は親ディレクトリを自動作成します。

---

## 使い方（基本的なコード例）

- 環境設定を参照する
  from kabusys.config import settings
  token = settings.jquants_refresh_token

- DuckDB 接続（デフォルトパスを使用）
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（run_daily_etl）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのスコアリング（OpenAI を使用）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written scores: {written}")

- レジーム（市場状況）判定
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  res = score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("regime scored", res)

- ニュース RSS を取得（単体）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["title"])

- 監査スキーマの初期化（既存接続に対して）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- J-Quants API 直接呼び出し（トークン管理は内部で行う）
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  id_token = get_id_token()
  quotes = fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)

- リサーチ系の関数利用例
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  vol = calc_volatility(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m"])

注意:
- OpenAI の呼び出しを行う関数は api_key 引数が None の場合、環境変数 OPENAI_API_KEY を参照します。
- LLM 連携は失敗に対して冗長的（フェイルセーフ）な設計で、API エラー時は該当スコアを 0 やスキップして継続します。

---

## 環境変数・自動読み込みの挙動

- ランタイム開始時、プロジェクトルート（.git または pyproject.toml が存在する上位ディレクトリ）が特定できれば自動で `.env` → `.env.local` の順に読み込みます。
- OS 環境変数は優先され、`.env.local` は `.env` の値を上書きできます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 必須変数が未設定の場合、settings プロパティ呼び出しで ValueError を送出します。

---

## 主要ファイル / ディレクトリ構成

（ルート: src/kabusys 以下）

- __init__.py
  - パッケージのエクスポート（data, strategy, execution, monitoring 等）

- config.py
  - 環境変数読み込み、settings オブジェクト（J-Quants / kabu / Slack / DB パス / モニタ閾値など）

- ai/
  - __init__.py
  - news_nlp.py: ニュースの銘柄別センチメントスコアリング（OpenAI）
  - regime_detector.py: ETF(1321) の MA200 乖離とマクロセンチメントを合成して市場レジームを判定

- data/
  - __init__.py
  - calendar_management.py: 市場カレンダー取得と営業日ロジック
  - etl.py: ETLResult のエクスポート
  - pipeline.py: 日次 ETL パイプライン、本体（run_daily_etl 等）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py: 監査ログ（シグナル・発注・約定テーブル）と初期化関数
  - jquants_client.py: J-Quants API クライアントと DuckDB への保存関数
  - news_collector.py: RSS 収集ユーティリティ（SSRF 対策、前処理、ID 正規化）

- research/
  - __init__.py
  - factor_research.py: モメンタム / ボラティリティ / バリュー ファクター計算
  - feature_exploration.py: 将来リターン / IC / 統計サマリー / ランク関数

（その他）
- strategy/, execution/, monitoring/ 等のモジュールはパッケージ export に含まれていますが、今回提示したコードベース内の詳細実装は該当サブパッケージに依存します。

---

## 運用上の注意点

- Look-ahead bias（将来情報の漏洩）対策が随所に組み込まれています。target_date の扱いや API 取得日時（fetched_at）の保持、DB クエリでの排他条件等に注意して設計されています。
- OpenAI / J-Quants など外部 API 呼び出しはリトライやバックオフ、エラーのフェイルセーフが実装されていますが、実運用では API 利用料・レート制限に注意してください。
- DuckDB での executemany に対する互換性（空リスト禁止など）への対処が実装されています。バージョン相違による挙動に注意してください。
- ニュース収集では SSRF 対策（リダイレクト検査、プライベート IP 拒否）や受信サイズ制限を実装していますが、外部フィードの取り扱いは慎重に行ってください。

---

## 開発・テスト

- テスト時に .env 自動ロードを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分は内部で分離され、ユニットテストでは該当関数をモックすることを想定しています（例: unittest.mock.patch）。

---

この README はコードベースの主要コンポーネントと利用方法の概要をまとめたものです。個々の関数や挙動の詳細は各モジュールのドキュメント文字列（docstring）をご参照ください。README の補足やサンプルスクリプトが必要であれば教えてください。