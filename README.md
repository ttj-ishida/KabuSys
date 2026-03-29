# KabuSys — 日本株自動売買プラットフォーム

KabuSys は日本株のデータパイプライン、研究（リサーチ）、ニュース NLP、AI を用いた市場レジーム判定、監査ログ・発注トレーサビリティなどを統合した自動売買基盤のライブラリ群です。ETL による J-Quants データ取得、DuckDB を用いたローカル DB 管理、OpenAI を用いたニュースセンチメント解析などを提供します。

## 主な機能

- データプラットフォーム
  - J-Quants API からの株価（日足）・財務データ・JPX カレンダー取得（差分取得・ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT で更新）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - ニュース収集（RSS）と前処理、記事と銘柄の紐付け
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）
  - ETL パイプライン（run_daily_etl 等）

- AI / ニュース解析
  - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント評価（score_news）
  - マクロ指標（ETF 1321 の 200 日 MA 乖離）とマクロニュースセンチメントを合成して市場レジーム判定（score_regime）

- リサーチ（ファクター）
  - Momentum / Value / Volatility 等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターンや IC（Information Coefficient）や統計サマリの計算ユーティリティ

- 監査（Audit） & 実行ログ
  - シグナル / 発注要求 / 約定 の監査テーブル定義と初期化（init_audit_schema / init_audit_db）
  - 発注の冪等性やトレーサビリティを確保するスキーマ

- 安全性・運用面の配慮
  - J-Quants のレート制御（120 req/min）とリトライ処理
  - RSS 収集の SSRF 対策・gzip サイズチェック・XML 安全パーサ（defusedxml）
  - OpenAI API 呼び出しでのリトライとフェイルセーフ（失敗時は無害なデフォルト）

---

## 必要条件 / 依存関係

- Python 3.10+
  - 型注釈（| 演算子）や __future__.annotations の使用から 3.10 以上を想定しています
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib, json, datetime 等を使用

（プロジェクト配布時は pyproject.toml / requirements.txt を参照してください）

---

## 環境変数（設定項目）

以下の環境変数が使用されます（最低限の必須項目は README 内で明示）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack のチャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化（テスト時に利用）

パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。プロジェクトルートは .git または pyproject.toml を基準に探索します。

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （他にテスト用や開発用の依存があれば requirements.txt / pyproject.toml を参照）

4. 環境変数設定
   - プロジェクトルートに `.env` を作成（.env.example を参考に必要なキーを設定）
   - 例:
     - JQUANTS_REFRESH_TOKEN=xxxx
     - OPENAI_API_KEY=xxxx
     - KABU_API_PASSWORD=xxxx
     - SLACK_BOT_TOKEN=xxxx
     - SLACK_CHANNEL_ID=xxxx

5. DuckDB データベース / 監査 DB の初期化
   - 監査用 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要 API と実行例）

以下は簡単な Python スニペット例です。実行は仮想環境内で行ってください。

- DuckDB 接続の取得（パスは設定に合わせて置換）

  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（run_daily_etl）

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（AI）をスコアリング（score_news）

  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {n_written} symbols")

  - api_key を引数に与えない場合は環境変数 OPENAI_API_KEY を使用します。
  - OpenAI 呼び出しは冪等ではありません。テスト時は _call_openai_api をモック可能。

- 市場レジーム判定（score_regime）

  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査テーブル初期化

  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- 市場カレンダー操作例

  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026,3,20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))

注意:
- score_news / score_regime は OpenAI API を使用し、API 呼び出しに失敗した場合はフェイルセーフ（0.0 など）にフォールバックする実装が多く含まれます。
- ETL・保存処理はいずれも DuckDB のトランザクションで保護されていますが、部分成功時の挙動はログ・戻り値を参照してください。

---

## 主要ディレクトリ構成

（リポジトリの src/kabusys 以下の主要モジュール）:

- kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — 環境変数 / 設定管理（.env 自動読み込み、settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを銘柄毎に集約して OpenAI に投げるスコアリング機能（score_news）
    - regime_detector.py — ETF MA とマクロニュースを合成して市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存関数）
    - pipeline.py — ETL パイプライン（run_daily_etl 他）、ETLResult
    - etl.py — ETL インターフェース再エクスポート
    - news_collector.py — RSS 取得・前処理・保存ロジック（SSRF 対策あり）
    - calendar_management.py — 市場カレンダー、営業日判定、calendar_update_job
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログ・トレーサビリティの DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility ファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
  - ai、data、research 以下に細かなユーティリティや設計メモが含まれます。

---

## 設計上の注意点と運用メモ

- Look-ahead バイアス回避:
  - 多くの関数は date.today() を内部で参照せず、明示的な target_date を要求します。バックテスト等ではこの挙動を遵守してください。

- レート制御 / リトライ:
  - J-Quants API は 120 req/min のレート制限を守る実装になっています。OpenAI 呼び出しもリトライロジックを備えています。

- セキュリティ:
  - RSS 収集には SSRF ガード、gzip サイズチェック、defusedxml による XML パースを使用しています。

- テスト:
  - OpenAI 呼び出し箇所は内部の _call_openai_api をモック可能にしており、ユニットテストで外部 API を回避できます。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使えば自動 .env 読み込みを無効化できます。

---

必要があれば README に含めるサンプル .env.example、CI の実行方法、開発フロー（ブランチ戦略）や API の詳細仕様（J-Quants / kabu）などを追記できます。追加で欲しい項目があれば教えてください。