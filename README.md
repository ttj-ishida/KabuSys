# KabuSys

日本株向けの自動売買・データプラットフォーム（KabuSys）の軽量実装コアライブラリです。  
データETL、ニュース収集・NLP、リサーチ（ファクター計算）、監査ログ（トレーサビリティ）などの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は日本株マーケット向けに設計されたデータパイプラインと研究・戦略支援ライブラリ群です。主な設計方針は以下の通りです。

- Look-ahead バイアス防止（バックテストや生成において現在時刻を直接参照しない設計）
- DuckDB をデータストアとして利用する ETL 中心のデータ基盤
- J-Quants API 経由の市場データ取得（株価、財務、カレンダー）
- RSS ニュース収集と OpenAI を使ったニュース NLP による銘柄スコアリング
- 市場レジーム判定（ETF + マクロニュースの合成）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 冪等性と耐障害性（ON CONFLICT、リトライ、フォールバック等）を重視

---

## 機能一覧

- 環境変数 / .env 自動読み込み（`kabusys.config`）
  - 自動ロードはプロジェクトルート（`.git` または `pyproject.toml`）を探索
  - 無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- データ収集 / ETL（`kabusys.data.pipeline`）
  - J-Quants から株価・財務・カレンダーを差分取得して DuckDB に保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar 等）
- ニュース収集（`kabusys.data.news_collector`）
  - RSS 取得（SSRF対策、gzip/サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への保存（冪等）
- ニュース NLP（`kabusys.ai.news_nlp`）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコア算出
  - バッチ処理、最大記事数/文字数制限、レスポンス検証、リトライ
- 市場レジーム判定（`kabusys.ai.regime_detector`）
  - ETF(1321) の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成
  - market_regime テーブルへ冪等書き込み
- 研究用ファクター計算（`kabusys.research`）
  - momentum / volatility / value 等のファクター計算
  - 将来リターン、IC、統計サマリー、Z スコア正規化
- 監査ログ（`kabusys.data.audit`）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ
  - 監査DB初期化関数（UTC タイムゾーン固定）

---

## セットアップ

必要条件（推奨）
- Python 3.10+
- DuckDB
- OpenAI Python SDK
- defusedxml

簡単なセットアップ例:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

（プロジェクトに requirements.txt がある場合はそれを使ってください。）

3. 環境変数を設定
   - プロジェクトルートに `.env` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数:

     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector 用）
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（必要に応じて）
     - SLACK_BOT_TOKEN: Slack 通知用（必要に応じて）
     - SLACK_CHANNEL_ID: Slack チャンネルID
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視DB (SQLite) のパス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）

   - 例（.env）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（簡易ガイド）

以下はライブラリの代表的な利用例です。実際には各関数の引数や戻り値の仕様を参照してください。

1. DuckDB 接続を作成して ETL を実行する（1日分）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュースの NLP スコア化（指定日）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み件数: {n_written}")
```

3. 市場レジーム判定を実行して market_regime に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4. 監査DB（別ファイル）を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events/order_requests/executions が作成されます
```

注記:
- OpenAI を利用する関数は API 呼び出しの失敗に対してフォールバックやリトライを実装していますが、APIキーが未設定だと ValueError を投げます。
- run_daily_etl などは内部で datetime.today()/date.today() を参照します（ただし主要な処理は target_date に依存して Look-ahead バイアスを避ける設計になっています）。

---

## ディレクトリ構成

リポジトリ内の主なファイル / モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: rss ソース等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research や data のサブモジュールは、ファクター計算・統計処理・ETL ロジック・品質チェックを含む

（上記は提供されたソースコードベースに基づく抜粋です）

---

## 追加の注意点 / ベストプラクティス

- 環境変数の自動読み込みはプロジェクトルート検出を行います。テストや特別な環境で自動読み込みを抑制する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルはデフォルトで data/ 配下に書き込まれます。運用時は永続配置先パスを DUCKDB_PATH で明示してください。
- OpenAI 使用時はレスポンスの形式（JSON mode）に依存しているため、API の仕様変更に注意してください。ユニットテストでは内部の _call_openai_api をモックしてテストできます。
- J-Quants の API 使用にはレート制限があります（モジュールで固定間隔レートリミッタを利用）。長時間の一括処理や並列化を行う場合は注意してください。
- 本コードベースは「データ取得・研究・監査」を提供するコアライブラリであり、実際の発注（kabuステーション等）や運用コンポーネントは別モジュールで統合することを想定しています。

---

必要であれば、README に以下の追加情報を追記できます：
- サンプル .env.example
- CI / テスト実行手順（pytest）
- 詳細な API ドキュメント（各モジュール関数一覧）
- データベーススキーマ（テーブル定義の抜粋）