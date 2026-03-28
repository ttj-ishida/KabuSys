# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をバックエンドに、J-Quants からのデータ取得・ETL、ニュースの収集と LLM によるセンチメント評価、ファクター計算、監査ログなどを一貫して提供します。

主な設計方針は以下の通りです：
- ルックアヘッドバイアス防止（内部で date.today() を不用意に参照しない等）
- 冪等性（DB 書き込みは ON CONFLICT / DELETE→INSERT 等で安全に）
- フェイルセーフ（外部 API 失敗時は部分的にスキップして継続）
- DuckDB を用いたローカルかつ高速なデータ処理

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ラッパー（`kabusys.config.settings`）
- データ収集 / ETL（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、JPX カレンダー取得（ページネーション・レートリミット対応）
  - DuckDB へ冪等保存（ON CONFLICT）
  - 日次 ETL パイプライン（`run_daily_etl`）
- データ品質チェック（`data.quality`）
  - 欠損、重複、スパイク、日付不整合などの検出（`QualityIssue`）
- ニュース収集（RSS）と前処理（`data.news_collector`）
  - URL 正規化・SSRF 対策・受信サイズ上限・Defused XML 利用
  - raw_news / news_symbols への冪等保存（設計により保存側実装と連携）
- ニュース NLP（OpenAI を利用）
  - 銘柄ごとのニュースセンチメント評価（`ai.news_nlp.score_news`）
  - マクロニュースを用いた市場レジーム判定（`ai.regime_detector.score_regime`）
  - API 呼び出しはリトライ・バックオフを実装、JSON mode を想定
- リサーチ / ファクター計算（`research`）
  - Momentum / Value / Volatility 等のファクター計算（DuckDB SQL ベース）
  - 将来リターン、IC（Spearman）、統計サマリー、Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル生成・初期化（`data.audit.init_audit_db`）
  - UUID ベースのトレーサビリティを想定

---

## 要件

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の依存は setup.py/pyproject.toml に記載する想定）

例（最低限のインストール）:
```bash
pip install duckdb openai defusedxml
```

プロジェクトを editable インストールする場合:
```bash
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 環境を作成（推奨: venv / pyenv）
3. 依存パッケージをインストール
4. 環境変数を設定（下記参照）
5. DuckDB データベース等のディレクトリを作成（設定に応じて自動作成されることがあります）

### 環境変数（.env の例）

config モジュールはプロジェクトルート（.git または pyproject.toml を起点）を探索し、自動で `.env` / `.env.local` を読み込みます。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

`.env.example` 相当の例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション（必要な場合）
KABU_API_PASSWORD=your_kabu_pwd
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# ローカル DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注:
- `.env.local` は `.env` をオーバーライドします（ローカル専用）。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます（テスト等で使用）。
- `kabusys.config.settings` を通じて各値にアクセスできます（必須値は未設定時に ValueError になります）。

---

## 使い方（主要 API の例）

以下は簡単な利用例です。実運用ではログ設定や例外ハンドリング、監査処理等を追加してください。

- DuckDB 接続を作成し ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（銘柄別センチメント）を生成:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 19))
print(f"scored {count} codes")
```

- 市場レジームを判定して保存:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 19))
```

- 監査用 DB を初期化:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの duckdb 接続
```

- ファクター計算（例: Momentum）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 19))
# records: list of dict (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)
```

- 設定値にアクセス:
```python
from kabusys.config import settings

print(settings.duckdb_path)        # Path オブジェクト
print(settings.is_live)           # bool
print(settings.jquants_refresh_token)  # raises ValueError if missing
```

注意点:
- OpenAI API 呼び出しには `OPENAI_API_KEY` が必要です（関数引数で明示的に渡すことも可能）。
- テスト時には内部の API 呼び出し関数（例: news_nlp._call_openai_api や regime_detector._call_openai_api）を mock して差し替えられる設計です。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py             — ニュースの LLM スコアリング（score_news）
  - regime_detector.py      — マクロ+MA200 を用いた市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py  — 市場カレンダー管理（is_trading_day, next_trading_day, ...）
  - etl.py                  — ETL 結果の公開型（ETLResult）
  - pipeline.py             — ETL パイプライン（run_daily_etl, run_prices_etl, ...）
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - quality.py              — データ品質チェック（check_missing_data 等）
  - audit.py                — 監査テーブル DDL / 初期化（init_audit_schema, init_audit_db）
  - jquants_client.py       — J-Quants API クライアント + 保存関数
  - news_collector.py       — RSS ニュース収集と前処理
  - pipeline.py             — ETL パイプライン（ETLResult 等）
- research/
  - __init__.py
  - factor_research.py      — ファクター計算（momentum, value, volatility）
  - feature_exploration.py  — 将来リターン、IC、統計サマリー等
- research/*                 — リサーチ向けユーティリティ
- その他（strategy / execution / monitoring 等の名前が __all__ にある想定）

README はこのプロジェクトの高レベル概要を示したものです。各モジュールの詳細はソースコード内の docstring を参照してください。

---

## 開発 / テストに関するメモ

- モジュールは外部 API 呼び出し部分に明確な抽象化（関数）を持っており、unit test でのモック差替えが容易です（例: news_nlp._call_openai_api を patch）。
- DuckDB は軽量でテスト向き（`:memory:` を使ったインメモリ DB 初期化も可能）。
- `.env` の自動読み込みはプロジェクトルート検出に依存します。CI やテスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い、必要な環境を明示的に用意してください。

---

必要であれば README に具体的なスクリプト例（cron / Airflow / systemd 用の起動例）、CI 設定例、開発フローや contribution ガイドを追加します。どの情報を追記したいか教えてください。