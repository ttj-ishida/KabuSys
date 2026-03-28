# KabuSys

日本株向け自動売買/データプラットフォームのコアライブラリ群です。  
データ取得（J-Quants）、ニュース収集・NLP（OpenAI）、ETL、研究用ファクター計算、監査ログ等を含むモジュール群を提供します。

## プロジェクト概要
KabuSys は以下を目的とした Python パッケージです。

- J-Quants API を用いた株価・財務・上場情報・市場カレンダーの差分取得（ETL）
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI を用いたニュースセンチメント解析（銘柄別／マクロ判定）
- マーケットレジーム判定（ETF の MA とマクロセンチメントの合成）
- 研究用ファクター算出（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック・監査ログスキーマの初期化・管理

設計のポイント:
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しない設計）
- DuckDB を主な永続ストアとして想定
- API 呼び出しはレートリミット・再試行・フォールバック実装あり
- 冪等性を考慮した保存処理（ON CONFLICT 等）

---

## 機能一覧
主な機能（抜粋）:

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch_*, save_*）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS 取得、前処理、raw_news への保存補助）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news：銘柄ごとのニュースセンチメント算出 → ai_scores テーブルへ）
  - マクロレジーム判定（score_regime：ETF 1321 の MA 乖離＋マクロセンチメント合成 → market_regime へ）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- 設定管理（kabusys.config）：.env 自動ロード機能・必須環境変数チェック

---

## 必要条件
- Python 3.10+
- 主に以下ライブラリを想定（プロジェクトに合わせて requirements を用意してください）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ

例（最低限）:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -e .        （パッケージが setuptools/pyproject を持つ場合）
   - または最低限: pip install duckdb openai defusedxml
4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env/.env.local を置くと、kabusys.config が自動で読み込みます。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主なもの）
以下はコード中で参照される主要な環境変数です。README 用のサンプル .env を作る際の参考にしてください。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client/get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注モジュールと連携する場合）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID: Slack 投稿先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db

OpenAI:
- OPENAI_API_KEY: OpenAI を使う場合の API キー（score_news, score_regime など）

注意:
- config.py はプロジェクトルートから .env/.env.local を自動ロードします（OS 環境変数が優先）。.env.local は .env を上書きします。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

サンプル .env.example:
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（基本例）
以下は代表的な操作の Python 例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続の作成例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026,3,20))
print(res.to_dict())
```

- ニュースの NLP スコア付与（score_news）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡す
n = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n} codes")
```

- マーケットレジーム判定（score_regime）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査 DB 初期化（監査ログ専用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db はスキーマ作成後の接続を返します
```

- 監査スキーマのみ既存接続に追加:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- 研究用ファクター計算:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

m = calc_momentum(conn, date(2026,3,20))
v = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

---

## 開発・テスト時のヒント
- 自動で .env を読み込みたくないテストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI や J-Quants の外部呼び出しはテスト時にモック化可能な構造になっています（各モジュールは内部呼び出し関数をパッチできるように設計されています）。
- DuckDB の一時的なインメモリ DB を使う場合は db_path に ":memory:" を渡せます（init_audit_db 等）。

---

## ディレクトリ構成（主要ファイル）
（リポジトリ内 src/kabusys を基準に抜粋）

- src/kabusys/
  - __init__.py  -- パッケージ定義
  - config.py    -- 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py (score_news の公開)
    - news_nlp.py        -- ニュースセンチメント（銘柄別）
    - regime_detector.py -- マクロ + MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  -- J-Quants API クライアント + 保存処理
    - pipeline.py        -- ETL パイプライン実装（run_daily_etl 等）
    - etl.py             -- ETLResult を公開
    - news_collector.py  -- RSS 取得・前処理（SSRF 対策等）
    - calendar_management.py -- マーケットカレンダー管理
    - stats.py           -- 統計ユーティリティ（zscore_normalize）
    - quality.py         -- データ品質チェック
    - audit.py           -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py -- モメンタム / バリュー / ボラティリティ
    - feature_exploration.py -- 将来リターン / IC / サマリー等

---

## ライセンス・貢献
この README はコードベースの説明目的です。実際のライセンス・貢献フローはリポジトリの LICENSE と CONTRIBUTING を参照してください。

---

もし README に加えたい運用手順（cron/airflow での ETL スケジューリング例、Slack 通知設定例、kabu ステーション連携手順等）があれば、その用途に合わせて追加テンプレートやサンプルを作成します。どの情報を追記しますか？