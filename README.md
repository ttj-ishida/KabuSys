# KabuSys

日本株向けの自動売買・データプラットフォーム（ライブラリ）。  
ETL、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログなど、投資システムで必要となる基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は DuckDB をデータレイヤーに用い、J-Quants / RSS / OpenAI 等を組み合わせて以下を実現します。

- J-Quants からの差分 ETL（株価、財務、マーケットカレンダー）
- RSS を使ったニュース収集・前処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別・マクロ）
- ETF（1321）とマクロセンチメントを合成した市場レジーム判定（bull/neutral/bear）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定までを追跡可能にする監査ログスキーマ

設計上の特徴:
- ルックアヘッドバイアスを避けるため、日付処理は明示的に target_date を受け取る（date.today() を直接参照しない箇所が多い）
- 外部 API 呼び出しに対するリトライ/バックオフ、フェイルセーフなフォールバック
- DuckDB へは冪等（ON CONFLICT DO UPDATE / DO NOTHING）で保存

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン自動リフレッシュ、レートリミット）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - カレンダー管理（営業日判定・next/prev_trading_day）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news — 銘柄別センチメント）
  - レジーム判定（score_regime — ETF MA とマクロセンチメントの合成）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - .env の自動ロード（プロジェクトルート検出）と必須環境変数管理

---

## 必要条件（環境）

- Python 3.10+
- 依存パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外のものは setup.py / pyproject.toml に合わせてインストールしてください）

---

## インストール

リポジトリをクローンし、開発環境へインストール（例）:

```
git clone <repo-url>
cd <repo-root>
pip install -e .
# または requirements.txt / pyproject.toml に従って pip install -r requirements.txt
```

---

## 設定（環境変数）

KabuSys はプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（最低限必要なもの）:

- JQUANTS_REFRESH_TOKEN ・・・ J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      ・・・ kabuステーション API 用パスワード
- SLACK_BOT_TOKEN        ・・・ Slack 通知用トークン
- SLACK_CHANNEL_ID       ・・・ Slack チャンネル ID
- OPENAI_API_KEY         ・・・ OpenAI API キー（score_news / score_regime に使用）
- DUCKDB_PATH            ・・・ DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            ・・・ 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            ・・・ environment: development / paper_trading / live
- LOG_LEVEL              ・・・ ログレベル（DEBUG/INFO/…）

例 `.env`:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（DB 初期化など）

1. 環境変数を設定（上の .env をプロジェクトルートに作成）
2. DuckDB のスキーマをプロジェクトで管理する場合、スキーマ初期化処理を用意している想定ですが、監査ログ専用 DB を初期化する例:

```python
from pathlib import Path
import kabusys.data.audit as audit

db_path = Path("data/audit.duckdb")
conn = audit.init_audit_db(db_path)  # テーブル作成済みの接続を返す
```

3. ETL を実行する前に DuckDB 接続（データベース）を用意してください。ETL 系は `kabusys.data.pipeline.run_daily_etl` を使用します。

---

## 使い方（主要な呼び出し例）

以下は最小構成のスニペット例です。実運用では適切なログ設定・例外処理・スケジューラを組み合わせてください。

- DuckDB 接続を作成し、日次 ETL を実行する例:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む（OpenAI API キーを渡せる）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
print("書き込み銘柄数:", n_written)
```

- マーケットレジームを評価して market_regime テーブルへ書き込む:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
```

- 監査 DB を初期化する:

```python
from pathlib import Path
import kabusys.data.audit as audit

conn = audit.init_audit_db(Path("data/audit.duckdb"))
# 以後 conn を使って監査ログに書き込める
```

- カレンダー関連ユーティリティの例:

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import next_trading_day, get_trading_days

conn = duckdb.connect("data/kabusys.duckdb")
nd = next_trading_day(conn, date(2026,3,19))
days = get_trading_days(conn, date(2026,3,1), date(2026,3,31))
```

注意:
- OpenAI 呼び出しはネットワーク依存かつコストが発生します。テスト時は関数内の _call_openai_api をモック可能です（ユニットテスト向けに patch しやすい設計）。
- API キーは引数で注入可能（テスト時の差し替えが容易）。

---

## ロギング / 実行環境

- 設定: KABUSYS_ENV（development / paper_trading / live）により挙動を分けられます。log レベルは LOG_LEVEL 環境変数で制御。
- システムは失敗時にできるだけフェイルセーフに動作する設計です（API 失敗時はスコアを 0 にする等）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要ファイルと役割（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数/.env 管理
  - ai/
    - __init__.py
    - news_nlp.py               — ニュースセンチメント（銘柄別）
    - regime_detector.py        — 市場レジーム判定（1321 MA + マクロ）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（fetch/save）
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - etl.py                    — ETLResult エクスポート
    - calendar_management.py    — マーケットカレンダー管理（営業日判定等）
    - news_collector.py         — RSS 収集と前処理
    - quality.py                — データ品質チェック
    - stats.py                  — zscore_normalize 等統計ユーティリティ
    - audit.py                  — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py        — ファクター計算（momentum/value/volatility）
    - feature_exploration.py    — forward returns / IC / summary / rank
  - ai/、data/、research/ はそれぞれ公開 API を __all__ で整理

---

## テストとモック

- OpenAI / HTTP 呼び出し部分は外部依存のためユニットテストではモックすることを推奨します。各モジュールは内部で _call_openai_api / _urlopen 等を定義しており、テストで差し替えしやすい作りになっています。
- ETL・保存関数は DuckDB 接続を受け取るため、":memory:" 接続やテスト用の一時ファイルを使ったテストが可能です。

---

## 貢献・ライセンス

- 開発・バグ報告・機能提案は Issue / PR で受け付けてください。README の追記やテストの追加も歓迎します。
- ライセンスはリポジトリのルートにある LICENSE を参照してください（ここには含まれていません）。

---

以上が KabuSys の概要と基本的な使い方です。必要であれば、README に実行例（cron / systemd / Docker での実行方法）、スキーマ定義（DuckDB DDL）の詳細、CI / テスト手順を追記できます。どの項目を優先して詳述しますか？