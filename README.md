# KabuSys

KabuSys は日本株向けデータプラットフォームとリサーチ / 自動売買補助ライブラリ群です。J-Quants からデータを取得して DuckDB に永続化し、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ用スキーマなどのユーティリティを提供します。

主な用途例:
- 日次 ETL による株価・財務・市場カレンダーの差分取得と保存
- ニュース記事の収集と LLM を使った銘柄センチメントスコア付与
- 市場レジーム判定（MA200 と マクロニュースの LLM センチメントの合成）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）とリサーチ用ユーティリティ
- 取引関連の監査ログスキーマ初期化（監査性・冪等性を考慮）

---

## 機能一覧

- data
  - J-Quants クライアント (fetch / save / 認証・リトライ・レート制御)
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days 等）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集ユーティリティ（RSS 取得・前処理）
  - 監査ログ（audit）: signal_events / order_requests / executions テーブル定義と初期化関数
  - 統計ユーティリティ（zscore 正規化 等）
- ai
  - ニュース NLP スコアリング（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI 呼び出しは gpt-4o-mini を JSON モードで利用（リトライ・フォールバック実装あり）
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込み・管理（.env / .env.local 自動ロード、必須設定取得ユーティリティ）

---

## 動作要件

- Python 3.10+
- 必要な外部パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS ソース, OpenAI API）

（プロジェクトルートに requirements.txt がある場合はそれを利用してください。なければ上記パッケージをインストールしてください）

---

## セットアップ手順（例）

1. レポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）
4. 環境変数を設定
   - プロジェクトルートに `.env` を置くか、OS 環境変数を設定します。自動的に `.env` と `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - SLACK_BOT_TOKEN — Slack 通知に使用（必須）
     - SLACK_CHANNEL_ID — Slack チャンネルID（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI を使う場合は必須（ai モジュールを使用する際）
   - 任意（デフォルトあり）:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

5. データベースの準備
   - DuckDB を使う場合は `settings.duckdb_path` で指定したパスの親ディレクトリが自動作成されます（必要な場合）。

---

## 使い方（主要 API の例）

以下は Python インタプリタやバッチスクリプト内での利用例です。

- 共通準備
  - 環境変数を設定し、Python 仮想環境を有効化した状態で実行します。

1) 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を None にすると今日を基準に実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアを生成する（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 引数 api_key を渡すか、環境変数 OPENAI_API_KEY を設定
n = score_news(conn, date(2026, 3, 20), api_key=None)
print(f"scored {n} symbols")
```

3) 市場レジームをスコアリングする（1321 の MA200 とマクロニュースの合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, date(2026, 3, 20))
```

4) 監査ログ用スキーマ（audit）を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリがなければ自動作成
# 返り値は DuckDB 接続
```

5) RSS フィードを取得する（ニュース収集の単体利用）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
for a in articles:
    print(a["datetime"], a["title"], a["url"])
```

6) J-Quants API を直接呼んでデータ取得（必要な認証情報は settings で管理）
```python
from kabusys.data import jquants_client as jq
# id_token は省略可能（内部でキャッシュ/リフレッシュされる）
quotes = jq.fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
print(len(quotes))
```

7) リサーチ用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(moms, ["mom_1m", "mom_3m", "mom_6m"])
```

注意:
- AI 関連関数は OpenAI API を呼び出します。API 利用に伴うコストに注意してください。
- ETL / 保存系関数は DuckDB に対して執拗な変更を行うため、本番 DB を上書きしないように注意してください（バックアップ推奨）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants のリフレッシュトークン
- OPENAI_API_KEY（ai を使う場合）: OpenAI API キー
- KABU_API_PASSWORD（必須）: kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN（必須）: Slack ボットトークン（通知などで利用）
- SLACK_CHANNEL_ID（必須）: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH: 実行プロセス用 PID ファイルパス（デフォルト data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

.env を配置すればプロジェクトルート検出により自動で読み込まれます（.env.local は .env を上書き）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py (ETL result re-export)
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: audit 初期化ユーティリティ等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/__init__.py は zscore_normalize とファクター関数を再エクスポート

（上記はリポジトリ内で提供されている主要モジュールです。実際のファイル・追加モジュールはリポジトリ内をご確認ください）

---

## 設計上の注意点 / ベストプラクティス

- Look-ahead bias を避けるため、関数群は内部で datetime.today() / date.today() を直接参照しないよう設計されています。テスト・バッチ実行時は明示的に target_date を渡すことを推奨します。
- OpenAI や J-Quants API 呼び出しはリトライ・バックオフ・フォールバックが組み込まれていますが、API 料金やレート制限には注意してください。
- DuckDB に対する INSERT/UPDATE は基本的に冪等性（ON CONFLICT）を考慮して実装されていますが、ETL 実行前のスキーマ準備やバックアップを推奨します。
- ニュース収集は SSRF / XML 攻撃対策（defusedxml、ホスト検査、リダイレクト検査、受信サイズ制限）を行っていますが、公開用途ではさらに運用上の安全対策が必要です。

---

README は概要と導入のための最小限の案内を目的としています。詳細な開発者向け情報（CI / テスト / デプロイ手順、API の細かい仕様、スキーマ定義）はリポジトリ内のドキュメント（もしあれば）や各モジュールの docstring を参照してください。必要であれば README に追記すべきセクション（例: 実運用でのデプロイ手順、例 .env.example のテンプレート）を教えてください。