# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ。  
データ収集（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、監査ログ（約定トレーサビリティ）、研究用ファクター計算などの実装を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究プラットフォームのためのコンポーネント群です。主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー等）
- ETL パイプライン（日次差分取得・保存・品質チェック）
- RSS ニュース収集と OpenAI を用いた銘柄別ニュースセンチメント算出
- 市場レジーム（bull / neutral / bear）判定（ETF + マクロニュース）
- 監査用テーブル（signal / order_request / execution）の作成と初期化
- 研究用ファクター計算・特徴量解析ユーティリティ

パッケージ名: `kabusys`  
パッケージバージョンは `src/kabusys/__init__.py` で管理（例: 0.1.0）。

---

## 主な機能一覧

- data
  - J-Quants クライアント（取得・保存・ページネーション・トークン自動リフレッシュ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news, SSRF 対策・トラッキング除去）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 共通統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（銘柄ごとのニュースセンチメント → ai_scores, 関数: score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースの合成 → market_regime, 関数: score_regime）
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（将来リターン、IC、統計サマリー）

設計上のポイント:
- ルックアヘッドバイアスを避けるために内部で date.today() を直接参照しない実装方針
- DuckDB を主要なローカル DB として使用
- OpenAI 呼び出しはリトライ・バックオフを備えた実装

---

## 必要条件（概略）

- Python 3.10+（ソースで `X | Y` 型注釈を使用しているため）
- 必要な Python パッケージ（主要なもの）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで多くを賄います）

インストールはプロジェクトに依存しますが、開発環境であれば pip を使い以下のように導入してください:

```
pip install duckdb openai defusedxml
# または開発用 requirements ファイルがあればそれを使用
```

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（編集可能インストール推奨）

```
git clone <repo-url>
cd <repo>
pip install -e .
```

2. 環境変数 / .env の準備

プロジェクトルートに `.env` と `.env.local` を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに利用）。

主要な環境変数（例）:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API（発注等）
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- OpenAI / ニュース NLP
  - OPENAI_API_KEY (推奨)
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB / ファイルパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
- 監視 / プロセス制御
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1)
- 実行環境 / ログ
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
- リソース閾値（任意）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

.env の簡易例:

```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

3. DuckDB 初期化（監査DBを作る例）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます
```

---

## 使い方（代表的な例）

以下はライブラリをプログラムから利用する基本例です。詳細は各モジュールの docstring を参照してください。

- 共通準備（設定・DB 接続）

```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返す
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）

```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると today（ただし内部実装は trading_day に調整）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースセンチメント（指定日分）を算出して ai_scores に書き込む

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# date(YYYY, M, D) を指定
written = score_news(conn, date(2026, 3, 20))  # OpenAI API KEY は環境変数 OPENAI_API_KEY か api_key 引数で渡す
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 を基準に日次で判定）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, date(2026, 3, 20))  # OpenAI API KEY は環境変数で指定
```

- 監査用 DB の初期化（別 DB に分けたい場合）

```python
from kabusys.data.audit import init_audit_db
aud_conn = init_audit_db("data/monitoring_audit.duckdb")
# これで signal_events / order_requests / executions 等の監査テーブルが作成されます
```

- 市場カレンダーの更新バッチ（J-Quants から差分を取得）

```python
from kabusys.data.calendar_management import calendar_update_job
calendar_update_job(conn)  # lookahead_days は引数で調整可
```

- 研究：ファクター計算の利用例

```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

ログとエラー処理:
- 各関数は内部でロギングを行います。`LOG_LEVEL` を適切に設定してください。
- OpenAI / J-Quants API 呼び出しはリトライ・バックオフやフェイルセーフを備えており、API 失敗時はスコアを 0 にフォールバックしたり、該当処理をスキップして継続する設計です（例: news_nlp, regime_detector）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（1 で無効化）

注意: Settings は `kabusys.config.settings` から利用できます。必須変数が未設定の場合は `ValueError` が発生します。

---

## ディレクトリ構成

リポジトリ（src 配下）のおおまかな構成:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch / save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult 再エクスポート
    - calendar_management.py  — 市場カレンダー管理
    - news_collector.py       — RSS ニュース収集
    - quality.py              — データ品質チェック
    - stats.py                — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログ（テーブル定義 / 初期化）
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - monitoring/ (存在する場合の監視・実行モジュール群)
  - strategy/ (戦略関連モジュール)
  - execution/ (発注/ブローカー連携モジュール)

（実際のファイルは src 以下の各モジュールを参照してください）

---

## 開発・テスト時のヒント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）から行われます。テストの際に自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しやネットワーク依存部分は、モジュール内部で小さなラッパー関数にまとめられており、`unittest.mock.patch` による差替えが容易です（例: news_nlp._call_openai_api, regime_detector._call_openai_api, news_collector._urlopen）。
- DuckDB の `executemany` は空リストを受け付けない点に注意（モジュール側で対策済み）。

---

この README はライブラリの主要な使い方と構成をまとめたものです。各モジュールの docstring に実装詳細と注意点が書かれていますので、実際の利用・拡張時は該当ソースを参照してください。必要であればサンプルスクリプトや CLI ヘルパーの追加も対応できます。