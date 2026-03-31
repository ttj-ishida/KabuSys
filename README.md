# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買支援ツール群を提供するパッケージです。J-Quants / kabuステーション / OpenAI 等を利用してデータ収集（ETL）、品質チェック、ニュース NLP、市場レジーム判定、研究用ファクター計算、監査ログなどを行うことを目的としています。

---

## 主な特徴 (機能一覧)

- データ収集（ETL）
  - J-Quants API から株価日足、財務データ、マーケットカレンダーを差分取得して DuckDB に保存
  - 差分取得・バックフィル・ページネーション対応
  - レートリミット遵守・リトライ・トークン自動リフレッシュ

- データ品質管理
  - 欠損データ、スパイク（急騰/急落）、重複、日付不整合の検出と QualityIssue レポート

- ニュース収集
  - RSS フィードの収集、URL 正規化、SSRF 対策、記事の前処理、raw_news テーブルへの冪等保存

- ニュース NLP / AI
  - OpenAI（gpt-4o-mini）を用いた銘柄単位のニュースセンチメント集計（news_nlp.score_news）
  - マクロ記事と ETF（1321）200日移動平均乖離を組み合わせた市場レジーム判定（regime_detector.score_regime）

- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー、Z スコア正規化

- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions など監査用テーブルの初期化 / DB 作成補助
  - order_request_id による冪等性設計

- 設定管理
  - 環境変数 / .env（.env.local）を自動でロード
  - 開発 / paper_trading / live の環境区分とログレベル検証

---

## 前提条件 / 依存関係

主に次のライブラリを使用します（必要に応じてバージョンを固定してください）:

- Python 3.9+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

（プロジェクトに requirements.txt があればそちらを使用してください。例:）
```
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン
```
git clone <repo-url>
cd <repo>
```

2. 仮想環境を作成・有効化（任意）
```
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows
```

3. 必要パッケージをインストール
```
pip install -r requirements.txt
# または手動
pip install duckdb openai defusedxml
```

4. 環境変数の設定
- プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（デフォルト挙動）。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で使用）。

必須の環境変数（コード内で _require により必須扱い）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector / その他で参照）

任意 / デフォルト値:
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — '1' にすると .env の自動読み込みを無効化

例 .env（.env.example を参考に作成してください）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=yourpassword
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
```

---

## 使い方（例）

以下は主なユーティリティを Python REPL またはスクリプトから呼ぶ基本例です。

- DuckDB 接続を準備する例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（市場カレンダー・株価・財務の差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成（ai_scores テーブルへ書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定（market_regime テーブルへ書き込む）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB / スキーマ初期化
```python
from kabusys.data.audit import init_audit_db, init_audit_schema

# 既存 DuckDB にスキーマを作る場合
init_audit_schema(conn, transactional=True)

# 監査専用 DB ファイルを初期化して接続を得る場合
audit_conn = init_audit_db("data/audit.duckdb")
```

- リサーチ関数（ファクター計算の例）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
```

備考:
- OpenAI を利用する関数は引数で `api_key` を渡すこともできます（省略すると環境変数 OPENAI_API_KEY を参照）。
- DuckDB 側のテーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime, market_calendar 等）は ETL や初期化処理で作られる想定です。初期スキーマ作成ユーティリティ等があれば先に実行してください。

---

## ディレクトリ構成（主要ファイル）

以下はソース内の主要モジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP（銘柄別センチメント）
    - regime_detector.py    # マクロ + ETF で市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py           # ETL 実行フロー（run_daily_etl 等）
    - etl.py                # ETLResult エクスポート
    - jquants_client.py     # J-Quants API クライアント（fetch/save）
    - news_collector.py     # RSS 収集と前処理
    - stats.py              # zscore_normalize 等
    - quality.py            # データ品質チェック
    - audit.py              # 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py    # モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py# 将来リターン, IC, summary, rank 等

---

## 実運用上の注意点 / 設計方針の要約

- ルックアヘッドバイアス対策: 多くの処理は内部で date.today() を盲目的に使わず、target_date を明示的に受け取ります。DB クエリも target_date 未満 / 以前などでルックアヘッドを防止しています。
- 冪等性: J-Quants 等からの保存処理は ON CONFLICT DO UPDATE（IDEMPOTENT）を採用しており、再実行しても上書きで安全に更新されます。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）に失敗した場合は例外を常に上位へ投げるわけではなく、ログ警告にとどめて代替値で継続するなどを基本に設計されています（ただし致命的な DB 書込失敗等は例外伝播します）。
- セキュリティ: news_collector では SSRF 対策、XML の defusedxml 使用、受信バイト上限などを実装しています。

---

## トラブルシューティング

- 環境変数不足による ValueError:
  - settings の必須プロパティは未設定だと ValueError を出します。`.env.example` を参考に `.env` を作成してください。
- OpenAI API の呼び出しで rate limit や 5xx が発生する場合はライブラリ内でリトライ/バックオフが掛かりますが、APIキーと課金上限を確認してください。
- DuckDB の executemany に関する注意:
  - 一部の DuckDB バージョンでは executemany に空リストを渡すとエラーになるため、コードは呼び出す前に空チェックを行っています。

---

必要であれば、README に「CLI の使い方」「スキーマ定義（DDL）」「デプロイ手順」「CI / テスト実行方法」などの追加セクションを追記します。どの部分を詳細化したいか教えてください。