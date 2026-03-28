# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
データの ETL、ニュースの NLP スコアリング、ファクター計算、監査ログ（トレーサビリティ）、および市場レジーム判定などの機能を提供します。

主な設計方針:
- DuckDB を中心にデータを保存・集計（ETL／品質チェック）
- J-Quants API を用いたデータ収集（レート制限・リトライ・トークン自動更新対応）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON Mode）
- ルックアヘッドバイアス防止に配慮（内部で today() を参照しない設計など）
- 冪等性（ON CONFLICT / UUID / order_request_id を冪等キー）を重視

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch/save 日足・財務・カレンダー等）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS -> raw_news、SSRF対策・トラッキング除去・記事IDハッシュ）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize 等）
- ai
  - ニュース NLP（score_news: ニュースを銘柄ごとに LLM でスコア）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロニュースを合成）
- research
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC（Spearman）計算, 統計サマリー）
- config
  - .env / 環境変数の自動ロードと設定管理（Settings クラス）

---

## 前提・依存

- Python 3.10+
- 必須パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
- その他プロジェクトに応じて:
  - urllib / json / logging 等は標準ライブラリで利用

パッケージ化されている前提であれば、下記のようにインストールできます（プロジェクト配布方法に依存します）:

```bash
python -m pip install -e .
# または個別に
python -m pip install duckdb openai defusedxml
```

必要に応じて requirements.txt を用意してください。

---

## 環境変数（主なもの）

自動ロード:
- プロジェクトルート（.git または pyproject.toml を探索）に存在する `.env` と `.env.local` を読み込みます。読み込み順は:
  1. OS 環境変数（優先）
  2. .env.local（override=True）
  3. .env（override=False）
- 自動ロードを無効化するには: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

必須の環境変数（Settings で _require されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — 通知先チャンネル ID

任意 / デフォルトがあるもの:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト: INFO）
- KABU_API_BASE_URL — デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH — デフォルト `"data/kabusys.duckdb"`
- SQLITE_PATH — デフォルト `"data/monitoring.db"`
- OPENAI_API_KEY — OpenAI 呼び出し時の API キー（ai.score_* 呼び出しで引数で渡すことも可能）

例 (`.env`):

```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発向け）

1. Python 3.10 以上を用意
2. リポジトリをクローン
3. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
4. 必要パッケージをインストール
   - pip install -e .  または  pip install duckdb openai defusedxml
5. `.env`（または環境変数）をセット
6. DuckDB 用のディレクトリを作成（必要なら）
   - mkdir -p data

---

## 使い方（主要 API と実行例）

以下は一例です。実際のアプリではログ設定やエラーハンドリングを追加してください。

- DuckDB 接続を作って日次 ETL を実行:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# 既定では settings.duckdb_path に保存されるファイルを使用する場合
conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアの付与（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数）:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn は duckdb 接続、target_date はスコア対象日
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored codes:", count)
```

- 市場レジーム判定:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB の初期化:

```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

conn = init_audit_db(Path("data/audit.duckdb"))
# conn は初期化済み DuckDB 接続
```

- RSS 取得（ニュースコレクタの一部）:

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点:
- score_news / score_regime は大量の OpenAI 呼び出しを行う可能性があり、API 使用料やレート制限に注意してください。両モジュールともリトライとフォールバック（失敗時は 0.0 を使う等）を備えています。
- jquants_client は API レート制限（120 req/min）を守る実装になっています。get_id_token はリフレッシュトークンから id token を取得します。

---

## 主要モジュール / ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py         -- ニュースの LLM スコアリング
    - regime_detector.py  -- マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py   -- J-Quants API クライアント（fetch / save）
    - pipeline.py         -- ETL パイプライン（run_daily_etl など）
    - calendar_management.py -- 市場カレンダー管理
    - news_collector.py   -- RSS 収集（SSRF 対策等）
    - quality.py          -- データ品質チェック
    - stats.py            -- 統計ユーティリティ（zscore_normalize）
    - audit.py            -- 監査ログスキーマ初期化（監査テーブル）
    - etl.py              -- ETL 結果型の再エクスポート
  - research/
    - __init__.py
    - factor_research.py  -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py -- 将来リターン、IC、統計サマリ
  - research/*.py
  - (その他: strategy, execution, monitoring 等の名前空間がエクスポートされる想定)

---

## 実装上の注意 / 設計メモ

- ルックアヘッドバイアス対策:
  - 多くのモジュールは date 引数を明示して内部で date.today() を直接参照しないよう設計されています（バックテスト向けに過去データのみを参照）。
- 冪等性:
  - ETL の保存関数は ON CONFLICT DO UPDATE を使い再度挿入しても安全。
  - audit.order_requests の order_request_id は冪等キーとして利用。
- LLM 呼び出し:
  - OpenAI Chat Completions を JSON Mode で利用し、厳密な JSON 出力を期待する設計。
  - リトライや 5xx 対応が入っているが、最終的にエラーやパース失敗時はフェイルセーフとしてスコア 0.0 を採用する箇所がある。
- セキュリティ:
  - news_collector では SSRF 防止のためスキーム・ホスト検査、リダイレクト検査、応答サイズ制限、defusedxml を利用。

---

## 開発 / テストのヒント

- 自動 .env 読み込みをテストで邪魔したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API 呼び出しや HTTP レイヤはモック可能な箇所（_call_openai_api、_urlopen 等）があり、ユニットテストで差し替えやすく設計されています。
- DuckDB はインメモリ（":memory:"）でのテスト利用が可能です（init_audit_db 等）。

---

この README はコード内の docstring と設計方針に基づいてまとめています。詳細な API 仕様や追加の運用手順（CI/CD、デプロイ、Slack 通知設定、kabuステーション接続の細部等）は別途ドキュメント（運用手順書、StrategyModel.md、DataPlatform.md など）を参照してください。