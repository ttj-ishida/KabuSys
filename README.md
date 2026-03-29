# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL・データ品質チェック・ニュース収集・AIによるニュースセンチメント解析・市場レジーム判定・各種リサーチ（ファクター計算）・監査ログ（発注／約定トレース）など、取引システム／研究用途に必要な機能群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存関係
- セットアップ手順
- 環境変数（.env）例
- 使い方（主要なユースケース例）
- ディレクトリ構成
- トラブルシューティング・注意点

---

## プロジェクト概要

KabuSys は以下の責務を分離して実装した Python パッケージです。

- J-Quants API からのデータ取得と DuckDB への差分保存（ETL）
- 市場カレンダー管理・営業日判定
- ニュース収集（RSS）と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（銘柄別）とマクロセンチメントを使った市場レジーム判定
- ファクター（Momentum / Volatility / Value 等）の計算と解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ定義・初期化

設計上のポイント：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を安易に参照しない等）
- DuckDB を中心に SQL で効率的に処理
- API 呼び出しはリトライ・バックオフ・レート制御・トークン自動リフレッシュを実装
- 冪等性（ON CONFLICT / DELETE→INSERT 等）を重視

---

## 主な機能（モジュール一覧）

- kabusys.config
  - 環境変数の自動読み込み（.env / .env.local）と設定アクセス（settings）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 + DuckDB 保存関数）
  - pipeline / etl: 日次 ETL パイプライン（run_daily_etl 等）
  - calendar_management: 市場カレンダー管理・営業日演算
  - news_collector: RSS 取得と前処理（SSRF 対策、サイズ制限、トラッキング除去）
  - quality: データ品質チェック（missing / spike / duplicates / date consistency）
  - audit: 監査ログスキーマ作成・初期化（signal_events / order_requests / executions）
  - stats: zscore 正規化など共通統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄別にまとめて OpenAI に投げスコアを保存
  - regime_detector.score_regime: ETF (1321) の MA 乖離とマクロニュースセンチメントを合成して市場レジームを判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提・依存関係

- Python 3.10 以上（型注釈の union 型 `|` を使用）
- 必要なパッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, datetime, json など）

（実際の packaging / requirements.txt がある場合はそちらを優先してください）

---

## セットアップ手順

1. Python 環境準備（3.10+ 推奨）
2. リポジトリをクローン / ソース配置
3. 必要パッケージをインストール
   - 例（最低限）:
     - pip install duckdb openai defusedxml
   - 開発時は editable install:
     - python -m pip install -e .
4. 環境変数を設定（.env ファイルをプロジェクトルートに置くと自動で読み込まれます）
   - 自動ロードは、パッケージからプロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を読み込みます
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 環境変数（.env）例

以下は主要な環境変数の一覧と説明（.env.example として参考にしてください）:

JQUANTS 関連:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

kabuステーション API:
- KABU_API_PASSWORD=your_kabu_api_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 省略可（デフォルト）

Slack:
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567

データベースパス:
- DUCKDB_PATH=data/kabusys.duckdb       # DuckDB ファイルパス（デフォルト）
- SQLITE_PATH=data/monitoring.db        # 監視用 SQLite（必要に応じて）

システム設定:
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|WARNING|ERROR|CRITICAL

OpenAI:
- OPENAI_API_KEY=sk-...

注意: Settings のプロパティは未設定だと ValueError を投げるものがあります（必須変数に依存する機能を呼ぶ場合）。

---

## 使い方（主要ユースケース）

下記は代表的な呼び出し例です。実行前に環境変数と DB パスを設定してください。

1) DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントをスコアリングする（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None は env OPENAI_API_KEY を使用
print(f"scored {count} symbols")
```

3) 市場レジーム（bull/neutral/bear）を計算して保存する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 別 DB にしたい場合は別パスを指定（":memory:" も可）
conn = init_audit_db(settings.duckdb_path)
# 以降 conn を使って発注・約定ログを記録するテーブルが作成されます
```

5) J-Quants から個別銘柄の過去日足を取得して保存（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
import duckdb
from kabusys.config import settings
from datetime import date

records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
conn = duckdb.connect(str(settings.duckdb_path))
saved = save_daily_quotes(conn, records)
print(f"saved {saved} rows")
```

---

## ディレクトリ構成（主要ファイル）

（この README は src/kabusys 配下の実装に基づいています）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - calendar_management.py
      - etl.py
      - pipeline.py
      - stats.py
      - quality.py
      - audit.py
      - jquants_client.py
      - news_collector.py
      - (その他 jquants_client の補助関数等)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/__init__.py
    - (将来的に strategy / execution / monitoring 等のパッケージを含む想定)

---

## トラブルシューティング・注意点

- 環境変数が未設定な場合、多くの関数が ValueError を投げます。必須のキーを .env に設定してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。テスト時などで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants API 呼び出しはネットワークやレート制限の影響を受けます。ライブラリはリトライ・バックオフを実装していますが、API キー・クォータを事前に確認してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあります（コード内で空チェックを入れていますが、環境によって差異が出る可能性があるため注意）。
- news_collector は RSS の取得時に SSRF 対策・サイズ制限・XML の安全パースを行います。外部フィードを追加する場合もその点に留意してください。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかで、live の場合は実際の発注等を行うモジュールが導入される想定です（本コードベースの該当部分は分離設計）。

---

必要であれば、README にサンプル .env.example、より詳細な API 説明（各関数の引数・戻り値）、ユニットテストの実行方法や CI の設定例なども追加できます。どの部分を優先して追記しましょうか？