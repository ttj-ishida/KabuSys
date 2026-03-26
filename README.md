# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォームとリサーチ／自動売買支援ライブラリです。J-Quants API や RSS ニュース、OpenAI（LLM）を組み合わせてデータ取得・品質チェック・ファクター計算・ニュースセンチメント集計・市場レジーム判定・監査ログ管理などを提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で date.today() 等を不用意に参照しない）
- ETL や DB 書き込みは冪等（idempotent）に設計
- 外部 API 呼び出しはリトライ / バックオフ / フェイルセーフを備える
- DuckDB を中心としたローカルデータ管理

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local の自動ロード（プロジェクトルート検出、OS 環境優先）
- データ ETL
  - J-Quants から株価日足、財務データ、JPX カレンダーの差分取得・保存
  - run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue を返す）
- ニュース収集
  - RSS から記事取得、正規化、raw_news / news_symbols への保存（SSRF 防止・サイズ検査）
- ニュース NLP（LLM）
  - 銘柄ごとのニュースセンチメントを OpenAI により評価し ai_scores に保存（score_news）
- 市場レジーム判定
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成し market_regime に保存（score_regime）
- リサーチ用ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research モジュール）
  - 将来リターン計算、IC（情報係数）、統計サマリー等
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブルと初期化ユーティリティ（init_audit_schema / init_audit_db）
- J-Quants クライアント
  - レート制御、トークンリフレッシュ、ページネーション対応、DuckDB への保存ユーティリティ

---

## 前提条件

- Python 3.10 以上
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース 等）

インストール時に依存を揃えてください（プロジェクトに requirements.txt 等がある想定です）。

例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .                 # パッケージ化されている場合
pip install duckdb openai defusedxml
```

---

## 環境変数（必須 / 主要）

以下は本リポジトリ内で参照される代表的な環境変数です。`.env.example` を参考に `.env` を作成してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client が get_id_token で使用）
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（execution 関連）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — environment（development | paper_trading | live）, デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）, デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス, デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite パス, デフォルト: data/monitoring.db
- OPENAI_API_KEY — OpenAI を使用する機能（score_news / score_regime 等）で使用

自動 .env 読み込み:
- パッケージ初期化時（src/kabusys/config.py）はプロジェクトルート（.git または pyproject.toml を検出）から `.env`、`.env.local` を読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きできます。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

---

## セットアップ手順（簡易）

1. レポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化、依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成する
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB データベース用ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要なユースケース）

以下は簡単な Python API 例です。いずれも duckdb の接続オブジェクト（duckdb.connect(<path>)）を渡して利用します。

- DuckDB に接続して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアの生成（OpenAI API キー必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None → 環境変数 OPENAI_API_KEY を参照
print(f"written: {num_written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions が作成されます
```

- カレンダーヘルパーの利用
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- OpenAI 関連の関数は API 呼び出しに失敗した場合、フォールバック（0.0 スコア等）して処理を継続する設計です。
- J-Quants API 呼び出しは rate limiter とトークン自動リフレッシュを行います。JQUANTS_REFRESH_TOKEN を設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義（version: 0.1.0）
  - config.py — 環境変数 / .env 読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP / score_news
    - regime_detector.py — 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - jquants_client.py — J-Quants API クライアント（fetch / save）
    - news_collector.py — RSS ニュース収集
    - quality.py — データ品質チェック
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — forward returns / IC / summary 等
  - ai、data、research 以下にそれぞれの機能が実装されています。

---

## 注意事項 / ヒント

- DuckDB スキーマは別途初期化が必要なテーブル（raw_prices, raw_news, market_calendar, raw_financials, ai_scores, prices_daily, news_symbols, ...）があります。ETL 実行前にスキーマ初期化スクリプトを整えてください（本リポジトリに schema 初期化ユーティリティがあればそちらを使用）。
- OpenAI API の呼び出しはコストがかかります。テスト時はモック（unittest.mock）で _call_openai_api を差し替えることが想定されています。
- 自動 .env 読み込みは便利ですが、本番環境や CI では OS 環境変数を明示的に設定するのを推奨します。
- KABUSYS_ENV によって挙動（実際の発注を行う execution 等）が変わる想定があるため、本番運用時は必ず `live` の設定のチェックと十分なレビューを行ってください。

---

開発・運用で README に追加して欲しい項目（スキーマ定義、サンプル .env.example、CI 実行例、より詳細な ETL の手順など）があればお知らせください。必要に応じて追記します。