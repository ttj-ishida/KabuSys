# KabuSys

日本株自動売買プラットフォームのコアライブラリ（ライブラリ的に分割されたデータ基盤・リサーチ・AI・監査・ETL 等を含む）。  
このリポジトリは、J-Quants / kabuステーション / OpenAI などの外部サービスと連携して、データ取得・品質管理・特徴量作成・ニュースセンチメント・市場レジーム判定・監査ログ・ETL を行います。

## 主要機能
- 環境設定管理（.env/.env.local 自動読込、必須設定の検証）
- J-Quants API クライアント（株価・財務・市場カレンダー取得、トークン自動リフレッシュ、レート制御・リトライ）
- ETL パイプライン（差分取得・保存・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev/trading days）
- ニュース収集（RSS → raw_news、SSRF や XML 攻撃対策、トラッキング除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメント算出、バッチ処理・リトライ）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ（Zスコア等）
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- 監査ログ（signal → order_request → execution のトレーサビリティテーブルと初期化ユーティリティ）
- DuckDB の保存/スキーマ操作ユーティリティ群

## セットアップ手順（ローカル開発向け）

前提
- Python 3.9+（ライブラリの型注釈等に合わせて推奨）
- DuckDB が Python 環境にインストールされていること

1. リポジトリをクローンしてパッケージをインストール
   - 開発インストール例:
     - pip:
       - pip install -r requirements.txt など（requirements.txt があれば）
       - または直接 editable install:
         python -m pip install -e .
     - poetry を使う場合は pyproject.toml に従ってください。

2. 必要な Python パッケージ（主な依存）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリのみで動作する部分も多いですが、上記は動作に必要です）

3. 環境変数の準備
   - プロジェクトルートに `.env`（と必要に応じて `.env.local`）を置くと自動で読み込まれます（自動ロードは CWD に依存せずプロジェクトルートを探索します）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で便利）。
   - 主要な必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI 呼び出しに使用（各関数で引数として渡すことも可能）
   - 任意/設定例:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

4. データベース初期化（監査ログ等）
   - 例: 監査ログ専用 DB を初期化
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存の DuckDB 接続に監査スキーマのみ追加する場合:
     ```python
     conn = duckdb.connect("data/kabusys.duckdb")
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```

## 使い方（主要な API と実行例）

- ETL（日次一括処理）
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別 AI スコア書き込み）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で渡す
  score_news(conn, target_date=date(2026,3,20))
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  ```

- マーケットカレンダー/営業日判定
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  is_trade = is_trading_day(conn, date(2026,3,20))
  nxt = next_trading_day(conn, date(2026,3,20))
  ```

- J-Quants API 直接呼び出し（データ取得 / 保存）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
  saved = save_daily_quotes(conn, records)
  ```

- ニュース収集（RSS フェッチ）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数でキーを指定できます。指定がない場合は環境変数 OPENAI_API_KEY を参照します。
- DuckDB に対する一部の executemany 処理は空のリストを許容しないため、呼び出しコード側で空チェックがされています（パッケージ自体で考慮済み）。
- LLM 呼び出し時のフェイルセーフ: API 失敗やパースエラーは基本的に例外を投げず安全側のデフォルト値（0.0 等）で継続する設計です。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 管理（自動ロード・保護・必須チェック）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント算出と ai_scores 書き込みロジック
    - regime_detector.py — マーケットレジーム判定（MA200 + マクロLLM）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得/保存/認証/レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py — ETL の公開インターフェース（再エクスポート）
    - calendar_management.py — マーケットカレンダー管理 / 営業日ユーティリティ
    - news_collector.py — RSS 収集と前処理（SSRF・XML 対策）
    - stats.py — zscore_normalize 等の汎用統計ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログスキーマ定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ等

（上記は主要モジュールの抜粋です。実際のコードベースにはさらに補助的なコードやユーティリティが含まれます。）

## 追加メモ / ベストプラクティス
- 自動環境読込:
  - .env（一般設定） → .env.local（ローカルで上書き）という優先度で読み込まれます。
  - OS 環境変数は保護され、.env.local の上書きからも守られます（必要に応じて override 挙動あり）。
- Look-ahead bias 対策:
  - 多くの関数は内部で date.today() や datetime.today() を直接参照せず、呼び出し側から target_date を渡す設計です。バックテストでの使用時は適切な時点のデータだけを使うようにしてください。
- テスト:
  - LLM / ネットワーク呼び出しはモック可能な設計（内部呼び出し関数を patch してテスト）になっています。
- ログレベル:
  - 環境変数 `LOG_LEVEL` でログレベルを制御可能です。開発時は DEBUG が便利です。

---

何か特定のモジュール（例: news_nlp のプロンプト調整、jquants_client のページネーションや認証フロー、ETL のメトリクス拡張など）について詳しいドキュメントや利用例が必要であれば教えてください。README の例や手順をその用途に合わせて追記します。