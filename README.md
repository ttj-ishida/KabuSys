# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュースの NLP によるセンチメント評価、研究用ファクター計算、監査ログ（トレーサビリティ）、及び取引戦略の判定補助などを含みます。

## 特徴（概要）
- J-Quants API からの差分取得・保存（ページネーション、リトライ、レートリミット対応）
- DuckDB ベースの ETL パイプライン（差分更新、バックフィル、品質チェック）
- ニュース収集（RSS）と LLM（OpenAI）を用いた銘柄別センチメントスコアリング
- マーケットレジーム判定（ETF MA200 と マクロニュースセンチメントの組合せ）
- 監査ログスキーマ（シグナル -> 注文 -> 約定 のトレース可能なテーブル群）
- 研究用ユーティリティ（モメンタム／バリュー／ボラティリティ等のファクター計算、IC や統計要約）
- 自動的な .env ロード機能（プロジェクトルートにある .env / .env.local を読み込み）

## 主な機能一覧
- data.jquants_client: J-Quants API クライアント（取得・保存関数）
- data.pipeline: 日次 ETL パイプライン（run_daily_etl 等）
- data.news_collector: RSS 取得と raw_news への保存補助
- data.quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
- data.calendar_management: 市場カレンダー判定・更新ジョブ
- data.audit: 監査ログテーブルの初期化 / audit DB ユーティリティ
- ai.news_nlp: ニュースから銘柄ごとの ai_score を生成（OpenAI）
- ai.regime_detector: マーケットレジーム（bull/neutral/bear）判定
- research.*: ファクター計算・特徴量解析ツール
- config: 環境変数・設定管理（.env 自動読み込み、必須チェック）

---

## 要件
- Python 3.10+
- 必要なパッケージ（一例）:
  - duckdb
  - openai
  - defusedxml
  - （その他プロジェクトで使用するパッケージを requirements.txt にまとめてください）

---

## インストール（開発環境での例）
リポジトリのルートで：
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"   # setup.cfg/pyproject に extras がある場合
# あるいは最低限:
pip install duckdb openai defusedxml
pip install -e .
```

---

## 環境設定（.env）
パッケージはデフォルトでプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD に依存せず __file__ を基準にプロジェクトルートを探索）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（実行系で必要）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必要に応じて）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で使用）
推奨 / オプション:
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例 (`.env.example`):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ（DB 初期化の簡易手順）
- DuckDB ファイルを指定して接続します。監査ログ用 DB 初期化ユーティリティが含まれています。

例: 監査 DB 初期化
```python
import duckdb
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# ファイル DB の初期化
conn = init_audit_db(settings.duckdb_path)  # または別 DB パス
# -> テーブルとインデックスが作成されます
```

注意: 本リポジトリには（示したコードの中で）監査スキーマ初期化関数が含まれますが、raw_prices / raw_financials / market_calendar 等のコアテーブルの DDL スクリプトは別途用意して適用する必要があります。通常は初期スキーマ作成スクリプト（migration）を実行してください。

---

## 使い方（主要 API・実行例）

基本的に DuckDB 接続を渡して各種関数を呼び出します。

- DuckDB 接続例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア生成（ai.news_nlp.score_news）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数にあるか、api_key を明示して渡す
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

- マーケットレジーム判定（ai.regime_detector.score_regime）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- RSS フィード取得（news_collector.fetch_rss の単体利用）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用ユーティリティ（例: モメンタム計算）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

mom = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
mom_z = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m","ma200_dev"])
```

- データ品質チェック:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

- 市場カレンダー / 営業日判定:
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

重要:
- OpenAI を使う関数は api_key 引数を受け取ります。None の場合は環境変数 OPENAI_API_KEY を参照します。
- ETL / 保存関数は既存データ上書き（冪等）を想定していますが、対象テーブルが存在することが前提です（スキーマ初期化を行ってください）。

---

## ディレクトリ構成（主要ファイル）
以下は本コードベースで提供されている主要モジュールと役割（抜粋）です。

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / .env 自動読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM による銘柄センチメントスコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（ETF MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集（fetch_rss 等）
    - quality.py — データ品質チェック
    - calendar_management.py — マーケットカレンダー管理 / 営業日ロジック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログ（signal / order_request / executions）スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー 等

---

## 注意点 / 運用上のヒント
- Look-ahead バイアス防止に配慮した設計（target_date を明示し、datetime.today() を内部で参照しない実装方針）です。バックテスト等では target_date を明示的に指定してください。
- OpenAI 呼び出しはリトライ/フォールバック（失敗時は中立スコア等）を実装していますが、APIコストやレート制限に注意してください。
- jquants_client は 120 req/min の制限に合わせた RateLimiter を実装しています。大量取得時は想定通り遅延が入ります。
- raw テーブル（raw_prices / raw_financials / raw_news / market_calendar / ai_scores 等）の DDL（スキーマ）は運用用スクリプトで事前に作成してください。監査スキーマについては data.audit.init_audit_db / init_audit_schema が利用可能です。

---

## 貢献・問い合わせ
バグ報告、機能提案は Issue を立ててください。開発方針や API 仕様に関する質問は README を更新していきます。

---

以上が README.md の概要です。必要であれば、具体的な schema SQL、requirements.txt、及び運用スクリプト（systemd タイマーや cron、ワーカー実行例）を追加で作成します。どの情報を優先して追記しますか？