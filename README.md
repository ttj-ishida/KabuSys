# KabuSys

日本株向けの自動売買・データ基盤ライブラリ (KabuSys)

このリポジトリは、J-Quants API や RSS / OpenAI を組み合わせて日本株のデータパイプライン、特徴量計算、ニュース NLP、マーケットレジーム推定、監査ログ（発注トレーサビリティ）などを提供する内部ライブラリ群です。バックテスト用データ作成や、実運用の前段処理（ETL / 品質チェック / シグナル → 発注監査）に重点を置いて設計されています。

---

## 主な機能（機能一覧）

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出） / KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能
  - 必須環境変数の取得ラッパー（settings）

- データ取得／ETL（kabusys.data）
  - J-Quants API クライアント（ページネーション / レート制御 / トークン自動リフレッシュ）
  - 日足（raw_prices）・財務（raw_financials）・上場銘柄情報・市場カレンダー取得
  - 差分 ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - マーケットカレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF対策・URL正規化・前処理）
  - 監査ログ（signal_events / order_requests / executions）テーブル作成ユーティリティ

- AI（kabusys.ai）
  - ニュース NLP（銘柄単位のセンチメントスコア付与: score_news）
  - マクロニュースと ETF の MA200 に基づく市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を JSON Mode で利用するためのリトライ・フォールバック実装を含む

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC 計算、統計サマリー、Z スコア正規化ユーティリティ

- 汎用ユーティリティ
  - 統計ユーティリティ（zscore_normalize 等）
  - DuckDB を前提にした SQL/ETL の設計

---

## 前提条件

- Python 3.10+
- 推奨パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS, OpenAI）

requirements.txt が用意されている場合はそれを使用してください。ない場合は手動でインストールします：

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクトの pyproject/requirements がある場合はそちらを優先してください）

---

## 環境変数（主要な設定）

このライブラリは環境変数または .env（プロジェクトルート）から設定をロードします。自動ロードは .git または pyproject.toml を基準に行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須は README 内で明示）：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注系）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- KABUSYS_ENV — 環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=yourpassword
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を用意します

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
```

2. 必要パッケージをインストール

```bash
pip install duckdb openai defusedxml
# またはプロジェクトの requirements.txt / pyproject.toml を利用
```

3. 環境変数を設定（.env をプロジェクトルートに作成）

4. データディレクトリを作成（必要に応じて）

```bash
mkdir -p data
```

5. DuckDB 初期スキーマ（監査ログ等）を作る（任意）

Python REPL 等で:

```python
import duckdb
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使用してさらにスキーマ追加や確認を行えます
```

---

## 使い方（代表的な API とコード例）

以下はライブラリの主要機能の使用例です。実行は Python スクリプトやバッチから行います。

- 設定アクセス

```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

- DuckDB 接続をオープンして日次 ETL を実行

```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース NLP スコア生成（score_news）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- マーケットカレンダー関連

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- 監査データベース初期化（監査ログ専用 DB を作る）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

- J-Quants から日足データを直接取得（低レベル API）

```python
from kabusys.data.jquants_client import fetch_daily_quotes
from datetime import date
recs = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```

注意:
- OpenAI 呼び出しはネットワーク/課金を伴います。テスト時は各モジュールの _call_openai_api を unittest.mock.patch で差し替え、API 呼び出しをモックしてください（news_nlp と regime_detector はそれぞれの _call_openai_api をテストフックとして用意しています）。
- self-contained な CLI は提供していません。上記のように Python から直接呼び出す想定です。

---

## テスト／開発上の注意

- 自動で .env をロードする動作は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化できます（テストのために利用）。
- OpenAI 呼び出しは各モジュール内でリトライ・フォールバック処理を行います。API エラー時は安全にフォールバック（0.0 等）するロジックが多数組み込まれています。
- DuckDB の executemany に関する互換性（空リストの制約など）に配慮した実装になっています。
- RSS 取得は SSRF 対策・gzip サイズチェック・XML パース安全化（defusedxml）を実装しています。

---

## ディレクトリ構成

主要なファイル/モジュールを抜粋しています（省略あり）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（score_news）
    - regime_detector.py       — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch / save）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult 再エクスポート
    - calendar_management.py   — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py        — RSS ニュース収集
    - quality.py               — データ品質チェック
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査ログテーブルの初期化 / DB 作成
  - research/
    - __init__.py
    - factor_research.py       — Momentum/Value/Volatility の計算
    - feature_exploration.py   — 将来リターン / IC / summary / rank

---

## 付記 / 設計上のポイント

- Look-ahead バイアス対策: 各モジュールは datetime.today()/date.today() を内部で直接参照しない等の配慮があり、ETL/スコアリングは明示的な target_date を受け取る設計です。
- 冪等性: ETL の保存処理は多くが ON CONFLICT DO UPDATE（または INSERT … ON CONFLICT）により冪等に実装されています。
- フォールバック: 外部 API（OpenAI / J-Quants / RSS）での失敗時に、処理を全面停止させず安全なデフォルトで継続する設計がなされています（ただし、重要なトークンは必須）。

---

この README はコードベースに基づく概要と利用例を示しています。追加で CLI、サンプル .env.example、テーブル DDL（raw_prices などのスキーマ）、あるいはデプロイ手順が必要であれば教えてください。