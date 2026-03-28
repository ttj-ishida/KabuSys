# KabuSys

日本株向け自動売買・データプラットフォームライブラリ。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、因子計算・リサーチ、監査ログ（発注/約定トレース）などを提供します。

---

## 主な特徴（機能一覧）

- 環境変数/設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須キー未設定時の明示的エラー
  - 実行環境フラグ（development / paper_trading / live）・ログレベル検証

- データプラットフォーム（DuckDB ベース）
  - J-Quants API クライアント（差分取得、ページネーション、リトライ、レート制御、ID トークン自動リフレッシュ）
  - ETL パイプライン（prices / financials / calendar の差分取得、品質チェック）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - マーケットカレンダー管理（営業日判定、前後営業日取得）
  - ニュース収集（RSS、SSRF対策、前処理、冪等保存）
  - 監査ログスキーマ初期化（signal/events → order_requests → executions のトレーサビリティ）

- AI（OpenAI）
  - ニュースセンチメント集約（gpt-4o-mini を利用する JSON モードで銘柄ごとにスコア化）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロ記事センチメント合成）
  - API 呼び出しでのリトライ・フェイルセーフ設計

- リサーチ / ファクター
  - モメンタム / バリュー / ボラティリティ / 流動性などのファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計要約
  - クロスセクション Z スコア正規化ユーティリティ

---

## 要件（推奨）

- Python >= 3.10
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実際のプロジェクトでは requirements.txt を用意してください。上記は主要依存の抜粋です。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone …（プロジェクトルートに .git / pyproject.toml があると自動で .env をロードします）

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージをインストール
   - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabu API の base URL（任意、デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャネルID（必須）
     - OPENAI_API_KEY: OpenAI 呼び出し用（score_news / score_regime の場合に必要）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development|paper_trading|live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
   - 自動ロードを無効化する場合:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. データベース初期化（監査ログ用など）
   - 例: 監査ログ専用 DB を作成
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要な例）

※ 以下はライブラリ API を直接呼び出す例。

- 設定の参照
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env)

- DuckDB 接続作成
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  - 戻り値は ETLResult（取得・保存件数、品質チェック結果、エラーメッセージを含む）

- ニュース収集（RSS を取得して処理する一部機能）
  from kabusys.data.news_collector import fetch_rss, preprocess_text
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      text = preprocess_text(a["title"] + " " + a["content"])
      # DB に保存する等の処理

- ニュース NLP スコアリング（OpenAI が必要）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定しておく

  - 関数は ai_scores テーブルへスコアを書き込む。戻り値は書き込んだ銘柄数。

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必要

- 研究用関数（因子計算・IC 等）
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
  factors = calc_momentum(conn, date(2026, 3, 20))
  zf = zscore_normalize(factors, ["mom_1m", "mom_3m", "ma200_dev"])

- 監査ログスキーマ初期化（既存の接続へテーブルを追加）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- J-Quants 直接呼び出し（トークン取得・API 呼び出し）
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使用
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))

---

## 重要な設計上の注意点

- ルックアヘッドバイアス防止
  - モジュールの多くは date / target_date を明示的に受け取り、datetime.today() を内部参照しない実装になっています。バックテストや再現性のため、target_date を明示して呼び出してください。

- 冪等性
  - ETL 保存処理は ON CONFLICT DO UPDATE などで冪等に設計されています（部分失敗時に既存データを不適切に上書きしない工夫あり）。

- フェイルセーフ
  - AI 呼び出し失敗時はスコアを 0 にフォールバックする、または空スキップして処理を継続する設計です（システムの停止を避ける）。

- セキュリティ対策
  - RSS 取得での SSRF 対策、defusedxml の利用、レスポンス上限の設定などを備えています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースの OpenAI によるセンチメント解析
    - regime_detector.py               — ETF MA + マクロニュースでの市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（取得・保存）
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETL 再エクスポート（ETLResult）
    - calendar_management.py           — 市場カレンダー管理（営業日判定）
    - news_collector.py                — RSS ニュース収集
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査ログ（監査用テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算（momentum/value/volatility）
    - feature_exploration.py            — 将来リターン・IC・統計サマリー
  - research/*（他ユーティリティ）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない場合
  - パッケージはプロジェクトルート（.git or pyproject.toml）を基準に .env を自動読み込みします。テストなどで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI 呼び出しで APIKey を使いたい
  - score_news / score_regime などは api_key 引数を受けます。None の場合は環境変数 OPENAI_API_KEY を使用します。API 呼び出しは gpt-4o-mini（JSON mode）を想定しています。

- DuckDB スキーマ
  - ETL の前にスキーマ（raw_prices, raw_financials, market_calendar など）が準備されていることが前提です。監査ログ用スキーマは kabusys.data.audit.init_audit_db / init_audit_schema で初期化できます。

---

README の内容は実装の要点を抜粋したものです。運用や本番導入前には、環境変数の管理、API レート制御、資格情報の安全な保管（Vault 等）を必ず検討してください。必要であれば README に追加すべきサンプル .env.example や requirements.txt、起動スクリプトのテンプレートを作成します。必要なら依頼してください。