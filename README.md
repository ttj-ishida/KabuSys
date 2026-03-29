# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。ETL（J-Quants からのデータ取得）、ニュース収集／NLP スコアリング、マーケットカレンダー管理、ファクター計算、監査ログ（発注追跡）など、トレード／リサーチに必要な機能群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の用途を想定した Python パッケージです。

- J-Quants API からの株価/財務/カレンダー取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF・XML 攻撃対策済み）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄単位）およびマクロセンチメント評価
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注 → 約定まで追跡できる監査ログスキーマ（DuckDB 初期化ユーティリティ）

設計方針として、Look-ahead バイアス回避、冪等性、外部 API に対する堅牢なリトライ・レート制御、安全性（SSRF、XML、巨大レスポンス対策）を重視しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン自動リフレッシュ、レート制御）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS 取得、前処理、安全対策）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュースセンチメント（score_news） — 銘柄ごとのスコアを ai_scores テーブルへ書き込み
  - 市場レジーム判定（score_regime） — ETF 1321 の MA200 とマクロセンチメントを合成
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み / 設定管理（.env 自動読み込み、必須変数チェック）

---

## 動作環境・依存

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他：標準ライブラリのみで多くを実装しているため追加は最小限）
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

pip でのインストール例:
```bash
python -m pip install duckdb openai defusedxml
# 開発時はパッケージルートで
python -m pip install -e .
```

（requirements.txt がない場合、使用する機能に応じて上記パッケージを追加してください）

---

## 環境変数（.env）

パッケージはプロジェクトルート（.git または pyproject.toml が存在する場所）にある `.env` / `.env.local` を自動で読み込みます（環境変数が優先、`.env.local` は上書き）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に使用される環境変数（最低限設定すべきもの）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb openai defusedxml
   # または開発モードでインストール
   python -m pip install -e .
   ```

4. `.env` を作成して必要な環境変数を設定（上記参照）。

5. DuckDB のデータディレクトリを作る（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（よく使う機能の例）

以下は Python REPL / スクリプト内での呼び出し例です。事前に `.env` を用意し、依存をインストールしてください。

- DuckDB 接続と ETL 実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）をスコアリングして ai_scores に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # requires OPENAI_API_KEY
print(f"wrote {written} scores")
```

- 市場レジーム判定（MA200 + マクロセンチメント）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # requires OPENAI_API_KEY
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # Schema を作成して接続を返す
```

- RSS を取得して記事を確認（ニュース収集の低レベルユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

- J-Quants から生データ取得（トークン取得含む）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()  # JQUANTS_REFRESH_TOKEN が必要
quotes = fetch_daily_quotes(date_from=None, date_to=None, id_token=token)
```

注意点:
- AI 関連機能は OpenAI の API キー（OPENAI_API_KEY）を必要とします。関数引数で api_key を渡すことも可能です。
- ETL / スコアリング関数はいずれも「ルックアヘッドバイアスを避ける」ために内部で date.today() を不用意に参照しない設計です。target_date を明示的に与えることを推奨します。
- .env の自動読み込みはプロジェクトルート検出に依存します。テスト等で自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数 / .env 自動ロード / settings
- ai/
  - __init__.py
  - news_nlp.py        — 銘柄別ニュースセンチメント（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（fetch/save）
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETLResult 再エクスポート
  - news_collector.py     — RSS 収集・前処理
  - calendar_management.py— マーケットカレンダー管理
  - quality.py            — データ品質チェック
  - stats.py              — 統計ユーティリティ（zscore_normalize）
  - audit.py              — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py    — ファクター計算（momentum/value/volatility）
  - feature_exploration.py— 将来リターン/IC/統計サマリー
- research/*, ai/*, data/* の内部に多数の補助関数・安全対策・設計注釈あり

---

## 開発／テスト時のヒント

- .env 自動読み込みの動作:
  - 読み込み順: OS 環境 > .env.local > .env
  - テストで環境を分離したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI API 呼び出しは内部でリトライ・バックオフ処理を行います。ユニットテストでは該当箇所をモックする設計になっています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB に対する executemany 空リストは一部バージョンでエラーとなるため、実装側は空チェックを行っています。開発時は DuckDB のバージョン互換性に注意してください。

---

## ライセンス・貢献

（ここにプロジェクトのライセンス情報や貢献方法を追記してください）

---

README は以上です。必要であれば、README に含めるより詳しい使い方（コマンドラインツール、CI の設定、サンプル .env.example、SQL スキーマ定義の抜粋など）を追加できます。どの部分を拡張しますか？