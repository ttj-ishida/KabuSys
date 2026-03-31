# KabuSys

日本株向けのデータプラットフォーム + 研究・AI スコアリング・監査ログを含む自動売買支援ライブラリです。DuckDB をデータストアとして用い、J-Quants API からの ETL、ニュース収集・NLP（OpenAI）、ファクター計算、品質チェック、監査ログ（発注→約定トレース）などを提供します。

主な想定用途
- 日次 ETL（株価・財務・市場カレンダー）を自動実行してデータレイクを更新
- ニュース記事のセンチメント分析（銘柄ごと）と市場レジーム判定（MA + マクロニュース）
- 研究用ファクター計算・特徴量探索（モメンタム / バリュー / ボラティリティ 等）
- 発注から約定までの監査ログ（トレーサビリティ）テーブルの初期化

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（OS 環境変数優先、プロジェクトルート判定）
  - 必須設定の明示的検証

- データ ETL（kabusys.data.pipeline）
  - J-Quants API から差分取得（ページネーション・リトライ・レート制御）
  - raw_prices / raw_financials / market_calendar への冪等保存
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、前処理、SSRF対策、トラッキングパラメータ除去、冪等保存

- AI スコアリング（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini）で評価して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321) の 200 日 MA 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定

- 研究ツール（kabusys.research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Z スコア正規化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル DDL と初期化ユーティリティ
  - 監査用 DuckDB データベース初期化

- J-Quants クライアント（kabusys.data.jquants_client）
  - ID トークン管理、自動リフレッシュ、レート制御、リトライ、保存関数（raw_prices 等）

---

## 前提条件・依存関係

最低限の依存（実際の pyproject/requirements に従ってください）:
- Python 3.10+
- duckdb
- openai
- defusedxml

（例）pip インストール例:
pip install duckdb openai defusedxml

---

## 環境変数

以下は主に config.Settings から参照される環境変数です。`.env` / `.env.local` をプロジェクトルートに置くと自動読み込みされます（OS 環境変数が優先）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード（発注等を行う場合）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必要な場合）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必要な場合）

任意（デフォルトあり）
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : environment (development, paper_trading, live)（デフォルト: development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用可能）

簡易 .env 例（プロジェクトルートの .env に保存）:
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

注意: .env のパーシングは Bash ライクな形式（export を許容、クォートの解釈、インラインコメント考慮）に対応しています。

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate

3. 依存ライブラリをインストール
   pip install -r requirements.txt
   または最低限:
   pip install duckdb openai defusedxml

4. 環境変数を設定
   プロジェクトルートに `.env`（およびローカル用に `.env.local`）を作成。上記参照。

5. DuckDB 用ディレクトリを作成（必要に応じて）
   mkdir -p data

---

## 使い方（サンプル）

以下はライブラリ API の簡単な使い方例です。各関数は DuckDB 接続（duckdb.connect(...) の返り値）を受け取ります。

- 日次 ETL を実行する
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュースセンチメントを計算して ai_scores に保存（OpenAI API キーを環境変数に設定）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用の DuckDB を初期化（order/signals テーブルを作成）
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って発注ログ格納などが可能

- J-Quants から株価を直接取得（テスト・スクリプト用途）
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(date_from=date(2026, 1, 1), date_to=date(2026, 3, 20))
  print(len(quotes))

注意点
- OpenAI 呼び出しは API キーを引数で渡すことも、環境変数 OPENAI_API_KEY を使うことも可能です。
- DuckDB のトランザクションや接続オプションは呼び出し側で管理できます。多くの関数は BEGIN/COMMIT を内部で使う場合があります。
- ETL / API 呼び出しはネットワーク・API 制限を伴うため実運用ではレートやリトライ挙動に注意してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュール）

- __init__.py
  - パッケージ公開 API（data, strategy, execution, monitoring を想定）

- config.py
  - 環境変数の自動読み込み・設定取得ユーティリティ（Settings クラス）

- ai/
  - __init__.py
  - news_nlp.py
    - news を銘柄別に集約し OpenAI でセンチメントを計算、ai_scores テーブルへ書き込む（score_news）
  - regime_detector.py
    - ETF(1321) の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に保存（score_regime）

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント、データ取得 & DuckDB 保存関数
  - pipeline.py
    - 日次 ETL のエントリポイント（run_daily_etl）と個別 ETL ジョブ
  - etl.py
    - ETLResult 型の再エクスポート
  - news_collector.py
    - RSS 取得・前処理・SSRF対策・raw_news への保存
  - calendar_management.py
    - market_calendar の更新 / 営業日判定ユーティリティ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py
    - 共通統計ユーティリティ（zscore_normalize）
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）DDL と初期化ユーティリティ

- research/
  - __init__.py
  - factor_research.py
    - momentum/value/volatility 等ファクター計算
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリー、rank 等

- （その他）
  - strategy, execution, monitoring は __init__ で公開を想定していますが、今回の抜粋には含まれていない可能性があります。

---

## 開発・運用上の注意

- Look-ahead バイアス対策
  - 各 AI / ETL / 研究モジュールは内部で date.today() を盲目的に参照しない設計（target_date を明示）になっています。バックテスト時は必ず適切な target_date を渡してください。

- 環境読み込み
  - .env / .env.local の読み込みルール: OS 環境 > .env.local > .env。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- OpenAI / J-Quants の呼び出しは課金・レート制限があるため、本番環境ではキー管理と呼び出し頻度を注意してください。

- DuckDB の executemany に関する注意
  - 一部コードは DuckDB のバージョン差異（executemany の空リスト不可等）を考慮しています。DuckDB のバージョン互換性に注意してください。

---

もし README にサンプルの .env.example や、より詳しい API ドキュメント（関数シグネチャ、戻り値のスキーマ、テーブルスキーマ）を追加したい場合は、どの部分を優先するか教えてください。