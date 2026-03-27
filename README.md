# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ。J-Quants からのデータ収集・ETL、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ管理など一連の機能を提供します。

主に DuckDB をバックエンドにしたデータパイプラインと、OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析・レジーム判定を含みます。

---

## 主な機能

- データ収集・ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを差分取得して DuckDB に冪等保存
  - ETL の実行結果を ETLResult で報告
- データ品質チェック
  - 欠損、重複、将来日付、スパイク検出などのチェックを実行
- ニュース収集・前処理
  - RSS フィード取得、URL 正規化、SSRF 対策、前処理を行い raw_news テーブルへ保存
- ニュース NLP（OpenAI）
  - ニュースを銘柄単位に集約し LLM（gpt-4o-mini）でセンチメントを算出し ai_scores に保存
- 市場レジーム判定（Regime Detector）
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM スコア（30%）を合成して日次で market_regime に保存
- 研究用モジュール
  - モメンタム / ボラティリティ / バリュー 等のファクター計算、将来リターン、IC 計算、統計サマリー等
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
- 環境変数管理
  - プロジェクトルートの `.env` / `.env.local` を自動ロード（無効化可）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください。
   （本リポジトリをパッケージとしてインストールする場合は pip install -e . を利用）

3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成して、必要な値を設定します。
   - 自動ロードはデフォルトで有効。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

.env の最小例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

- 説明:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーションAPI のパスワード（必須）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知等に使用（必須）
  - OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector 等で使用）
  - DUCKDB_PATH / SQLITE_PATH: データベースファイルパス（デフォルト設定あり）
  - KABUSYS_ENV: development / paper_trading / live（"development" がデフォルト）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

---

## 使い方（API サンプル）

下記は主なユーティリティの呼び出し例です。全て Python から呼び出します。

- DuckDB 接続を作成して ETL を実行する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# ファイルパスは settings.duckdb_path を使ってもよい
conn = duckdb.connect("data/kabusys.duckdb")

# 今日の ETL を実行（内部でカレンダー -> prices -> financials -> 品質チェックを実行）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコア付け:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB の初期化:
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査テーブルにアクセス
```

- News RSS を取得する（ニュースコレクタ単体の利用例）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用ファクター計算例:
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list of dict with keys 'date','code','mom_1m','mom_3m','mom_6m','ma200_dev'
```

注意点:
- OpenAI を使う関数は API キー（環境変数 OPENAI_API_KEY）が必要です。引数で明示的に渡すこともできます。
- DuckDB のスキーマ（raw_prices / raw_financials / market_calendar / raw_news 等）が必要です。初期化スクリプトやマイグレーションが別途ある場合は先に実行してください。

---

## 環境変数 / 設定の挙動

- 自動 .env ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml を探索）を基に `.env` と `.env.local` を自動読み込みします。
  - 読み込み順: OS 環境 > .env > .env.local（.env.local は上書き）
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Settings（kabusys.config.settings）により主な設定を取得できます（例: settings.duckdb_path, settings.env, settings.is_live など）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py: ニュース NLP 処理（OpenAI 使用） — score_news, calc_news_window 等
    - regime_detector.py: ETF MA とマクロニュースの LLM 評価を組み合わせた市場レジーム判定 — score_regime
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（取得 + DuckDB 保存ロジック）
    - pipeline.py: ETL パイプライン（run_daily_etl 等）
    - etl.py: ETLResult 再エクスポート
    - calendar_management.py: JPX カレンダー管理 / 営業日判定ユーティリティ
    - news_collector.py: RSS 取得・前処理・保存ユーティリティ
    - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py: zscore_normalize 等の統計ユーティリティ
    - audit.py: 監査テーブル DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py: Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py: 将来リターン / IC / rank / factor_summary 等
  - research/ ...（他モジュール）
  - その他: strategy / execution / monitoring 用のパッケージ（__all__ に含まれる想定）

---

## 運用上の注意

- Look-ahead bias（ルックアヘッド）対策がコード中で意識されています:
  - target_date の計算や DB クエリで過去データのみ参照する実装になっています。バックテストや再現性を考慮して設計されています。
- API のレート制御・リトライ:
  - J-Quants は固定間隔スロットリング、OpenAI 呼び出しはリトライ＋バックオフが実装されています。
- フェイルセーフ:
  - LLM の失敗や API 5xx 等は多くの場所でフェイルセーフ（スコア 0.0 等）にフォールバックして処理継続を図ります。
- DuckDB の executemany に関する注意:
  - 一部関数では executemany に空リストを渡さないようチェックがあります（互換性確保のため）。

---

## 開発・テストのヒント

- 環境変数の自動ロードを無効にして単体テストを行う場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを防ぐ
- OpenAI 呼び出し部分はモジュール内の `_call_openai_api` をモックしてテスト可能（news_nlp / regime_detector 共に差し替えポイントあり）
- news_collector のネットワーク呼び出しは `_urlopen` をモック可能

---

## ライセンス / 貢献

（この README ではライセンス情報は含めていません。リポジトリの LICENSE ファイルを参照してください）

---

必要であれば、README に実際のテーブルスキーマ作成や初期化スクリプト、CI/デプロイ手順、より詳細な API ドキュメント（各関数の引数や戻り値の例）を追加できます。どの情報を優先して追記するか教えてください。