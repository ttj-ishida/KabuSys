# KabuSys

日本株向けのデータプラットフォーム + 自動売買/調査ユーティリティ群（KabuSys）。  
DuckDB をデータ基盤に、J-Quants と RSS / OpenAI を活用してデータ取得・品質チェック・AI スコアリング・レジーム判定・ファクター算出・ETL パイプライン・監査ログ管理を行うためのライブラリ群です。

主な用途：
- J-Quants から株価・財務・カレンダーを差分取得して DuckDB に蓄積する ETL
- ニュース記事の収集と LLM によるセンチメントスコア付与（銘柄別 ai_score）
- マーケットレジーム判定（MA200 と マクロニュースの LLM センチメントを合成）
- 研究用ファクター（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマ初期化と DB 操作
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env / 環境変数の自動読み込み、設定オブジェクト `settings`
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 + DuckDB 保存用関数）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, ...）と ETLResult
  - news_collector: RSS 取得・前処理・raw_news 保存ロジック（SSRF/Gzip 対策等）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用スキーマ初期化・監査DB初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM で銘柄別センチメント算出 → ai_scores へ保存
  - regime_detector.score_regime: ETF(1321) MA200 とマクロニュース LLM を合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件（推奨）

- Python 3.10+
- DuckDB
- openai (OpenAI Python client)
- defusedxml
- そのほか標準ライブラリで賄える部分が多いですが、外部ライブラリは requirements.txt を整備しておくことを推奨します。

例（requirements の参考）:
- duckdb
- openai
- defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

3. パッケージを開発モードでインストール（ローカル開発向け）
   - pip install -e .

4. 環境変数 / .env の用意
   - プロジェクトルート（pyproject.toml や .git があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須例:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...   （AI機能を使う場合）
   - 任意:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. DuckDB ファイルの親ディレクトリを作成（必要なら）
   - mkdir -p data

---

## 使い方（主要ユースケースの例）

以下は Python スクリプトや対話環境での簡単な例です。すべて Look-ahead バイアス防止のため、明示的な target_date を与える設計です。

共通準備:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースを LLM でスコアリングして ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーを明示的に渡すか、環境変数 OPENAI_API_KEY を設定
num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", num_written)
```

3) 市場レジームスコアを計算して market_regime に書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用 DB を初期化して接続を取得する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査ログ操作や schema の存在を確認できます
```

5) 研究用ファクター計算（例: momentum）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト。必要に応じて zscore_normalize を適用
```

ログ設定の例:
```python
import logging
logging.basicConfig(level=settings.log_level)
```

注意点:
- OpenAI 呼び出しには OPENAI_API_KEY が必要。API レートや課金に注意してください。
- J-Quants API 呼び出しは JQUANTS_REFRESH_TOKEN を使って id_token を取得します（settings.jquants_refresh_token）。
- DuckDB の SQL スキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）は事前に作成しておく必要があります。本リポジトリにはスキーマ初期化用ユーティリティが含まれている場合があるので、プロジェクトの schema 定義を参照してください。

---

## ディレクトリ構成（抜粋）

（パッケージは src/kabusys 以下に格納）
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースの LLM スコアリング（ai_scores）
    - regime_detector.py       — 市場レジーム判定（market_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch / save）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult の再エクスポート
    - news_collector.py        — RSS 収集・前処理・raw_news 保存
    - calendar_management.py   — 市場カレンダー & 営業日ユーティリティ
    - quality.py               — データ品質チェック
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査ログテーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py       — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py   — 将来リターン / IC / summary / rank
  - research/ (他の研究ユーティリティ群)
  - (その他 strategy / execution / monitoring 等のサブパッケージを用意可能)

---

## 運用時の注意・設計方針（抜粋）

- Look-ahead bias を避けるため、日付参照は明示的な target_date を使う設計。datetime.today()/date.today() を内部で使わないよう配慮。
- API 呼び出しはリトライ（指数バックオフ）とフェイルセーフを備え、一部失敗しても全体処理を継続する設計。
- ニュース収集は SSRF / Gzip Bomb / XML Attack（defusedxml）等の対策を実装。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE）で行う。
- 監査ログは発注フローを完全にトレースできるスキーマで設計（削除しない前提）。

---

## もっと知りたい / 追加作業

- スキーマ（DuckDB の CREATE TABLE 文）やマイグレーション、CI のテスト等は別途用意してください。
- 実運用では J-Quants と OpenAI のレート制限・認証・課金管理に注意してください。
- Slack 経由の通知や kabuステーション API（発注・注文管理）連携は本リポジトリに接続レイヤを追加して実装してください。

---

質問や README の補足（例: 実行スクリプト、初期スキーマ、requirements.txt の生成など）が必要であれば、用途に合わせて追記します。