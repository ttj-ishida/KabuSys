# KabuSys — 日本株自動売買プラットフォーム（ライブラリ）

KabuSys は日本株向けのデータパイプライン、リサーチ、AI ベースのニュース解析、監査ログ基盤、および戦略/実行支援ユーティリティを含む内部ライブラリ群です。本リポジトリは DuckDB を中心にデータを管理し、J-Quants や RSS、OpenAI 等の外部サービスと連携する設計になっています。

主な設計方針:
- ルックアヘッドバイアスを避ける（date を明示的に引き渡す設計）
- DuckDB を使ったローカルデータレイク
- 冪等性（ON CONFLICT / idempotent 保存）と監査性（監査テーブル）
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを実装

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save：株価、財務、マーケットカレンダー、上場銘柄情報）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - データ品質チェック（欠損・重複・スパイク・日付不整合検出）
  - マーケットカレンダー管理（営業日判定など）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（zscore_normalize 等）
- ai
  - ニュース NLP（score_news: 銘柄ごとのニュースセンチメント算出、OpenAI 使用）
  - 市場レジーム判定（score_regime: ETF 1321 の MA200 とマクロニュースを合成）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索（将来リターン、IC、統計サマリー、ランク変換）
- config
  - .env 自動読み込み（プロジェクトルート判定）と Settings オブジェクト
- monitoring / execution / strategy / その他（パッケージ公開のための名前空間）

---

## 要件（主な依存）

- Python 3.10+
- duckdb
- openai (OpenAI の Python SDK v1 系を想定)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, typing 等）

インストール前に pyproject.toml / requirements.txt を確認してください（本 README はコードベースから推測した依存を列挙しています）。

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は duckdb, openai, defusedxml を個別にインストールしてください）
   - pip install duckdb openai defusedxml

3. プロジェクトルートに .env を配置（自動読み込みされます）
   - 自動 `.env` ロードは、パッケージのソース配置時に .git または pyproject.toml を基準に行われます。
   - 自動ロードを無効化するには環境変数を設定してください:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必要な環境変数（.env 例）
   以下は本コードで参照される主な環境変数です（必須・省略可はコメント参照）。

   .env.example（抜粋）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   # KABU_API_BASE_URL を省略するとデフォルト http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...

   # DB パス（オプション）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

---

## 使い方（サンプル）

以下は主要な操作を Python スクリプトから呼ぶ例です。必ず環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してから実行してください。

- DuckDB 接続を作成して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path を使う場合:
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

# 今日分の ETL（target_date を指定して過去日を処理可能）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
print(f"scored {count} codes")
```

- 市場レジームスコアを計算して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
```

- 監査ログ用 DuckDB を初期化する
```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
```

- ETL の個別ジョブ（価格・財務・カレンダー）
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

# 例: run_prices_etl(conn, target_date, id_token=None)
```

メソッドの引数説明や戻り値の詳細はコードの docstring を参照してください（run_daily_etl は ETLResult を返します）。

---

## 注意事項 / 運用メモ

- OpenAI 呼び出しは JSON Mode を利用し、レスポンスのバリデーションを厳密に行っています。API キーは OPENAI_API_KEY または関数引数で指定してください。
- J-Quants クライアントは ID トークンの自動リフレッシュと 120 req/min のレート制限を内部で管理します。JQUANTS_REFRESH_TOKEN を設定してください。
- ニュース収集は SSRF 対策とレスポンスサイズ制限、XML セキュリティ（defusedxml）を実装しています。
- DuckDB バインドで executemany に空リストが渡せないバージョン等の考慮を行っています（コード内に注記あり）。
- 設定が足りない場合、config.Settings の必須プロパティは ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_* 等）。

---

## ディレクトリ構成（重要ファイル）

- src/kabusys/
  - __init__.py — パッケージ初期化（version, __all__）
  - config.py — 環境変数読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — カレンダー管理（is_trading_day 等）
    - news_collector.py — RSS 収集・前処理
    - quality.py — データ品質チェック（QualityIssue）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査スキーマの初期化
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum, value, volatility）
    - feature_exploration.py — 将来リターン、IC、summary、rank
  - ai, research, data 以下にはユーティリティ関数や SQL が豊富に含まれます。

---

## 開発・テスト時のヒント

- 自動 .env ロードを無効にしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants の外部呼び出しはユニットテストでモックすることを推奨します。コード内でも各所で _call_openai_api / _urlopen 等を差し替え可能に設計しています。
- DuckDB はインメモリ(":memory:")で利用可能なので、テストでの DB 初期化が容易です（init_audit_db(":memory:") 等）。

---

必要であれば README に以下を追加します:
- 詳細な .env.example ファイル（全キーと説明）
- よくあるエラーとトラブルシューティング
- CI / デプロイ手順
- API 使用上のレート制限の運用例

追加してほしい項目があれば教えてください。