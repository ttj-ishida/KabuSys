# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・マーケットカレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算・リサーチユーティリティ、監査ログ（トレーサビリティ）等を提供します。

主な設計方針：
- Look-ahead バイアス対策（内部で date.today()/datetime.today() を直接参照しない等）
- DuckDB を中心とした軽量なローカル分析基盤
- API 呼び出しの堅牢性（リトライ、バックオフ、フェイルセーフ）
- 冪等性を考慮した DB 操作（ON CONFLICT / DELETE→INSERT 等）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env または環境変数から設定を自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック

- データ ETL（kabusys.data.pipeline）
  - J-Quants からの株価（日足）、財務、マーケットカレンダーの差分取得と DuckDB への保存
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・次/前営業日の取得・期間内営業日の列挙
  - JPX カレンダーの差分更新ジョブ

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news への冪等保存（記事IDは正規化 URL の SHA-256 を使用）
  - SSRF/サイズ上限/XML 安全対策を実装

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメントを算出し ai_scores に保存
  - バッチ、トリミング、リトライ、レスポンス検証を含む

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）200日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して
    市場レジーム（bull / neutral / bear）を判定・market_regime テーブルに保存

- リサーチ / ファクター計算（kabusys.research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリーなど

- 監査ログ（kabusys.data.audit）
  - シグナル→発注→約定までをトレースする監査テーブルの初期化ユーティリティ
  - order_request_id による冪等性、UTC タイムスタンプ保証

---

## セットアップ手順

前提:
- Python 3.10+（型注釈に union 型等を使用）
- DuckDB が必要（pip install duckdb）
- OpenAI SDK（openai）を利用（news / regime モジュール）
- defusedxml（RSS パースの安全化）

推奨インストール（例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .            # パッケージ配布が用意されている前提
pip install duckdb openai defusedxml
```

必須環境変数（少なくとも実行に必要なもの）
- JQUANTS_REFRESH_TOKEN  - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      - kabuステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN        - Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID       - Slack 通知先チャンネルID

オプション / デフォルト
- KABU_API_BASE_URL      - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            - SQLite / 監視用 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV            - 環境 (development / paper_trading / live)、デフォルト development
- LOG_LEVEL              - ログレベル（DEBUG/INFO/...）、デフォルト INFO

自動 .env 読み込み:
- プロジェクトルート（pyproject.toml または .git 配下）にある `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 .env（README 用テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（抜粋・サンプル）

以下は簡単な Python スニペット例です。実際はログ設定や例外処理を適切に行ってください。

- DuckDB 接続を作って日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリングを実行する（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）:
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {n} codes")
```

- 市場レジームを判定して保存する:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化（監査専用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの duckdb 接続
```

- RSS フィードから記事を取得する（news_collector の低レベル関数利用例）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数でキー注入が可能（テストや環境分離に便利）。
- DuckDB の接続を複数モジュールへ渡して処理を行います。トランザクションの扱いに注意してください（モジュール内で BEGIN/COMMIT/ROLLBACK を使用する箇所があります）。

---

## よく使うモジュール / API 一覧（インポート例）
- 環境設定: from kabusys.config import settings
- ETL: from kabusys.data.pipeline import run_daily_etl, run_prices_etl, ETLResult
- News NLP: from kabusys.ai.news_nlp import score_news
- Regime: from kabusys.ai.regime_detector import score_regime
- Audit 初期化: from kabusys.data.audit import init_audit_db
- J-Quants クライアント: from kabusys.data import jquants_client as jq
- カレンダー: from kabusys.data.calendar_management import is_trading_day, next_trading_day

---

## ディレクトリ構成

主要ファイル/モジュールの概観（src/kabusys 配下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py          # ニュースセンチメント算出（OpenAI）
  - regime_detector.py   # マーケットレジーム判定
- data/
  - __init__.py
  - jquants_client.py    # J-Quants API クライアント + DuckDB 保存ユーティリティ
  - pipeline.py          # ETL パイプライン（run_daily_etl 等）
  - etl.py               # ETLResult 再エクスポート
  - calendar_management.py
  - news_collector.py
  - stats.py
  - quality.py
  - audit.py             # 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py   # モメンタム / ボラ / バリュー 等
  - feature_exploration.py
- その他: monitoring / strategy / execution / など（パッケージ __all__ に含まれる想定）

（上記は主要モジュールの抜粋です。実装細部は各ファイルのドキュメント文字列を参照してください。）

---

## 設計上の重要な注意点

- Look-ahead バイアス対策: 多くの処理が target_date 引数を受け、内部で現在時刻を直接参照しないように設計されています。バックテスト等での利用時は target_date を明示してください。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）失敗時に処理を続行できるようにフォールバック（スコア 0.0 など）や部分失敗を許容する実装が多くあります。
- 冪等性: ETL 保存処理や監査テーブル初期化は冪等操作を念頭に置いています（ON CONFLICT / DELETE→INSERT 等）。
- セキュリティ: news_collector は SSRF/ZIP 膨張/XML Bomb を考慮した実装になっています。RSS ソースを追加する際も注意してください。

---

## 開発・テスト時メモ

- 自動 .env 読み込みを無効化したい（ユニットテスト等）場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- OpenAI 呼び出しは内部で再利用しやすいよう関数単位で定義されているため unittest.mock.patch による差し替えが容易です（例: kabusys.ai.news_nlp._call_openai_api をモックする）。
- DuckDB のバージョン依存（executemany で空リスト禁止等）に注意。テストではインメモリ ":memory:" を使うことが可能です。

---

必要があれば、README に含めるコマンド例（cron/airflow ジョブ例）、.env.example の完全テンプレート、または各モジュールの API リファレンスを追記します。どの情報を追加しますか？