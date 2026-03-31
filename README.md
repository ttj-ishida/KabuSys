# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。J-Quants や RSS、kabuステーション、OpenAI（LLM）などを組み合わせて、データ収集（ETL）、品質チェック、特徴量計算、ニュースセンチメント評価、マーケットレジーム判定、監査ログ（トレーサビリティ）といった機能を提供します。

主に研究・バックテスト・運用の各レイヤーで使えるモジュール群を含み、DuckDB をデータストアとして想定しています。

バージョン: 0.1.0

---

## 主な機能

- データ ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得して DuckDB に保存（ページネーション／冪等保存対応）
  - ETL 実行結果を ETLResult として返却・ログ出力
- データ品質チェック
  - 欠損、スパイク、重複、将来日付・非営業日データの検出（QualityIssue）
- ニュース収集 / 前処理
  - RSS 取得（SSRF 対策・gzip 対応・トラッキングパラメータ削除）
  - raw_news と news_symbols を用いた銘柄紐付け
- ニュース NLP（LLM）
  - 銘柄ごとのニュースを LLM（gpt-4o-mini）でセンチメント評価し ai_scores に書き込む（バッチ・リトライ・JSON Mode 対応）
  - ニュースウィンドウ計算（JST ベース）
- レジーム判定（市場状態）
  - ETF (1321) の 200 日 MA 乖離 + マクロニュースの LLM センチメントを合成して日次で 'bull'/'neutral'/'bear' を判定して market_regime に保存
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリ、Z スコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを作成し、発注フローを UUID でトレース可能にする初期化関数を提供

---

## 要件

- Python 3.10+
- 主な依存パッケージ（実行する機能による）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス:
  - J-Quants API（データ取得）
  - OpenAI API（ニュース NLP / レジーム判定）
  - 外部 RSS フィード（ニュース収集）
- 環境変数（下記参照）

---

## 環境変数

最低限必要な環境変数（機能により必須となるものがあります）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（fetch/save 系で使用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABUSYS_ENV: 環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルト: INFO

デフォルトの DB パス（環境変数で上書き可能）:
- DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: デフォルト `data/monitoring.db`

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（例）

1. Python 環境を用意（3.10+ を推奨）
2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - その他プロジェクトの requirements.txt があればそれに従ってください
3. リポジトリをチェックアウトし、プロジェクトルートに `.env` を作成
   - `.env.example` を参考に必要な環境変数を設定してください（本コードベースには例ファイルは含まれていませんが、上記の必須変数を設定してください）
4. DuckDB ファイル用ディレクトリを作成（必要に応じて）
   - デフォルトでは `data/kabusys.duckdb` が使用されます
5. 監査ログ専用 DB 初期化（任意）
   - Python REPL やスクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # 接続が返され、必要なテーブルが作成されます

---

## 使い方（基本例）

以下はいくつかの代表的な関数呼び出し例です。実際にはログ設定や例外処理、APIキー配置を行ってください。

- DuckDB 接続を作成して日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())
  ```

- ニュースセンチメント（ai_scores）を生成する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} codes")
  ```

- 市場レジーム判定を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログスキーマの初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn をアプリ内で利用できます
  ```

- 研究用ファクター計算:
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

注意:
- OpenAI を使う関数は API キーが必要です。引数に api_key を与えるか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API を呼ぶ関数は JQUANTS_REFRESH_TOKEN が必要です（get_id_token を内部で利用します）。
- DuckDB のテーブルスキーマは本 README に含まれていません。ETL / save 関数が前提とするテーブル群（raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / market_regime 等）を事前に作成するか、本プロジェクトに同梱のスキーマ初期化スクリプトを使ってください（コード内の save_* 関数は既存テーブルへの挿入／更新を行います）。

---

## ログ / 環境設定

- LOG_LEVEL 環境変数でログの出力レベルを制御できます（デフォルト INFO）。
- KABUSYS_ENV で環境（development / paper_trading / live）を指定し、運用ロジックの分岐に使用できます。

---

## ディレクトリ構成（主要ファイル）

（ファイルリストはコードベースから抜粋した主要モジュール）

- src/kabusys/
  - __init__.py  — パッケージ初期化（__version__）
  - config.py    — 環境変数 / .env 自動読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py       — ニュース NLP（score_news）
    - regime_detector.py— 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / get_id_token）
    - pipeline.py       — ETL パイプライン（run_daily_etl など）
    - etl.py            — ETLResult 再エクスポート
    - news_collector.py — RSS ニュース収集（fetch_rss 等）
    - quality.py        — データ品質チェック（check_missing_data 等）
    - stats.py          — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - audit.py          — 監査ログ（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ / rank

---

## 設計上の注意点 / 運用メモ

- Look-ahead bias に関して多くの関数が注意を払って設計されています（target_date 未満のみ参照、datetime.today() を直接参照しない等）。
- J-Quants API はレート制限を守るため内部で RateLimiter を実装しています。大量リクエスト時はこの制約に従ってください。
- OpenAI 呼び出しは JSON Mode を使ったパースを前提にしており、API のエラー・パース不良時は安全側のデフォルト（例: macro_sentiment=0.0）で続行する実装です。
- DuckDB への書き込みは基本的に冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を尊重する設計です。
- news_collector は SSRF 対策、レスポンスサイズ制限、XML 脆弱性対策（defusedxml）など安全対策を実装しています。

---

この README はコードベースの主要な使い方と構成をまとめたものです。より詳細な API 仕様やテーブルスキーマ、実運用のための設定例はプロジェクトのドキュメント（Design / DataPlatform / Strategy の仕様書等）を参照してください。質問や補足が必要であれば教えてください。