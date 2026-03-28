# KabuSys

日本株の自動売買・データ基盤ライブラリ（KabuSys）の README。  
このリポジトリはデータ ETL、ニュース NLP（LLM を使ったセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は日本株向けの以下機能群を提供する Python パッケージです。

- J-Quants からのデータ ETL（株価日足・財務・市場カレンダー）
- RSS ニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別 ai_score）算出
- 市場レジーム判定（ETF の MA とマクロニュースを統合）
- 研究用ファクター／特徴量計算（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / executions）の初期化ユーティリティ
- J-Quants クライアント（取得・保存ロジック、ページネーション、リトライ、レートリミット対応）

設計上の要点：
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を不用意に参照しない）
- DuckDB ベースのデータ格納・処理（SQL + Python）
- 冪等性（ETL の保存は ON CONFLICT DO UPDATE 等で安全に更新）
- フェイルセーフ（外部 API 失敗時は局所的にフォールバックして継続）

---

## 主な機能一覧（抜粋）

- データ取得・保存
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - data.pipeline.run_daily_etl（市場カレンダー → 株価 → 財務 → 品質チェックの一括実行）

- ニュース / NLP
  - data.news_collector.fetch_rss（RSS 収集、SSRF 対策、トラッキング除去）
  - ai.news_nlp.score_news（銘柄ごとのニュースをまとめて OpenAI に投げ、ai_scores テーブルへ書込）
  - ai.regime_detector.score_regime（ETF 1321 の MA とマクロニュースの LLM スコアを合成して market_regime へ保存）

- 研究 / ファクター
  - research.factor_research.calc_momentum / calc_volatility / calc_value
  - research.feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize

- データ品質・カレンダー
  - data.quality.run_all_checks（欠損・スパイク・重複・日付不整合の検出）
  - data.calendar_management.*（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）

- 監査ログ
  - data.audit.init_audit_schema / init_audit_db（監査用テーブル群の初期化）

---

## 必要条件 / 依存関係

最低限必要な依存パッケージ（コード内 import を基に抜粋）:

- Python 3.10+
- duckdb
- openai
- defusedxml

※ 実際のプロジェクトでは追加の依存（SLACK クライアント等）や開発用ツールがあるかもしれません。pyproject.toml / requirements.txt を参照してください（本スナペットに未提示）。

---

## 環境変数 / 設定

KabuSys は環境変数から設定を読み込みます（`kabusys.config.settings`）。自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数（名前は大文字）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に必要）

任意 / デフォルト付き:

- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

.env の例（.env.example を用意してください）:

```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして、プロジェクトルートへ移動。

2. 仮想環境を作成して有効化（例）:

   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 依存パッケージをインストール（例）:
   ```
   pip install -r requirements.txt
   ```
   または主要依存のみ:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数を用意:
   - プロジェクトルートに `.env` または `.env.local` を作成するか、環境変数をエクスポートしてください。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. （初回）監査 DB 初期化（任意）:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（例）

以下は主要なユーティリティの簡単な使い方例です。実運用ではログ設定、例外ハンドリング、接続管理を適切に行ってください。

- DuckDB 接続の作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（OpenAI 必須）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（OpenAI 必須）:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査テーブルの初期化（既存接続へ追加）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- ニュース RSS 取得（単体）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

---

## よく使う API（抜粋）

- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
- kabusys.data.news_collector.fetch_rss
- kabusys.ai.news_nlp.score_news
- kabusys.ai.regime_detector.score_regime
- kabusys.research.factor_research.calc_momentum / calc_volatility / calc_value
- kabusys.data.quality.run_all_checks
- kabusys.data.audit.init_audit_db / init_audit_schema

---

## ディレクトリ構成

ソースは `src/kabusys` 配下に配置されています。主なファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  : 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              : ニュース NLP（銘柄別スコア算出）
    - regime_detector.py       : 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py        : J-Quants API クライアント（取得／保存／認証）
    - pipeline.py              : ETL パイプライン（run_daily_etl 等）
    - etl.py                   : ETL 結果型の再エクスポート
    - news_collector.py        : RSS ニュース収集
    - calendar_management.py   : マーケットカレンダー管理
    - stats.py                 : 共通統計ユーティリティ（zscore_normalize）
    - quality.py               : データ品質チェック
    - audit.py                 : 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py       : ファクター計算（momentum, volatility, value）
    - feature_exploration.py   : 将来リターン / IC / 統計サマリー
  - monitoring/ (将来的な監視モジュール等)
  - strategy/ (戦略層: Signal 生成・リスク管理など)
  - execution/ (発注・ブローカー連携)

（実際のリポジトリにある全ファイルはこの一覧を参照してください）

---

## 開発・テスト時の注意

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を基準に行います。テスト時に自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。
- OpenAI / J-Quants の実 API を叩く関数はリトライやフォールバックを備えていますが、実行時の課金やレート制限に注意してください。ユニットテストでは外部呼び出しをモックしてください（コード中でもテスト差替えを想定した設計です）。
- DuckDB に対する executemany の空リスト渡しは一部バージョンで問題になるため、コードでチェックしています。DB 書き込み前に params が空でないことを確認すること。

---

## 貢献 / 連絡

バグ、改善提案、機能追加は issue を立ててください。貢献の際は既存の設計原則（ルックアヘッド回避、冪等性、フェイルセーフ）に留意してください。

---

README は以上です。必要であれば実行例や .env.example のテンプレート、CI 用コマンド、さらに詳しいモジュール別ドキュメントを追記します。どの部分を優先して詳細化しましょうか？