# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注・約定トレース）などを提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡単な例）
- ディレクトリ構成（主要ファイル説明）
- 環境変数 / 設定について
- 補足（自動 .env ロード挙動など）

---

## プロジェクト概要

KabuSys は日本株を対象とした以下の機能を統合的に提供する Python パッケージです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの ETL（差分取得、冪等保存、品質チェック）
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- ETF（1321）を利用した市場レジーム判定（MA200 とマクロセンチメントの合成）
- 研究用ファクター計算（Momentum / Volatility / Value など）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）用の DuckDB スキーマ初期化ユーティリティ
- データ品質チェックモジュール（欠損・スパイク・重複・日付整合性）

設計方針として、Look-ahead バイアス回避・冪等性・フェイルセーフ（API 失敗時はスキップして継続）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存関数、認証、リトライ、レート制限）
  - pipeline: 日次 ETL 実行 run_daily_etl など
  - news_collector: RSS 取得と前処理（SSRF 対策・トラッキング除去）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査ログテーブル初期化・監査 DB 作成
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメント生成（OpenAI）
  - regime_detector.score_regime: ETF MA200 とマクロニュースを合成した市場レジーム判定
- research/
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数読み込み・Settings（自動 .env ロード、必須設定の検証）
- audit / monitoring 周りの DB 初期化、監査テーブルの作成支援

---

## セットアップ手順

1. リポジトリをクローン

   git clone <リポジトリURL>
   cd <repo>

2. Python 環境の準備（推奨: venv）

   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージのインストール

   requirements.txt がない場合は代表的なパッケージをインストールしてください：

   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）
   pip install -r requirements.txt

4. 環境変数設定

   プロジェクトルートに `.env`（および任意で `.env.local`）を作成してください。以下は最低限必要となる代表的な環境変数例です：

   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-....

   注意:
   - config モジュールはデフォルトでプロジェクトルート（.git または pyproject.toml のある場所）を探索し、`.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須項目が不足していると Settings プロパティで ValueError が発生します。

5. データディレクトリの作成（任意）

   デフォルトの DuckDB ファイルは `data/kabusys.duckdb`、監視用 SQLite は `data/monitoring.db` です。必要に応じてディレクトリを作成してください。

   mkdir -p data

---

## 簡単な使い方（コード例）

以下は代表的なモジュールの呼び出し例です。実行前に環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）が必要です。

- Settings の読み取り

```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.env)          # 'development' / 'paper_trading' / 'live'
```

- DuckDB 接続と日次 ETL 実行

```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を省略すると今日を基準に実行
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI 使用）

```python
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n = score_news(conn, target_date=date(2026, 3, 20))  # 指定日のニュースを評価
print(f"scored {n} codes")
```

- 市場レジーム判定（1321 の MA200 とマクロニュース統合）

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算例

```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records))
```

- 監査 DB の初期化（監査テーブル作成）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # transactional=True を渡すことも可
```

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py: パッケージ初期化、バージョン情報
  - config.py: 環境変数読み込み・Settings（自動 .env ロード、必須チェック）
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py: ニュースのバッチセンチメントスコアリング（OpenAI 呼び出し、レスポンス検証、DuckDB への書き込み）
  - regime_detector.py: ETF(1321)の MA200 乖離とマクロセンチメントを合成して市場レジーム判定
- src/kabusys/data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得 / 保存 / 認証 / リトライ / rate limit）
  - pipeline.py: ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector.py: RSS 収集、前処理、raw_news への保存処理補助
  - calendar_management.py: 市場カレンダー管理、営業日判定ユーティリティ
  - quality.py: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit.py: 監査ログスキーマ定義・初期化・init_audit_db
  - stats.py: 汎用統計ユーティリティ（zscore_normalize）
  - etl.py: ETLResult の再エクスポート
- src/kabusys/research/
  - __init__.py
  - factor_research.py: Momentum / Volatility / Value 計算
  - feature_exploration.py: 将来リターン計算、IC 計算、統計要約、ランク関数

---

## 環境変数 / 設定

主な環境変数（Settings 経由で参照・必須/任意）:

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL で使用）
  - KABU_API_PASSWORD: kabuステーション API 連携用パスワード
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- 任意（デフォルト値あり）
  - KABUSYS_ENV: 'development' (default) / 'paper_trading' / 'live'
  - LOG_LEVEL: 'INFO' (default), 'DEBUG' / 'WARNING' / 'ERROR' / 'CRITICAL'
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると自動 .env ロードを無効化
  - OPENAI_API_KEY: News NLP / Regime Detector が OpenAI を呼ぶ際の API キー（関数引数で上書き可能）
  - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH: デフォルト "data/monitoring.db"

config.Settings は不足した必須値を検出した場合 ValueError を投げます。

自動 .env 読み込みの挙動:
- プロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を探索し、
  見つかった場合、`.env`（低優先）と `.env.local`（高優先）を読み込みます。
- OS 環境変数優先。既に設定されているキーは上書きされません（ただし .env.local は override=True の挙動で上書きするが、OS 環境変数は保護されます）。
- 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用途など）。

---

## 補足・運用上の注意

- OpenAI 呼び出しは外部 API に依存しており、失敗時はフェイルセーフとしてスコア 0.0（またはスキップ）へフォールバックする設計です。API の利用状況に応じてリトライやレート制御が組み込まれています。
- J-Quants API にはレート制限（120 req/min）を守るための RateLimiter を実装しています。
- DuckDB に対する INSERT は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で設計されています。
- 本ライブラリの多くの関数は外部通信を伴うため、ユニットテスト時は該当関数を patch / mock することを推奨します（コード中にテスト差し替えを想定した箇所が複数あります）。

---

README に書かれている以外の使い方や詳細はソースコード内のドキュメントストリング（docstring）を参照してください。  
必要であれば利用シナリオ別のサンプルや運用手順（cron / ワーカー構成など）も追記します。