# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
DuckDB をデータ層に、J-Quants および RSS / OpenAI を活用してデータ収集・品質検査・AI スコアリング・監査ログを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持ったモジュール群を提供します。

- データ収集（J-Quants からの株価・財務・マーケットカレンダー取得、RSS ニュースの収集）
- ETL パイプライン（差分取得、冪等保存、品質チェック）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア算出）
- 市場レジーム判定（ETF の MA とマクロ記事の LLM スコアを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- 監査ログ（シグナル → 発注 → 約定までのトレーサビリティ用 DB スキーマ）

設計上の特徴：
- ルックアヘッドバイアス対策（内部で date.today() を不用意に参照しない等）
- 冪等操作（DuckDB への保存は ON CONFLICT で上書き）
- フェイルセーフ（外部 API 失敗時は部分的に 0.0 やスキップで継続）
- テストしやすい設計（API 呼び出しの差し替えや自動 env ロードの無効化など）

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API からの取得（株価日足 / 財務 / 上場情報 / マーケットカレンダー）
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
  - レートリミット・リトライ・トークン自動リフレッシュ対応

- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェックの流れ
  - 個別 ETL 関数（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETLResult による実行結果サマリ

- data.quality
  - 欠損 / 重複 / スパイク / 日付不整合 のチェック（QualityIssue を返す）

- data.news_collector
  - RSS フィード取得、前処理、raw_news への冪等保存（SSRF/サイズ/XML 脆弱性対策あり）

- data.calendar_management
  - market_calendar を用いた営業日判定（is_trading_day / next_trading_day / get_trading_days 等）

- data.audit
  - シグナルから約定までの監査テーブル定義と初期化（init_audit_schema / init_audit_db）

- ai.news_nlp
  - 銘柄ごとのニュースセンチメントスコア算出（score_news：gpt-4o-mini を利用、JSON Mode）

- ai.regime_detector
  - ETF（1321）の 200 日 MA 乖離 + マクロ記事 LLM スコアで市場レジームを判定（score_regime）

- research
  - ファクター算出（momentum / value / volatility）、forward returns、IC、統計要約、z-score 正規化

---

## セットアップ手順

前提
- Python 3.10+（typing の Union | 記法等に依存）
- duckdb, openai, defusedxml 等の依存パッケージ

例：仮想環境を使ったセットアップ

1. リポジトリをクローン（もしくはプロジェクトソースを取得）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトに requirements.txt がない場合は最低限以下を入れてください）
   ```
   pip install duckdb openai defusedxml
   ```

4. 開発モードでインストール（任意）
   ```
   pip install -e .
   ```

環境変数 / .env
- プロジェクトは .env / .env.local を自動でルートから読み込みます（CWD 依存せず .git や pyproject.toml を探索してルート判定）。
- 自動ロードを無効にしたい場合は環境変数をセット：
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

主要な環境変数（.env 例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注: Settings にて必須の変数が未設定の場合、アクセス時に ValueError が発生します。

---

## 使い方（コード例）

以下は代表的な使い方の抜粋です。実行前に必要な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成する（ai.news_nlp）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {n_written}")
```

- 市場レジームを判定して保存する（ai.regime_detector）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

- RSS を取得する（news_collector）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用：ファクター算出例
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records))
```

注意点：
- OpenAI を用いる ai モジュールは API 呼び出しでコストが発生します。テスト時はモックを使用してください。
- DuckDB に保存されるタイムスタンプは UTC を前提とする箇所があります（audit.init_audit_schema は TimeZone を UTC に設定します）。

---

## ディレクトリ構成

（主要ファイル／モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py              -- 環境変数 / 設定読み込みロジック（.env 自動読込）
  - ai/
    - __init__.py
    - news_nlp.py          -- ニュースセンチメント（score_news）
    - regime_detector.py   -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント（fetch / save 系）
    - pipeline.py          -- ETL パイプライン（run_daily_etl 等）
    - etl.py               -- ETLResult 再エクスポート
    - news_collector.py    -- RSS 取得・前処理
    - calendar_management.py -- 市場カレンダー / 営業日判定
    - quality.py           -- データ品質チェック
    - stats.py             -- z-score 等統計ユーティリティ
    - audit.py             -- 監査(トレーサビリティ)スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py   -- momentum/volatility/value 等
    - feature_exploration.py -- forward returns, IC, rank, summary
  - research/*             -- 研究用ユーティリティ群

---

## 運用上の注意 / ベストプラクティス

- 環境分離：KABUSYS_ENV（development / paper_trading / live）を使って環境を管理してください。settings.is_live などで挙動分岐が可能です。
- 機密情報：JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY / SLACK_BOT_TOKEN 等は安全に管理してください。`.env` をリポジトリに含めないようにしてください。
- テスト：外部 API 呼び出しはモック化してユニットテストを行ってください。ライブラリ内でも差し替えやすい設計になっています。
- バックテスト：データの取得日は厳密に管理し、Look-ahead バイアスが入らないよう ETL のタイムスタンプ / fetched_at を遵守してください。
- ログレベル：LOG_LEVEL を適切に設定して運用時のノイズを制御してください。

---

もし README に追記したいセクション（例えば CLI 使い方、具体的な SQL スキーマ、デプロイ手順、CI 設定例 等）があれば、用途に合わせて追加のドキュメントを作成します。