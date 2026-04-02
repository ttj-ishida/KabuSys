# KabuSys

日本株向け自動売買 / データパイプライン基盤ライブラリ

短い説明:
KabuSys は日本株のデータ収集（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを組み合わせて、自動売買システムやリサーチパイプラインの基盤処理を提供する Python パッケージです。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 要件
- セットアップ手順
- 環境変数（.env）と自動ロード
- 使い方（主要 API サンプル）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下のような機能をモジュール化して提供します。

- J-Quants API を使った株価 / 財務 / 市場カレンダーの差分 ETL（レート制御・リトライ・ページネーション対応）
- DuckDB を用いたデータ保存・統計処理・品質チェック
- RSS ベースのニュース収集と前処理（SSRF対策・トラッキングパラメータ除去・正規化）
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメント付与（銘柄ごと / マクロ）
- ETF の移動平均や LLM センチメントを組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）および特徴量解析ユーティリティ
- 監査ログテーブル（signal_events, order_requests, executions）の初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計方針のポイント:
- ルックアヘッドバイアスを避ける（内部で date.today() 等に依存しない設計）
- 冪等性（DB 保存は ON CONFLICT DO UPDATE 等で上書き）
- フェイルセーフ（外部 API 失敗時は処理を継続・ログ化）
- DuckDB を中心に SQL で高速に集計・ウィンドウ処理

---

## 機能一覧

主要機能（モジュール別）

- kabusys.config
  - .env ファイルと環境変数読み込み、設定アクセス（settings オブジェクト）
- kabusys.data.jquants_client
  - J-Quants API 経由の fetch/save 関数（株価、財務、カレンダー、上場銘柄情報）
  - rate limiter / retry / token refresh を内蔵
- kabusys.data.pipeline / etl
  - run_daily_etl や個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETLResult による実行結果集約
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合チェック
- kabusys.data.news_collector
  - RSS 収集、前処理、raw_news テーブルへの保存補助
- kabusys.data.calendar_management
  - 市場カレンダーの営業日判定・前後営業日探索・夜間更新ジョブ
- kabusys.data.audit
  - 監査ログテーブル DDL と初期化（init_audit_schema / init_audit_db）
- kabusys.ai.news_nlp
  - 銘柄別ニュースセンチメント（batch 化 / OpenAI 呼び出し / レスポンス検証）
- kabusys.ai.regime_detector
  - ETF(1321)の MA 乖離 + マクロセンチメントから市場レジームを日次スコアリング
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank

---

## 要件

- Python 3.10+（Union 型演算子（|）を使用）
- duckdb
- openai（OpenAI SDK）
- defusedxml
- その他標準ライブラリ

（実際の requirements はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは pyproject.toml がある場合: pip install -e .
4. 環境変数を設定
   - プロジェクトルートに .env（または .env.local）を作成（下記参照）
5. DuckDB / 監査 DB を初期化（任意）
   - Python REPL かスクリプトから init_audit_db を呼ぶ:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
6. ETL やその他処理を実行（下記 usage を参照）

---

## 環境変数（.env）と自動ロード

KabuSys の設定は環境変数経由で取得されます。ルート（.git または pyproject.toml 所在）に置いた `.env` / `.env.local` は自動で読み込まれます（os 環境変数 > .env.local > .env の優先順）。テスト等で自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（settings で参照される）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- PID_FILE_PATH (任意) — デフォルト: data/execution.pid
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV — 有効値: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールは引数でも受け取れる）

.env の例（.env.example を参考にしてください）:
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567

注意:
- .env のクォート・コメント処理は config モジュールのパーサに従います。
- OS 環境変数は .env による上書きを保護します。

---

## 使い方（主要 API サンプル）

以下は代表的な利用例です。実際のスクリプトではログ設定や例外処理を行ってください。

1) ETL（日次パイプライン）
- 日次 ETL を実行してデータ取得・品質チェックを行う:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースセンチメント付与（銘柄別）
- raw_news / news_symbols が整備された DuckDB 接続で実行:

from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
print(f"scored {count} codes")

3) 市場レジーム判定
- ETF(1321) の MA 乖離とマクロニュースの LLM 評価を合成して market_regime テーブルへ書き込む:

from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")

4) 研究用ファクター計算
- calc_momentum / calc_volatility / calc_value 等:

from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))

5) カレンダー関連ユーティリティ

from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))

6) 監査ログ初期化

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")

7) RSS 取得（ニュース収集）
- fetch_rss を使って外部 RSS から記事を取得・前処理して保存処理に渡す：

from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
# articles は dict のリスト（id, datetime, source, title, content, url）

注意点:
- OpenAI 呼び出しは API キーの設定が必要です（引数または環境変数 OPENAI_API_KEY）。
- J-Quants は rate limit 制約があり、jquants_client により制御されます。
- ETL の各フェーズは失敗時にログ化して続行する設計です（呼び出し側で result.errors を確認してください）。

---

## ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ（抜粋）

src/kabusys/
- __init__.py
- config.py                        — 環境変数 / .env パーサと Settings
- ai/
  - __init__.py
  - news_nlp.py                     — ニュース NLP（銘柄別センチメント）
  - regime_detector.py              — 市場レジーム判定（ETF MA + macro sentiment）
- data/
  - __init__.py
  - jquants_client.py               — J-Quants API クライアント + DuckDB 保存
  - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
  - etl.py                          — ETL インターフェース再エクスポート
  - quality.py                      — データ品質チェック
  - news_collector.py               — RSS 収集 / 前処理
  - calendar_management.py          — 市場カレンダーと営業日ユーティリティ
  - audit.py                         — 監査ログ DDL / 初期化
  - stats.py                         — zscore_normalize 等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py              — モメンタム / ボラティリティ / バリュー 等
  - feature_exploration.py          — 将来リターン / IC / 統計サマリー
- research/*（上記）
- その他: strategy, execution, monitoring（パッケージ内公開予定）

ルート:
- pyproject.toml / setup.py / requirements.txt（プロジェクトルートに配置）

---

## 開発・テスト

- 自動ロードを無効にしてユニットテストを実行する場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 pytest
- OpenAI / J-Quants の外部依存はモックしてテストする設計（各モジュール内部で _call_openai_api などを差し替え可能）

---

## 備考・注意点

- DuckDB の SQL 文はパラメータバインド(?) を使用しており、SQL インジェクションリスクに配慮しています。
- J-Quants の認証トークン自動リフレッシュやレート制御は jquants_client が管理しますが、外部 API の仕様変更により追加対応が必要になる場合があります。
- ニュース収集では SSRF 対策・レスポンスサイズ制限・XML 脆弱性防止（defusedxml）を実装しています。
- 監査ログ設計は削除禁止・タイムスタンプは UTC といった前提があります。運用時は DB のタイムゾーンと照合してください。

---

質問や追加で README に入れたい使い方（例: CLI、docker、CI 設定）があれば教えてください。必要に応じてサンプルスクリプトや .env.example を作成します。