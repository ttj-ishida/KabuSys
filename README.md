# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群です。  
ETL・データ品質チェック・ニュース収集・AIによるニュースセンチメント・市場レジーム判定・リサーチ（ファクター計算）・監査ログ（トレーサビリティ）などの機能を提供します。

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーなどを差分で取得して DuckDB に永続化する ETL パイプライン
- RSS ベースのニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント解析（AI スコア）
- ETF を用いた市場レジーム判定（MA 乖離 + マクロニュースセンチメントの合成）
- 研究用途のファクター計算（モメンタム・ボラティリティ・バリューなど）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマ（信号→発注→約定のトレーサビリティ）
- 環境変数 / .env の自動読み込み機構

設計方針として「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗時の継続）」を重視しています。

---

## 主な機能一覧

- データ取得・保存
  - J-Quants クライアント（差分取得、ページネーション、リトライ、トークン自動更新）
  - DuckDB への保存（ON CONFLICT DO UPDATE による冪等保存）
- ETL
  - 日次 ETL（market calendar → prices → financials → 品質チェック）: run_daily_etl
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質
  - 欠損、スパイク、重複、日付不整合チェック（run_all_checks）
- ニュース収集
  - RSS フィード取得・前処理・SSRF 対策・トラッキングパラメータ除去（news_collector）
- AI（OpenAI）関連
  - 銘柄ごとのニュースセンチメント計算と ai_scores 書き込み（score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント合成）: score_regime
  - リトライ / エラーハンドリング / JSON モード処理
- リサーチ（research）
  - モメンタム / ボラティリティ / バリュー算出（calc_momentum, calc_volatility, calc_value）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等
  - zscore 正規化ユーティリティ（data.stats.zscore_normalize）
- 監査（audit）
  - signal_events / order_requests / executions を含む監査 DB 初期化（init_audit_schema / init_audit_db）
- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）、必須値取得ユーティリティ（kabusys.config.settings）

---

## セットアップ手順

前提: Python 3.10 以上を推奨（ソースは型ヒントに Python 3.10+ 機能を使用しています）。

1. リポジトリをクローン（例）
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール  
   必要なパッケージ例:
   - duckdb
   - openai
   - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```

   ※ 実際の requirements.txt / pyproject.toml がある場合はそちらを使用してください。

4. 環境変数（.env）を準備  
   プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   最低限設定が必要な環境変数:
   - JQUANTS_REFRESH_TOKEN（必須） — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD（必須） — kabuステーション用パスワード（発注機能を使う場合）
   - OPENAI_API_KEY（AI 機能を使う場合）
   推奨/任意:
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知等）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
   - その他監視設定やログレベル：KABUSYS_ENV, LOG_LEVEL 等

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

5. （任意）データベース用ディレクトリを作成
   ```
   mkdir -p data
   ```

---

## 使い方（主要な API 例）

以下はライブラリを直接インポートして使う例です。DuckDB 接続には `duckdb.connect()` を使用します。

- 日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコアを計算して ai_scores テーブルへ書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジームをスコアリングして market_regime テーブルへ保存
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ DB を初期化して接続を得る
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn を使って監査テーブルへアクセス
  ```

- RSS を取得する（ニュース収集コンポーネントの一部）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- 環境設定の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意:
- AI 系 API（score_news, score_regime）は OpenAI API キー（OPENAI_API_KEY または api_key 引数）が必要です。
- J-Quants 関連は JQUANTS_REFRESH_TOKEN（または明示的な id_token）を必要とします。

---

## 自動環境読み込みについて

kabusys.config モジュールは、パッケージの配置場所からプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、その下の `.env` と `.env.local` を自動で読み込みます（優先順: OS 環境 > .env.local > .env）。自動読み込みを無効化するには環境変数を設定します:

```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

必須環境変数を参照する際は settings のプロパティが ValueError を投げます（必要に応じて .env を作成してください）。

---

## ディレクトリ構成

主要なファイル / モジュールは以下のようになっています（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py            — 銘柄ごとのニュースセンチメント解析（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 他）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 収集 / 前処理 / 保存ロジック
    - quality.py             — データ品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - audit.py               — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/、data/、research/ 以下のユーティリティ群がそれぞれの責務を分離

---

## 注意点 / ベストプラクティス

- ルックアヘッドバイアス回避のため、関数群は日付引数（target_date）を外部から与える設計になっています。テストやバックテストでは必ず target_date を指定してください。
- OpenAI 呼び出しは外部ネットワーク依存かつ課金が発生します。ユニットテスト時は relevant internal callables をモック（例: kabusys.ai.news_nlp._call_openai_api）してください。
- DuckDB への executemany に空リストを渡すとバージョン依存でエラーになる可能性があるため、該当箇所は空チェックがあります（パイプライン内参照）。
- news_collector は SSRF 対策・XML パースの安全化（defusedxml）などのセキュリティ考慮を行っています。外部 RSS の扱いは慎重に行ってください。

---

## 追加情報 / 貢献

- ドキュメントやテスト、CI の追加や実運用でのログ/監視設定の強化を歓迎します。
- バグ報告・機能改善は Issue を作成してください。

---

README は以上です。必要であれば、インストール用の requirements.txt や利用例のスクリプト、.env.example のテンプレートを作成します。どの形式がよいか教えてください。