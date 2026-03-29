# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集と LLM によるニュースセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）、市場カレンダー管理などを備え、売買戦略の研究と本番運用を支援します。

主な設計方針として「ルックアヘッドバイアスの排除（datetime.today() 等を直接参照しない）」「DuckDB を中心としたローカルデータ管理」「API 呼び出しの堅牢化（リトライ・バックオフ・レート制御）」を掲げています。

---

## 機能一覧

- データ ETL（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場情報、JPX カレンダーの差分取得・保存（冪等）
  - レートリミッター、トークン自動リフレッシュ、再試行（バックオフ）
- ニュース収集
  - RSS 取得・正規化・SSRF 対策・重複排除・raw_news / news_symbols への保存
- ニュース NLP（LLM）
  - gpt-4o-mini を用いた銘柄別センチメント算出（JSON Mode、バッチ処理、堅牢なバリデーション）
  - ニュースウィンドウの時間計算（JST ベース → DB は UTC naive）
- 市場レジーム判定
  - ETF (1321) の MA200 乖離 + マクロニュース LLM を合成して market_regime を算出
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）、ファクター統計サマリ、Z-score 正規化
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue オブジェクト）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ
  - order_request_id による冪等性、UTC タイムスタンプ管理
- 設定管理
  - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local が override）
  - 必須設定は Settings 経由で参照（未設定時は例外）

---

## セットアップ

必要な Python ライブラリ（代表例）:
- duckdb
- openai
- defusedxml

（実際の requirements はプロジェクトに合わせて用意してください）

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発インストール（パッケージ化されている場合）
pip install -e .
```

環境変数の設定:
- 必須（アプリケーションの主要機能に必要）
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード（発注等に必要）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID      : Slack 通知対象チャンネル ID
- 任意 / デフォルトあり
  - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env ロードを無効化
  - OPENAI_API_KEY        : OpenAI API キー（score_news / regime で使用）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH           : 監視系 sqlite パス（デフォルト data/monitoring.db）

プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（.env.local は上書き）。  
自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例（.env の最小テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単な例）

事前に DuckDB 接続を用意しておきます（デフォルトファイルは settings.duckdb_path）。

基本例: 日次 ETL 実行
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニューススコアリング（LLM）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数か api_key 引数で指定
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("scored:", n_written)
```

市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

監査ログ DB 初期化（独立 DB にする例）:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査用 DB を独立ファイルに作る場合
audit_conn = init_audit_db("data/audit.duckdb")
```

J-Quants から直接データを取得したいとき:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# id_token を手動で取得する例
id_token = get_id_token()  # settings.jquants_refresh_token を使う
records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,12,31))
```

ニュースフィード取得（RSS）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

ログレベルや実行モードの制御は環境変数 KABUSYS_ENV / LOG_LEVEL で行います（Settings クラス参照）。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src レイアウトで実装されています。主要なモジュール構成は以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP（銘柄別センチメント）
    - regime_detector.py             -- マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（取得 + 保存）
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - etl.py                         -- ETL の公開型再エクスポート
    - news_collector.py              -- RSS 収集
    - calendar_management.py         -- 市場カレンダー管理（営業日判定等）
    - quality.py                     -- データ品質チェック
    - stats.py                       -- 統計ユーティリティ（zscore 等）
    - audit.py                       -- 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py             -- モメンタム/ボラ/バリュー等
    - feature_exploration.py          -- 将来リターン/IC/統計サマリ
  - ai/、data/、research/ 以下にある各モジュールは、DuckDB 接続を受け取る設計で
    バックテストと本番を安全に分離できるようになっています。

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス対策
  - ほとんどの関数で内部的に datetime.today() / date.today() を直接参照しません。target_date を明示して呼ぶ設計になっており、バックテストや再現性が確保されています。
- 環境変数自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動ロードします。テスト時などに無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API 呼び出しは堅牢化
  - OpenAI / J-Quants への呼び出しはリトライ・バックオフ・タイムアウト・ステータスコード判定を実装しています。LLM 呼び出しでは JSON パース失敗時に安全にフェイルバックします（例：macro_sentiment=0.0）。
- DuckDB の互換性
  - DuckDB のバージョン差異に配慮した実装（executemany の空リスト回避や SQL の互換性）を行っています。
- セキュリティ
  - RSS 取得では SSRF 対策、受信サイズ制限、defusedxml を用いた XML パースなどを実施しています。
- 冪等性
  - ETL / 保存処理では ON CONFLICT またはユニークキーを使った冪等保存を行います。監査ログの order_request_id も冪等キーとして設計されています。

---

## 追加情報 / 開発者向け

- テスト: モジュール内の API 呼び出しはモックしやすいよう分離されています（例: kabusys.ai.news_nlp._call_openai_api を patch 可能）。
- ロギング: 各モジュールは logger を使用しており、LOG_LEVEL による出力制御が可能です。
- 拡張ポイント:
  - 新たなニュースソースを DEFAULT_RSS_SOURCES に追加してニュース収集を拡張できます。
  - 研究用のファクターモジュールは duckdb 接続を受け取るため、カスタム分析の追加が容易です。

---

この README はコードベースの主要機能と使い方をまとめたものです。さらに詳細な API の利用例や schema 定義、CI / デプロイ手順などが必要でしたらお知らせください。