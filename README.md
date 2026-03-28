# KabuSys

日本株のデータプラットフォームと自動売買支援ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI でのセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注／約定トレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 動作要件 / 依存関係
- セットアップ手順
- 環境変数 (.env)
- 使い方（主要な例）
- ディレクトリ構成
- よくあるトラブルシュート

---

## プロジェクト概要

KabuSys は日本株向けのデータ基盤とリサーチ／自動売買補助ライブラリ群です。  
主に以下の用途を想定しています：

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に格納（ETL パイプライン）
- RSS を収集してニューステーブルに保存し、OpenAI による銘柄センチメント評価を行う
- ETF（1321）やマクロニュースを組み合わせた市場レジーム判定
- ファクター（Momentum / Value / Volatility 等）の計算と探索的解析
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注・約定の監査ログ用スキーマ初期化とユーティリティ

設計上のポイント：
- ルックアヘッドバイアス対策（target_date ベース、date.today() に依存しない処理）
- DuckDB を中心とした軽量な永続化
- OpenAI 呼び出しはリトライとフェイルセーフを含む
- ETL・保存は冪等性を重視（ON CONFLICT / DELETE→INSERT 等）

---

## 主な機能（モジュール一覧・要旨）

- kabusys.config
  - .env の自動読み込み（プロジェクトルートを検出）、環境変数の簡易取得（必須チェック）
- kabusys.data
  - pipeline.run_daily_etl: 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レートリミット）
  - news_collector: RSS 取得・前処理・raw_news への保存
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal_events / order_requests / executions）のスキーマ初期化
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースを集約し OpenAI でスコア化 → ai_scores に保存
  - regime_detector.score_regime: ETF ma200 とマクロニュース（LLM）を合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 動作要件 / 依存関係

必須（少なくとも）：
- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

その他の標準ライブラリや urllib 等を使用。

（プロジェクト側で requirements.txt があればそれに従ってください。ここでは主要パッケージのみ列挙しています）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. インストール
   - 開発・編集する場合:
     ```
     pip install -e .
     ```
   - 必要パッケージを個別にインストールする場合:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定（.env を作成。詳細は次節）
   ```
   cp .env.example .env
   # 編集して必要な値をセット
   ```

5. データディレクトリの準備（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 環境変数 (.env) と設定

kabusys.config.Settings が使用する主な環境変数：

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL      : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID       : Slack チャネル ID（必須）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : 実行環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL              : ログレベル (DEBUG/INFO/...)（デフォルト: INFO）
- OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime 呼び出し時に未指定なら参照）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると自動 .env ロードを無効化

自動読み込み:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` と `.env.local` を自動で読み込みます。テスト等で無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意:
- Settings は必須環境変数が未設定の場合 ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。

---

## 使い方（主要な例）

ここでは代表的な使用例を示します。すべて Python API を直接呼び出す形を想定しています。

- DuckDB に接続して ETL を実行（run_daily_etl）：
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ったニューススコアリング（score_news）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {written} codes")
```

- 市場レジーム判定（score_regime）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```

- ファクター計算（研究用）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- データ品質チェック:
```python
from datetime import date
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

各関数のドキュメント（関数コメント）に詳細な引数・返り値・挙動が記載されています。target_date ベースでルックアヘッドバイアスを避ける設計なので、バックテスト等で使用する場合は target_date を明示してください。

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下の主なファイルとサブパッケージ）

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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult を含む)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - data/__init__.py

主なテーブル（DuckDB 側、コード参照）:
- raw_prices / prices_daily（株価）
- raw_financials（財務）
- market_calendar（JPX カレンダー）
- raw_news / news_symbols（ニュース）
- ai_scores（ニュース由来の銘柄スコア）
- market_regime（レジーム判定結果）
- signal_events / order_requests / executions（監査ログ用）

---

## よくあるトラブルシュート

- 環境変数が足りない:
  - settings の必須キー（JQUANTS_REFRESH_TOKEN 等）が未設定だと ValueError が出ます。.env を作成して設定してください。
- OpenAI 呼び出しが失敗:
  - OPENAI_API_KEY を指定するか、score_news / score_regime に api_key を渡してください。
  - レート制限や一時エラーには内部でリトライやフォールバック（0.0）を行う設計です。
- DuckDB のテーブルがない:
  - ETL でテーブルを作成するか、監査スキーマを初期化する際は init_audit_db / init_audit_schema を使ってください。
- RSS 取得で SSL/DNS/SSRF が問題になる:
  - news_collector は SSRF 対策・レスポンスサイズ制限・gzip チェック等を行います。必要に応じてソース URL を確認してください。

---

README は以上です。詳細は各モジュールの docstring を参照してください。必要なら利用例や CLI スクリプト、CI / テスト用の手順を追記した README の拡張も対応できます。要望があれば教えてください。