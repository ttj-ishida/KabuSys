# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群。ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、リサーチ（ファクター計算・特徴量解析）、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントを備えた日本株向けのシステムライブラリです。

- J-Quants API を用いた差分 ETL（株価日足、財務、JPX カレンダー）
- DuckDB を中心としたオンプレ/ローカル向けデータ保存（冪等保存）
- ニュース収集（RSS）と前処理、OpenAI を用いた銘柄・マクロのセンチメント評価
- 研究用モジュール（モメンタム、ボラティリティ、バリュー等のファクター算出、IC計算、Zスコア正規化）
- マーケットカレンダー（営業日判定、next/prev/trading days）ユーティリティ
- 監査ログスキーマ（signal → order_request → executions の追跡）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上、ルックアヘッドバイアスを避けるため「内部で date.today() を直接参照しない」等の注意が払い込まれています。また API 呼び出しはリトライやバックオフ、フェイルセーフ（失敗時はスコア 0 で継続）等が実装されています。

---

## 機能一覧（抜粋）

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得、バックフィル・品質チェック、結果は ETLResult で返却
- J-Quants クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB 保存、冪等）
- ニュース収集 / NLP
  - fetch_rss（RSS 収集、SSRF 防御、前処理）
  - score_news（銘柄単位のニュースセンチメント計算、OpenAI）
  - score_regime（ETF 1321 の MA200 とマクロニュースを合成して市場レジーム判定）
- リサーチ
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（クロスセクション正規化）
- データ品質
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- カレンダー/営業日ユーティリティ
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
- 監査ログ
  - init_audit_schema / init_audit_db（監査テーブル・インデックスの初期化）

---

## 必要環境・依存関係

主要依存（実行に必要なパッケージ）:

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

その他、標準ライブラリの urllib 等を利用します。実際のプロジェクトでは requirements.txt を用意し pip で管理してください。

例（手動インストール）:
```
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／パッケージをインストール
   - 開発時（編集可能インストール）:
     ```
     git clone <repo>
     cd <repo>
     pip install -e .
     ```
   - 本番配布では wheel / pip install を使用

2. 必要な環境変数を設定
   - 環境変数は OS 環境変数またはプロジェクトルートの `.env` / `.env.local` を通じて自動読み込みされます（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注等で使用）
     - SLACK_BOT_TOKEN — Slack 通知用
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
   - DB パス等は省略時デフォルトが使われます（例: DUCKDB_PATH=data/kabusys.duckdb）。
   - 例 `.env`（サンプル）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=secret
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```

3. DuckDB 初期スキーマ（監査ログなど）を作成
   - 監査DBを別ファイルで初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - または既存の DuckDB 接続へ `init_audit_schema(conn)` を呼び出して追加

---

## 使い方（主要な例）

- 基本的な DuckDB 接続:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（カレンダー、株価、財務、品質チェックまで）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニューススコアリング（銘柄ごとのニューススコアを ai_scores に書き込む）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数にある前提
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  res = score_regime(conn, target_date=date(2026, 3, 20))
  ```

- RSS を取得して raw_news へ保存するフロー例
  - RSS 収集関数 `fetch_rss` は記事リストを返すので、収集 → 保存（ON CONFLICT DO NOTHING）を行う独自コードを作成してください。

- ファクター計算（研究用）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  ```

注意点:
- OpenAI 呼び出しは gpt-4o-mini を JSON mode で利用する実装になっています。API キーと利用可否（コスト）を事前に確認してください。
- ETL / ニュース処理などは API 呼び出しが含まれるため、テスト時は該当部（_call_openai_api 等）をモックすることを推奨します。
- 設計方針としてバックテスト等でのルックアヘッドバイアスを避けるため、target_date を明示して使う実装になっています。内部で date.today() を参照しない関数が多いです。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- OPENAI_API_KEY (必須 for NLP) — OpenAI API キー
- KABU_API_PASSWORD (必須 if using kabu API) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — デフォルト DB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視/モニタリング用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
- KABUSYS_ENV — 環境（development | paper_trading | live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動読み込みを無効化（テスト用）

設定は .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（ただしプロジェクトルートが特定できない場合はスキップされます）。

---

## ディレクトリ構成（要点）

（主要ファイル／モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント (score_news)
    - regime_detector.py    — 市場レジーム判定 (score_regime)
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント / DuckDB 保存
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult 再エクスポート
    - calendar_management.py— マーケットカレンダー管理
    - news_collector.py     — RSS 収集・前処理
    - quality.py            — データ品質チェック
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - audit.py              — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py    — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py— calc_forward_returns / calc_ic / factor_summary / rank
  - ai/、data/、research/ のそれぞれが公開 API を備え、研究・ETL・NLP を分離した設計

---

## 開発・テストのヒント

- OpenAI 呼び出しやネットワークリクエストは外部依存があるためユニットテストではモックを利用してください（実装側も各所でモック差替えが想定されています）。
- DuckDB のファイルを ":memory:" にしてテストを行うと副作用を避けられます（init_audit_db(":memory:") 等）。
- .env の自動読み込みはプロジェクトルートを __file__ の親から探索して行います。テスト中に環境読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ETL のログや ETLResult を監査ログとして保存することで CI / バッチの健全性を確認できます。

---

以上が README の要約です。必要であれば、実際の .env.example（全キー一覧）、requirements.txt、具体的なスキーマ定義（DDL）抜粋、コマンドラインツールラッパーの例なども追記できます。どの情報を優先して追加しますか？