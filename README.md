# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants からの差分取得）、ニュースの NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）、および戦略側で利用するユーティリティを提供します。

---

## 主な特徴（機能一覧）

- 環境変数/設定管理
  - .env/.env.local の自動読み込み（優先度: OS 環境 > .env.local > .env）
  - 必須値チェック（Settings クラス）
  - 自動読み込み無効化オプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）
- データ ETL（kabusys.data.pipeline）
  - J-Quants API からの差分取得（株価 / 財務 / 市場カレンダー）
  - 保存（DuckDB へ冪等保存、ON CONFLICT DO UPDATE）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次パイプライン run_daily_etl
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）で銘柄別ニュースセンチメントを算出し ai_scores に保存
  - バッチ・トリム・リトライ・レスポンス検証
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日 MA 乖離 + マクロニュース LLM スコアを合成して市場レジームを判定し market_regime に保存
- 研究用ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン算出、IC 計算、統計サマリ、Z スコア正規化
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーの保存 / 営業日判定 / next/prev_trading_day 等
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、SSRF 保護、トラッキングパラメータ除去、冪等保存
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions などの監査テーブルを作成・初期化
  - init_audit_db で専用 DuckDB を初期化
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制御、リトライ（401 リフレッシュ含む）、ページネーション、DuckDB への保存ユーティリティ

---

## 必要環境・依存

推奨: Python 3.10+  
主な依存パッケージ:
- duckdb
- openai
- defusedxml

（プロジェクトで実際に使うフロントエンドや CLI があればそれに応じて追加依存が必要です）

例: requirements.txt（参考）
- duckdb
- openai
- defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
2. 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 依存インストール
   pip install -r requirements.txt
   または最低限:
   pip install duckdb openai defusedxml
4. （オプション）パッケージを editable インストール
   pip install -e .
5. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env/.env.local を配置すると自動ロードされます。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主な環境変数（Settings 参照）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime のデフォルト）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知関連（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用DB）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 監視系設定
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

注意: Settings は必須のキーが無い場合 ValueError をスローします（例: JQUANTS_REFRESH_TOKEN が未設定など）。

---

## 使い方（主要ユースケース）

以下はライブラリの主要な関数の呼び出し例です。DuckDB 接続を用いるのが基本です。

1) DuckDB 接続
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- ETL はカレンダー -> 株価 -> 財務 -> 品質チェック の順に実行します。
- J-Quants の認証は settings.jquants_refresh_token を使います（必要に応じて id_token を引数で注入可能）。

3) ニューススコアリング（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
# OPENAI_API_KEY は環境変数か api_key 引数で渡す
```

4) 市場レジーム判定（OpenAI 必須）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
```

6) 監査ログ DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

7) マーケットカレンダーの判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

8) ニュース収集（RSS）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
# 取得した記事は raw_news に保存するロジック（別関数）を作成して利用してください
```
- fetch_rss は SSRF 対策や受信サイズ制限、トラッキング除去等を行います。

---

## 設計上の注意点 / セキュリティ

- Look-ahead バイアス防止:
  - 多くのモジュールは datetime.today() / date.today() を内部で参照しないように設計されています（API の引数で基準日を与える）。
  - データ読み出し時は target_date 未満の条件などによりルックアヘッドを回避します。
- OpenAI 呼び出し:
  - API キーは api_key 引数で注入可能。テストでは関数内部の API 呼び出しをモックできます。
  - レスポンスのバリデーション・リトライ（429, タイムアウト, 5xx）を実装。
- NewsCollector:
  - URL 正規化・トラッキングパラメータ除去・SSRF のチェック・リダイレクト時検査・受信サイズ制限を実装。
- J-Quants クライアント:
  - レート制御（120 req/min）を固定間隔スロットリングで実施。
  - 401 の場合にリフレッシュトークンを用いた再取得を行う。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 内に主なモジュールを配置しています。主要ファイルと概要:

- src/kabusys/__init__.py
  - パッケージのバージョン定義
- src/kabusys/config.py
  - 環境変数・設定管理（Settings クラス）
- src/kabusys/ai/
  - news_nlp.py : ニュースの LLM センチメントスコアリング（ai_scores 書込）
  - regime_detector.py : マーケットレジーム判定（ma200 と マクロニュース合成）
- src/kabusys/data/
  - pipeline.py : ETL のメイン実装（run_daily_etl など）
  - jquants_client.py : J-Quants API client + 保存ユーティリティ
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management.py : マーケットカレンダー管理・営業日判定
  - news_collector.py : RSS 取得・前処理・安全対策
  - audit.py : 監査ログ用スキーマ初期化 / init_audit_db
  - etl.py : ETLResult 再エクスポート
  - stats.py : 汎用統計ユーティリティ（zscore_normalize）
- src/kabusys/research/
  - factor_research.py : momentum/volatility/value の計算
  - feature_exploration.py : 将来リターン、IC、統計サマリ等
- src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py, ... : 公開 API の整理

---

## 開発・テスト向けヒント

- 自動 .env ロードを無効にするには:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI や J-Quants 呼び出しは外部 API なので、ユニットテストでは該当モジュールの内部 API 呼び出し関数（_call_openai_api や _urlopen、_request など）をモックしてください。
- DuckDB を使ったテストは ":memory:" を指定してインメモリ DB を利用できます（例: duckdb.connect(":memory:")）。

---

## ライセンス・貢献

（ここにプロジェクト固有のライセンスや貢献ルールを追記してください。）

---

不明点や README に追記してほしい例（例: CLI 実行方法、CI 設定、追加依存の詳細など）があれば教えてください。