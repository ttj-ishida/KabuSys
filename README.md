# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と AI によるニュースセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）、市場レジーム判定などを提供します。

---

## 主な特徴

- データ取得（J-Quants）と ETL パイプライン（差分取得・バックフィル・品質チェック）
- DuckDB ベースのデータ保存と冪等性を考慮した保存処理
- ニュース収集（RSS）と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を利用したニュース単位／マクロセンチメント評価（JSON Mode）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 設定は環境変数 / .env ファイルで管理。自動読み込み機能あり（パッケージ内で実装）

設計上のポイント:
- ルックアヘッドバイアス対策（多くの処理で datetime.today()/date.today() を直接参照しない）
- API 呼び出しにはリトライと指数バックオフ、レートリミット制御を実装
- 外部依存は最小限（OpenAI SDK、duckdb、defusedxml 等を使用）

---

## 機能一覧（モジュールごと）

- kabusys.config
  - 環境変数の読み込み（.env/.env.local、自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
  - settings オブジェクト経由で設定にアクセス
- kabusys.data
  - jquants_client: J-Quants API クライアント（データ取得・保存）
  - pipeline: 日次 ETL 実行（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 収集と前処理、raw_news への保存ロジック
  - calendar_management: 市場カレンダー管理、営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化・専用 DB 初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを計算して ai_scores に保存
  - regime_detector.score_regime: マクロセンチメントと ETF MA を合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンしてパッケージをインストール（editable 推奨）

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e .
   ```

2. 依存パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - それ以外に標準ライブラリのみで動くよう設計されていますが、実行環境に応じて上記をインストールしてください。

   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定（.env をプロジェクトルートに置くと自動で読み込まれます）
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   推奨の .env（例）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # OpenAI
   OPENAI_API_KEY=sk-...

   # DB
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境とログ
   KABUSYS_ENV=development    # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   注意:
   - 必須環境変数（settings が要求するもの）は、
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - （多くの機能は OPENAI_API_KEY を使用。score_news/score_regime に api_key を直接渡すことも可能）

---

## 使い方（簡単な例）

- settings の利用例:

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須（未設定時は ValueError）
print(settings.duckdb_path)
print(settings.is_live)
```

- 日次 ETL を実行（DuckDB 接続を渡す）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア算出（OpenAI API キーは env で設定するか api_key 引数で渡す）:

```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect('data/kabusys.duckdb')
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> env OPENAI_API_KEY を参照
print(f"scored {n_written} codes")
```

- 市場レジーム判定:

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 研究用ファクター計算（例: momentum）:

```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect('data/kabusys.duckdb')
factors = calc_momentum(conn, target_date=date(2026,3,20))
# factors は dict のリスト: [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

- 監査ログ用 DB 初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルへ書き込みが可能
```

- カレンダー関係ユーティリティ:

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect('data/kabusys.duckdb')
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## ディレクトリ構成（概要）

- src/kabusys/
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
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - (その他データ関連ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research パッケージからは zscore_normalize 等を再エクスポート
- pyproject.toml / setup.cfg / .git/ 等（プロジェクトルート）

（上記は提供されたコードベースの主要ファイルと責務の概観です）

---

## 実行上の注意点・運用メモ

- OpenAI API を利用する処理（news_nlp, regime_detector）はコスト・レート制限に注意してください。API 呼び出しはリトライとバックオフを実装していますが、運用時はスロットルやコスト上限の管理が必要です。
- ETL / API 呼び出しはネットワークや外部 API に依存するため、運用ではログ監視や再実行戦略を用意してください。
- settings.env: KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければエラーになります。is_live / is_paper / is_dev の判定があります。
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を読み込みます。
  - OS 環境変数は優先されます。.env.local は .env を上書きします。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Look-ahead バイアス対策: 多くの関数は target_date 引数や DB の過去データのみを参照するよう設計されています。バックテストで使用する場合は、必ず過去時点で利用可能なデータ状態を再現してください。
- DuckDB の executemany に空リストを与えると問題になる古いバージョンへの対策がコード中にあります。運用環境の duckdb バージョンに注意してください。

---

## 貢献・拡張

- 新しいニュースソースの追加は data/news_collector.py の RSS ソース定義とパース処理を拡張してください。
- OpenAI モデルの変更やプロンプト調整は ai/news_nlp.py と ai/regime_detector.py の _SYSTEM_PROMPT や _MODEL を編集してください（JSON Mode を使用）。
- 監査ログのスキーマ変更は data/audit.py に反映し、init_audit_schema / init_audit_db を用いてマイグレーションしてください。

---

README では主要な使い方とモジュール責務をまとめました。個別の関数や API（引数・返値の形式など）はソースコードの docstring を参照してください。追加で「開発用の実行例」「CI 設定」「テスト手順」などを加えたい場合は、その要件を教えてください。