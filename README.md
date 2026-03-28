# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
DuckDB をデータレイヤーに、J-Quants（市場データ）と OpenAI（ニュース NLP）を活用して、ETL、ニュースセンチメント、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

## 主要機能

- データ取得 / ETL
  - J-Quants から株価（日足）、財務データ、マーケットカレンダーを差分取得・保存
  - 差分更新・バックフィル・ページネーション・リトライ・レート制御を備えたクライアント
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック（QualityIssue レポート）
- ニュース収集・前処理
  - RSS 取得、URL 正規化、SSRF 対策、サイズ制限、XML 安全パース
- ニュース NLP（OpenAI）
  - 銘柄別ニュースを統合して LLM に投げ、センチメント（ai_scores）を書き込み
  - エラーハンドリング・バッチ処理・レスポンス検証付き
- マーケットレジーム判定（AI + テクニカル）
  - ETF（1321）200日移動平均乖離とマクロ記事センチメントを合成して日次レジームを判定
- リサーチ用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブルを DuckDB に初期化するユーティリティ
  - UUID ベースのトレーサビリティ、冪等性・インデックス定義あり

---

## 動作環境・前提

- Python 3.10+
  - PEP 604（X | None）などの構文を使用しているため 3.10 以上を推奨します
- 推奨ライブラリ（最低限）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワーク接続（J-Quants API、OpenAI API、RSS フィード）

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ プロジェクトがパッケージ化されている場合:
   - pip install -e .

4. 環境変数の設定
   - ルートに `.env` または `.env.local` を作成して必要な値を設定できます。OS 環境変数が優先されます。
   - 自動 .env 読み込みはデフォルトで有効。無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（ETL 用）
- KABU_API_PASSWORD : kabuステーション API のパスワード（注文 API 用）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID : Slack チャネル ID
- OPENAI_API_KEY : OpenAI 呼び出しに必要（AI 機能を使う場合）

オプション / デフォルト
- KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
- LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）

例 (.env)
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development

---

## 使い方（簡単な例）

以下は各主要 API の利用例です。実行前に環境変数（特に OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB 接続準備例
```
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行（データ取得・品質チェック）
```
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント（AI）でスコアリング
```
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

- マーケットレジーム判定（AI + MA200）
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- リサーチ系ファクター計算
```
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DB 初期化（監査専用 DuckDB を作る）
```
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

---

## 注意事項 / 実装上のポイント

- .env 自動ロード:
  - ルート（.git または pyproject.toml がある場所）を探索し、`.env` を先に読み込み、`.env.local` を上書き読み込みします。
  - OS の環境変数は保護され、.env による上書きは行われません（ただし .env.local は上書き）。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- Look-Ahead Bias 対策:
  - AI スコアリング / レジーム判定 / ETL の各処理は内部で date を明示しており、datetime.today() 等の実行時現在値に依存しないよう設計されています（バックテスト時のリーク防止）。

- OpenAI 呼び出し:
  - gpt-4o-mini を利用（JSON mode を使用）。API エラーやパース失敗時はスコアをデフォルト値にフォールバックし、処理を継続します。

- J-Quants クライアント:
  - レート制限（120 req/min）を内部で制御、リトライ・トークン自動リフレッシュ機能搭載。
  - DuckDB への保存は冪等（ON CONFLICT）で行われます。

- テスト容易性:
  - OpenAI 呼び出し部分は内部関数を patch してモックしやすく設計されています（ユニットテストでの差し替えが想定されています）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / .env ローディング
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP（スコアリング）
    - regime_detector.py             -- レジーム判定（MA200 + マクロ NLP）
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント + DuckDB 保存
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - etl.py                         -- ETLResult 再エクスポート
    - calendar_management.py         -- 市場カレンダー管理 / 営業日ロジック
    - news_collector.py              -- RSS 収集 / 正規化 / raw_news 保存
    - quality.py                     -- データ品質チェック
    - stats.py                       -- z-score など共通統計ユーティリティ
    - audit.py                       -- 監査ログテーブル初期化 / audit DB helper
  - research/
    - __init__.py
    - factor_research.py             -- Momentum / Value / Volatility の計算
    - feature_exploration.py         -- 将来リターン / IC / summary utilities
  - research/（その他モジュール）
- pyproject.toml (想定)
- .env.example (想定)

---

## よくあるトラブルと対処

- OpenAI / J-Quants の API キー未設定で例外:
  - score_news / score_regime / get_id_token 等は API キー未設定時に ValueError を投げます。環境変数または関数引数でキーを渡してください。

- DuckDB テーブルが存在しない / スキーマ不足:
  - ETL 実行前に必要なスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, prices_daily 等）を用意してください。開発用にスキーマ初期化スクリプトを用意すると便利です。

- RSS フィード取得で接続失敗や SSRF ブロック:
  - news_collector はリダイレクト先のホスト判定やプライベート IP へのアクセス防止を行います。自己ホスト RSS を利用する際はホストの可視性や URL スキームを確認してください。

---

必要に応じて README に含めるサンプル .env.example、DB スキーマ初期化スクリプト、CI 設定などのテンプレートも作成できます。詳細な開発・運用手順（デプロイ、ジョブスケジューリング、モニタリング）を追加したい場合は教えてください。