# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース NLP（OpenAI を使ったセンチメント評価）、市場レジーム判定、監査ログ（発注→約定のトレーサビリティ）、研究用ファクター計算などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株取引の自動化・データ運用を想定したコンポーネント群です。主な目的は以下です。

- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL
- RSS ニュース収集と OpenAI を用いた銘柄センチメントスコアリング
- ETF（1321）ベースの移動平均とマクロニュースを組み合わせた市場レジーム判定
- 研究（research）向けファクター計算・将来リターン / IC 分析
- 実運用向けの監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の共通方針として、バックテストにおけるルックアヘッドバイアス回避や、API 呼び出しのフェイルセーフ（失敗時は例外を投げず中立値で継続する等）を採用しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存関数、トークン自動リフレッシュ、レートリミット）
  - ニュース収集（RSS fetcher、SSRF 対策、前処理）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: OpenAI を用いた銘柄別ニュースセンチメント評価（ai_scores に書き込み）
  - regime_detector.score_regime: ETF MA200 乖離 + マクロニュース LLM 評価による market_regime 判定
- research/
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー等
- config.py
  - .env 自動読み込み（プロジェクトルートに .env / .env.local があればロード）
  - 必須環境変数取得ヘルパ（settings）

---

## 前提・要求環境

- Python >= 3.10（PEP 604 の型記法等を使用）
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- J-Quants API のリフレッシュトークン、kabu API、Slack、OpenAI API キー等の環境変数を設定すること

※実際の依存関係はプロジェクトの packaging / requirements を参照してください。最低限は上記をインストールしてください：

pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン／プロジェクトを取得

2. Python 環境を用意
   - 推奨: venv または pyenv で Python >=3.10 を使用

3. 依存パッケージをインストール
   - 例:
     pip install -e .
     または必要パッケージを個別に:
     pip install duckdb openai defusedxml

4. 環境変数 / .env ファイルを準備
   - プロジェクトルート（.git または pyproject.toml のある位置）に `.env` / `.env.local` を置くと自動で読み込まれます（config.py が自動ロードします）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用など）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
     - KABU_API_PASSWORD: kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に使用
     - OPENAI_API_KEY: OpenAI API キー（ai.score 系で利用）
   - 任意/デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

5. データベース初期化（監査ログ用）
   - 監査ログ専用 DB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - または既存の DuckDB 接続にスキーマを適用:
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn)

---

## 使い方（主要な例）

以下は代表的なモジュールの簡単な使い方です。実行は適切な環境変数と DB が準備されていることを前提とします。

- DuckDB 接続の作成（デフォルトの DB パスは settings.duckdb_path）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（カレンダー・株価・財務・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（OpenAI 必須）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を参照
  print(f"scored {n_written} codes")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数を参照

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date
  moment = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))

- J-Quants からの直接データ取得（デバッグ）
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))

- RSS フィードの取得（ニュース収集）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

注意点:
- OpenAI 呼び出しは gpt-4o-mini を JSON mode で利用する実装になっており、レスポンスのパースやリトライロジックを備えています。API キーが未設定の場合は ValueError を投げます。
- ETL 系はフェイルセーフ設計で、個別ステップの失敗は他ステップに影響しないように捕捉されています（エラー情報は ETLResult.errors に格納されます）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで利用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — .env 自動ロードを無効化（任意: 値を設定すると自動読み込みをスキップ）

.env の読み込み仕様:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に `.env` と `.env.local` を順次読み込む
- OS 環境変数が優先され、`.env.local` は `.env` の上書きに使えます
- export KEY=val 形式、クォートやインラインコメントのパース対応あり

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (存在する場合のモジュール)
- execution/ (実行/ブローカー接続などのモジュール)
- strategy/ (戦略実装用モジュール)

（README に記載した以外にも補助モジュールやユーティリティが含まれます。実際のプロジェクトルートを参照してください。）

---

## 開発メモ / 注意事項

- 型ヒントとドキュメンテーション文字列を広く使っているため、静的解析（mypy）やテストの追加が容易です。
- OpenAI / J-Quants / RSS など外部依存がある箇所は、テスト時に関数をモックする設計（_call_openai_api を差し替える等）になっています。
- DuckDB は一部バージョン固有の挙動（executemany に空リスト不可など）に配慮した実装があります。運用時は duckdb のバージョン互換性に注意してください。
- 監査ログテーブルは削除しない前提で設計されています。スキーマは冪等で初期化可能（init_audit_schema）です。

---

## 貢献 / ライセンス

- コントリビューション歓迎。Issue / Pull Request を通じて提案してください。  
- ライセンス情報はリポジトリに含まれる LICENSE ファイルを参照してください（本 README には明記していません）。

---

もし特定の機能（例: ETL の自動スケジューリング設定、kabu API 発注フロー、Slack 通知サンプル、ローカルテスト用の fixtures）について README に追記したい場合は、用途を教えてください。必要なサンプルコードや手順を追加で作成します。