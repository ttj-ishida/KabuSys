# KabuSys

KabuSys は日本株のデータパイプライン・研究・AI/NLP 解析・監査ログ・ETL を含む日本株自動売買支援ライブラリです。本リポジトリはデータ収集（J-Quants / RSS）、品質チェック、ファクター計算、ニュースセンチメント（OpenAI）評価、マーケットレジーム判定、監査テーブルの初期化などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

- J-Quants API を用いた株価・財務・カレンダーの取得と DuckDB への保存（差分ETL）
- RSS ベースのニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 / マクロ）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュース合成）
- ファクター（モメンタム / バリュー / ボラティリティ等）計算および研究ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / execution）テーブル初期化ユーティリティ
- 環境変数・.env の自動読み込み（プロジェクトルート検出）と設定管理

設計上の注意点:
- ルックアヘッドバイアス防止のため内部処理は直接 `datetime.today()` / `date.today()` を参照しない設計（多くの関数は `target_date` を明示的に受け取る）
- OpenAI / J-Quants への呼び出しはリトライやバックオフ等フェイルセーフを備える

---

## 機能一覧

- data
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save daily quotes, financials, market calendar, listed info）
  - calendar management（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
  - news_collector（RSS 取得・正規化・保存）
  - quality（データ品質チェック: 欠損・スパイク・重複・日付不整合）
  - stats（zscore_normalize 等）
  - audit（監査テーブルの初期化・専用 DB 作成）
- ai
  - news_nlp.score_news（銘柄ごとのニュースセンチメント評価、ai_scores に書込）
  - regime_detector.score_regime（ETF 1321 MA200 とマクロニュースを合成して market_regime に書込）
- research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理
  - kabusys.config.settings（.env / 環境変数読み込み、各種パス・フラグ・モード判定）

---

## セットアップ手順

1. Python 環境を用意（推奨: venv）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. パッケージをインストール（依存例）

   必要最低限の依存パッケージ（プロジェクトに合わせて調整してください）:
   - duckdb
   - openai
   - defusedxml

   例:

   ```
   pip install duckdb openai defusedxml
   ```

   （開発用に他のライブラリやテストツールを追加する場合は requirements.txt を用意してください）

3. リポジトリをインストール（開発中は editable 推奨）

   ```
   pip install -e .
   ```

4. 環境変数設定

   プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動で読み込まれます（プロジェクトルートの判定: 親階層に `.git` または `pyproject.toml` があるディレクトリ）。自動読み込みを無効化したい場合は環境変数を設定:

   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
   - OPENAI_API_KEY (AI 機能を使う場合必須) — OpenAI API キー
   - KABUSYS_ENV (optional) — development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL（optional）— DEBUG|INFO|WARNING|ERROR|CRITICAL
   - DUCKDB_PATH（optional）— DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（optional）— 監視用 SQLite（デフォルト data/monitoring.db）
   - PAPER_FILL_MODE（optional）— instant | partial | never | reject（paper_trading 用モック埋め合わせ）
   - PAPER_TRADING_SQLITE_PATH（optional）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用、任意）
   - PID_FILE_PATH / KILL_FLAG_PATH（実行監視用）

---

## 使い方 (簡易例)

以下は主要な操作の Python スニペット例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作って日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ってニュースセンチメントをスコアリングし ai_scores に書き込む

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にある前提。api_key を直接渡すことも可能。
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）を実行

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化する

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにレコードを挿入・参照できます
```

- J-Quants のトークンを取得（内部で settings.jquants_refresh_token を使う）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
print(token)
```

ログレベルは環境変数 `LOG_LEVEL` で制御してください。

---

## 実装上のポイント / 注意点

- OpenAI 呼び出しはリトライ・バックオフを持ち、API 失敗時はフェイルセーフ（多くのケースで 0.0 を返す、例外を上位に上げない）で継続する設計です。ただし API キーが未設定の場合は ValueError を送出します。
- J-Quants クライアントは内部でレートリミッタを持ち、401 受信時はリフレッシュ（get_id_token）して再試行します。
- DuckDB への保存は基本的に冪等化されており（ON CONFLICT DO UPDATE / DO NOTHING）、ETL を何度実行しても重複登録が起きにくくなっています。
- ニュース収集は SSRF 対策、トラッキングパラメータ除去、XML の安全パース（defusedxml）などのセキュリティ措置を講じています。
- サイズや API 呼び出しの都合上、ニュース NLP は銘柄ごとにトリム（文字数上限）やバッチ処理を行います。
- 多くの関数は look-ahead bias を避けるために `target_date` を引数に取ります。バックテスト等の用途で使用する際は必ず日付引数を明示してください。

---

## ディレクトリ構成

（主要ファイル / モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント解析（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save / auth）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等） & ETLResult
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - news_collector.py     — RSS 収集・前処理
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログテーブルの DDL / 初期化
    - etl.py                — ETL 公開インターフェース（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン、IC、統計サマリー等
  - ai, data, research などのサブパッケージが主要機能を提供

---

## よく使う環境変数（まとめ）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY（AI 機能を使う場合）

- 推奨/任意:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL (INFO デフォルト)
  - PAPER_FILL_MODE (paper_trading 用: instant/partial/never/reject)
  - PAPER_TRADING_SQLITE_PATH
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env 読込を無効化）

---

必要に応じて README を拡張して、インストール要件（requirements.txt）, 実行例（cron / systemd）、CI / テスト方法、データスキーマ定義（DDL）などを追加してください。追加で README に含めたい内容（例: 実行スクリプト、サンプル .env.example）を教えていただければ反映します。