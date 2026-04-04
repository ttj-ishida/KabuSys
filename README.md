# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログの初期化など、バックテスト・運用で必要な主要機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）/ 設定
- 使い方（サンプル）
- ディレクトリ構成（主要ファイル解説）
- 補足 / 注意点

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・カレンダーの差分 ETL（DuckDB 保存）
- ニュースの収集・前処理（RSS）および OpenAI を用いた銘柄別センチメント（ai_scores）生成
- ETF（1321）ベースの移動平均などを使った市場レジーム判定（LLM 結果と合成）
- 研究用（ファクター計算、将来リターン、IC・統計サマリー）
- 監査ログ用スキーマ（シグナル→注文→約定の追跡用テーブル）初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計方針として、バックテストでのルックアヘッドバイアス防止、外部 API 呼び出しの堅牢なリトライ・レート制御、DuckDB による冪等保存などを重視しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン自動更新、RateLimiter）
  - market_calendar 管理（営業日判定、next/prev/get_trading_days）
  - news_collector（RSS 収集・前処理、SSRF 対策、記事ID生成）
  - quality（品質チェック：欠損・スパイク・重複・日付整合性）
  - audit（監査ログスキーマ初期化 / init_audit_db）
  - stats（zscore 正規化等ユーティリティ）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントスコアを生成して ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離 + マクロニュース（LLM）を合成して market_regime に書き込む
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等の定量ファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー、ランク変換等
- config
  - 環境変数の自動読み込み（.env / .env.local）、Settings オブジェクト（settings）で集中管理

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（typing の一部に | 型注釈等を使用）
- DuckDB（Python パッケージ）を使用
- OpenAI Python SDK を使用（ニュース/レジーム判定で必須）
- defusedxml（RSS パースの安全性向上）

例: 仮想環境を作り、依存パッケージをインストールする

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# 必要なパッケージの一例
pip install duckdb openai defusedxml
# 開発環境の場合はプロジェクト直下で
pip install -e .
```

※ パッケージ化されている場合は pip install でインストールしてください。requirements.txt / pyproject.toml に依存が定義されている想定です。

---

## 環境変数（.env） / 設定

config.Settings で環境変数を集約しています。パッケージは起点ファイルからプロジェクトルート (.git または pyproject.toml) を探索し、自動で `.env` と `.env.local` を読み込みます（自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。ETL 実行時に必要。
- KABU_API_PASSWORD (必須)
  - kabuステーション API を使う場合のパスワード。
- OPENAI_API_KEY
  - OpenAI を用いる機能（score_news / score_regime）で使用。関数呼び出し時に api_key を直接渡すことも可能。
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - 通知用途（任意）
- DUCKDB_PATH (省略時: data/kabusys.duckdb)
- SQLITE_PATH (省略時: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - 実行監視用オプション
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - 監視の閾値
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

例 (.env):

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（サンプル）

以下は代表的な利用例です。各モジュールは DuckDB の接続オブジェクトを受け取る設計です。

1) DuckDB 接続を作る / 監査 DB を初期化する

```python
import duckdb
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# ファイル DB を直接使う場合
conn = duckdb.connect(str(settings.duckdb_path))

# 監査ログ専用 DB を初期化（ファイルが無ければ親ディレクトリを作成）
audit_conn = init_audit_db(settings.duckdb_path)  # 例: ":memory:" も可
```

2) 日次 ETL の実行（J-Quants トークンは settings.jquants_refresh_token を使用）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())

print(result.to_dict())
```

3) ニュースセンチメントスコアを作成して ai_scores テーブルへ書く

```python
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数にある前提。api_key 引数で明示することも可能。
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

4) 市場レジーム判定（ma200 と LLM を合成）

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
# OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定
score_regime(conn, target_date=date(2026, 3, 20))
```

5) ファクター計算 / 研究用ユーティリティ

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
import duckdb

conn = duckdb.connect('data/kabusys.duckdb')
mom = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
```

6) 品質チェックを実行する

```python
from kabusys.data.quality import run_all_checks
from datetime import date
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## ディレクトリ構成（主要ファイルの概略）

- src/kabusys/__init__.py
  - パッケージ初期化、バージョン定義

- src/kabusys/config.py
  - 環境変数読み込み、Settings（settings）を提供
  - 自動 .env ロード（.env / .env.local）

- src/kabusys/ai/
  - news_nlp.py : ニュースセンチメント（score_news）
  - regime_detector.py : 市場レジーム判定（score_regime）
  - __init__.py

- src/kabusys/data/
  - pipeline.py : ETL のメインロジック（run_daily_etl 等）
  - jquants_client.py : J-Quants API 呼び出し・保存ロジック（fetch/save）
  - news_collector.py : RSS 取得・前処理
  - calendar_management.py : 市場カレンダー管理（営業日判定、更新ジョブ）
  - quality.py : データ品質チェック
  - audit.py : 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats.py : zscore_normalize 等ユーティリティ
  - etl.py : ETLResult の再エクスポート
  - __init__.py

- src/kabusys/research/
  - factor_research.py : モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py : forward returns / IC / summary / rank
  - __init__.py

---

## 補足 / 注意点

- OpenAI 呼び出し:
  - news_nlp / regime_detector は OpenAI の Chat Completions（gpt-4o-mini 想定）を使用します。API キーは OPENAI_API_KEY 環境変数、または各関数の api_key 引数で渡してください。
  - API 呼び出しはリトライやフェイルセーフ（失敗時はスコア 0.0 にフォールバック）を備えていますが、回数制限やコストには注意してください。

- J-Quants:
  - get_id_token() は settings.jquants_refresh_token を使用して ID トークンを取得します。正しいトークンを .env に設定してください。
  - API レート制限 (120 req/min) を遵守する実装が組み込まれています。

- DuckDB の互換性:
  - 一部の実装は DuckDB のバージョン依存の挙動（executemany の空リストバインド等）を考慮しています。DuckDB のバージョンにより注意が必要です。

- セキュリティ:
  - news_collector は SSRF 対策、XML パースの安全化（defusedxml）、最大応答サイズの制限などを行っていますが、運用環境での外部接続は監視してください。

- 自動 .env ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml）を探索して .env を自動的に読み込みます。テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要に応じて README に追記します（例: Docker / systemd サービス化、より具体的な ETL スケジュール例、テスト手順など）。追加で欲しい節があれば教えてください。