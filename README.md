# KabuSys

日本株向け自動売買・データプラットフォーム（ライブラリ）  
このリポジトリは「KabuSys」プロジェクトのコアライブラリです。J-Quants や RSS、OpenAI 等を用いて市場データ／ニュースを収集・品質検査・AIでスコアリングし、研究/戦略/発注レイヤへデータを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 指向、datetime.today() を直接参照しない）
- ETL／保存は冪等（ON CONFLICT）で実装
- 外部 API 呼び出しはリトライ・バックオフ・レート制御を備える
- DuckDB をデータ格納に利用

---

## 主な機能（概要）
- データ取得・ETL
  - J-Quants API から株価日足・財務データ・JPX カレンダーの差分取得・保存（rate limit / retry 対応）
  - ETL パイプライン：run_daily_etl による日次 ETL（カレンダー→株価→財務→品質チェック）
- データ品質管理
  - 欠損・重複・スパイク・日付不整合チェック（quality モジュール）
- ニュース収集・NLP（AI）
  - RSS 取得・正規化・SSRF 防御・前処理（news_collector）
  - OpenAI を用いたニュースセンチメント算出（news_nlp）
  - マクロニュース＋ETF MA を合成した市場レジーム判定（regime_detector）
- 研究用ユーティリティ
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
  - Z スコア正規化ユーティリティ
- 監査（audit）
  - シグナル→発注→約定 のトレーサビリティテーブル定義と初期化ユーティリティ
- 設定管理
  - .env / 環境変数の自動読み込み（config.Settings）

---

## 必要条件（推奨）
- Python 3.10+
- DuckDB
- OpenAI Python SDK
- defusedxml
- その他：標準ライブラリ（urllib, json 等）

インストール例（プロジェクトに requirements.txt がある想定）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 直接最低限の依存だけ入れるなら:
pip install duckdb openai defusedxml
```

---

## 環境変数 / 設定
設定は環境変数またはリポジトリルートの `.env` / `.env.local` で読み込まれます（kabusys.config により自動ロード。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須（Settings で _require() が使われるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード（利用する場合）
- SLACK_BOT_TOKEN — Slack 通知に使用する場合
- SLACK_CHANNEL_ID — Slack 通知に使用する場合

任意 / デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効にするフラグ
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUS_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

簡単な `.env` 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順 (概要)
1. リポジトリをクローン
2. Python 仮想環境の作成・依存インストール
3. `.env` を作成して必要な環境変数を設定
4. DuckDB 用ディレクトリを作成（必要なら）
5. 監査ログ用 DB を初期化（必要に応じて）

例:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data
# .env を作成する（上の例参照）
```

監査ログ DB の初期化例（Python）:
```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db
import duckdb

# settings.duckdb_path は Path オブジェクト
conn = init_audit_db(settings.duckdb_path)
# これで監査用テーブル群が作成されます
```

注意: プロダクションで利用する場合は data/schema 初期化（全テーブル定義）等が必要です。本リポジトリのドキュメント（DataPlatform.md 相当）を参照してスキーマを作成してください。

---

## 使い方（主要 API の例）

共通: DuckDB 接続作成例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを算出して ai_scores テーブルへ書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None なら env の OPENAI_API_KEY を使用
print(f"written: {n_written}")
```

3) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

4) ファクター計算・研究用関数
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize
from datetime import date

fa = calc_momentum(conn, date(2026,3,20))
fb = calc_value(conn, date(2026,3,20))
fc = calc_volatility(conn, date(2026,3,20))
# Z スコア正規化
normed = zscore_normalize(fa, ["mom_1m", "mom_3m", "mom_6m"])
```

5) RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
# raw_news テーブルへの保存はプロジェクト側で DB INSERT を行ってください
```

注意点:
- OpenAI 呼び出しは課金対象・レート制限あり。API キーの管理と使用量に注意してください。
- J-Quants API もレート制限があり、本クライアントは固定間隔スロットリングを実装しています。

---

## ディレクトリ構成（主なファイル）
以下は src/kabusys 配下の主要ファイル一覧（本リポジトリのスニペットに基づく）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py               — ニュースの AI スコアリング
    - regime_detector.py        — 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py    — マーケットカレンダー管理
    - etl.py                    — ETL インターフェース
    - pipeline.py               — ETL 実装（日次 ETL 等）
    - stats.py                  — 統計ユーティリティ（zscore_normalize 等）
    - quality.py                — データ品質チェック
    - audit.py                  — 監査ログテーブル定義・初期化
    - jquants_client.py         — J-Quants API クライアント + 保存ロジック
    - news_collector.py         — RSS ニュース取得・正規化
    - (その他ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py        — Momentum / Value / Volatility 計算
    - feature_exploration.py    — 将来リターン・IC・統計サマリ

---

## 運用上の注意
- ルックアヘッドバイアス対策が各所に組み込まれています。バックテスト等で利用する場合は target_date の取扱いを誤らないでください。
- 外部 API（OpenAI / J-Quants / RSS）呼び出しはネットワークや料金の観点から慎重に扱ってください。テストでは該当関数をモックすることが推奨されます（コード内にモック想定コメントあり）。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）は ETL 側や別スクリプトで定義/作成する必要があります。監査テーブルに関しては data.audit.init_audit_db が初期化ユーティリティを提供します。

---

## 開発・貢献
- テストは API 呼び出しをモックして実行してください（OpenAI / J-Quants / ネットワーク依存箇所の差し替えが想定されています）。
- 新しい ETL ジョブやテーブルを追加する場合は、既存の冪等性・品質チェック・トレーサビリティ方針に従ってください。

---

必要があれば、README にサンプル .env.example や DuckDB スキーマ作成 SQL、CI 設定、より詳細な運用手順（運用ジョブの cron / Airflow 例）を追加できます。どの補足を希望しますか？