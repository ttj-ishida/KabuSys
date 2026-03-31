# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ。
DuckDB を中心としたデータ ETL、ニュース NLP（OpenAI）、市場レジーム判定、
リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

主な対象
- J-Quants API からのデータ取得（株価・財務・カレンダー）
- RSS ニュース収集と LLM による銘柄別センチメント集計
- 市場レジーム判定（ETF + マクロニュース）
- 研究用途のファクター計算 / 前方リターン計算 / IC 評価
- ETL パイプライン（差分取得・品質チェック）
- 監査ログ用テーブルの初期化 / 管理

---

## 機能一覧

- 環境変数 / .env 自動読み込み（settings オブジェクト経由で利用）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB に冪等保存（ON CONFLICT DO UPDATE）
  - レートリミット・リトライ・401 自動リフレッシュ対応
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 結果は ETLResult 型で返る（品質チェック結果含む）
- ニュース収集 & NLP
  - RSS 取得（SSRF 対策、gzip 対応、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）経由で銘柄ごとの ai_score を ai_scores に格納（score_news）
  - レイトリミット・リトライ・レスポンス検証・クリップ
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離とマクロニュース LLM を合成し market_regime に書き込み（score_regime）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック（run_all_checks）
- カレンダー管理（JPX）
  - 営業日判定 / 次営業日・前営業日検索 / カレンダー更新ジョブ
- 研究（research）
  - momentum / value / volatility ファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- 監査ログ（audit）
  - signal_events, order_requests, executions テーブル定義と初期化ユーティリティ
  - init_audit_db / init_audit_schema（UTC タイムスタンプ統制）

---

## 前提・依存関係

推奨 Python バージョン: Python 3.10 以上

主な Python パッケージ（一例）
- duckdb
- openai
- defusedxml

リポジトリに requirements.txt / pyproject.toml があればそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン / ダウンロード

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. パッケージインストール（プロジェクトルートに pyproject.toml / setup.cfg がある想定）
   - pip install -e .

   あるいは必要パッケージを個別にインストール:
   - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成します。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabu ステーション API パスワード
     - SLACK_BOT_TOKEN       : Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
     - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）
   - オプション / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live)、デフォルトは development
     - LOG_LEVEL（DEBUG|INFO|...）、デフォルト INFO
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB 用）

   - 自動読み込みを無効化したいとき:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. データディレクトリの作成（必要なら）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は主要ユースケースの最小実行例です。実行前にデータベースや環境変数を整えてください。

- DuckDB 接続を作成して ETL を実行する例
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアを計算して ai_scores に保存
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring_audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 研究モジュールを使ったファクター計算
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026,3,20)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
```

- カレンダー関係ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026,3,20)))
print(next_trading_day(conn, date(2026,3,20)))
```

注意点
- OpenAI を使う機能は OPENAI_API_KEY が必要です（引数で上書きも可能）。
- DuckDB のスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar 等）は ETL / 初期化用のDDL が別途必要です（通常は schema 初期化スクリプトを提供してください）。

---

## 環境変数（主なもの）

必須（実行する機能によっては不要な場合あり）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先
- OPENAI_API_KEY — OpenAI を用いる NLP / レジーム判定

任意
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（INFO 等）

.env ファイルの自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml がある場所）にある .env / .env.local を自動ロードします。
- 既存の OS 環境変数は保護され、.env.local は .env を上書きできます。
- 自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主なモジュール構成です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存ロジック
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS 取得 / 正規化 / 保存
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック
    - stats.py               — zscore_normalize 等ユーティリティ
    - audit.py               — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py     — momentum/value/volatility ファクター
    - feature_exploration.py — forward returns / IC / summary

（上記以外に strategy / execution / monitoring 等の名前空間が __all__ に含まれていますが、README の時点での主要実装を優先して記載しています）

---

## 開発・テスト

- ローカルでの開発は仮想環境と DuckDB を使って行ってください。
- OpenAI / J-Quants 呼び出し部はネットワーク依存なので、ユニットテスト時は HTTP 呼び出しや OpenAI 呼び出しをモックする設計になっています（module 内で _call_openai_api を patch する等）。
- .env を用いて API キーを用意し、最小限の ETL を実行してスキーマ整備を行ってください。

---

## 注意事項

- 本ライブラリは実運用の売買実行を直接行うモジュール（broker への送信等）と組み合わせて使用する想定です。実際の発注処理を行う前に十分なテストとリスク管理を実施してください。
- OpenAI / J-Quants / kabu ステーションの利用に伴う API 使用料・利用規約に注意してください。
- データの時系列取り扱いは Look-ahead バイアス回避を重視した実装方針を取っています。バックテスト等での利用時はこの方針を理解した上でデータ準備を行ってください。

---

README に書かれていない補足や、特定モジュールの詳細な使い方（例: ETL の schema 初期化スクリプト、strategy / execution の具体的実装）が必要であれば、その箇所を指定していただければ追記します。