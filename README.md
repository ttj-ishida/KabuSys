# KabuSys

日本株向けのデータプラットフォーム兼自動売買（研究・シグナル生成・監査）ライブラリです。  
ETL、データ品質チェック、ファクター計算、ニュースNLP（OpenAI使用）、市場レジーム判定、監査ログ等の主要機能を提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群をまとめた Python パッケージです。

- J-Quants API からのデータ取得（株価・財務・カレンダー）
- DuckDB を用いたデータ永続化と差分 ETL パイプライン
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）および OpenAI を用いた記事センチメント評価（銘柄別 ai_score）
- 市場レジーム判定（ETF の MA とマクロニュースセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、正規化）
- 監査（signal → order_request → execution のトレーサビリティ）用スキーマおよび初期化

設計上の特徴:
- ルックアヘッドバイアスを避ける（内部で date.today() 等を不用意に参照しない）
- DuckDB を中心に SQL と Python を組み合わせた処理
- 冪等性（INSERT ... ON CONFLICT DO UPDATE / DO NOTHING 等）
- 外部 API 呼び出しに対するリトライ・レート制御・フォールバックを実装

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: API 呼び出し・保存（fetch / save）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - news_collector: RSS 収集＆raw_news への保存（SSRF 対策・前処理）
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit: 監査ログスキーマ生成・監査 DB 初期化
  - stats: zscore_normalize 等共通統計ユーティリティ
- ai
  - news_nlp.score_news: OpenAI を用いた銘柄別ニュースセンチメント集計・ai_scores へ保存
  - regime_detector.score_regime: ETF MA と LLM マクロセンチメントを合成して market_regime を更新
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件 / 依存関係

- Python 3.10+
- 主な Python パッケージ:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで実装されている部分も多いです）

インストール例（仮に requirements.txt が無い場合）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# パッケージを開発モードでインストールする場合
pip install -e .
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（読み込み優先度: OS 環境変数 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使用される環境変数:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabu ステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- OpenAI / AI
  - OPENAI_API_KEY (news_nlp / regime_detector に未指定時に参照)
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベースパス（デフォルトは data/ 以下）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用, デフォルト: data/monitoring.db)
- 監視関連
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- システム環境
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/...

設定参照方法の例:

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## セットアップ手順（概要）

1. リポジトリをクローンして Python 仮想環境を作成
2. 依存パッケージをインストール（duckdb, openai, defusedxml など）
3. プロジェクトルートに `.env` を作成し必要な環境変数を設定（.env.example を参考にする想定）
4. DuckDB のデータベースを用意（デフォルトは data/kabusys.duckdb）
5. 監査用 DB を初期化（必要に応じて）

監査 DB 初期化例:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続
```

---

## 使い方（主要な利用例）

以下は主要なモジュールの呼び出し例です。いずれも DuckDB の接続を渡して実行します。

- 日次 ETL 実行

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント評価（OpenAI APIキーは env か api_key 引数で指定）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- ファクター計算（研究用）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の辞書リスト
```

- データ品質チェック

```python
from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意:
- OpenAI を使う機能は API コストが発生します。API キーは厳重に管理してください。
- ETL / API 呼び出しはネットワーク・レート制御とリトライを備えていますが、運用時はログやエラーハンドリングを適切に行ってください。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env の自動読み込みと Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースの銘柄別センチメント算出・ai_scores 書込み
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save）
  - pipeline.py — ETL 実行ロジック（run_daily_etl 他）
  - etl.py — ETLResult エクスポート
  - calendar_management.py — 市場カレンダー管理、営業日判定
  - news_collector.py — RSS 取得・前処理・raw_news 書込み（SSRF対策）
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付整合）
  - audit.py — 監査テーブル DDL と初期化ユーティリティ
  - stats.py — zscore_normalize 等統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py — モメンタム・バリュー・ボラティリティ計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- research/*（各種研究ユーティリティ）

---

## 運用上の注意 / ベストプラクティス

- 環境変数や API キーは Git に含めないでください。`.env` は .gitignore に追加することを推奨します。
- OpenAI 呼び出しで失敗した場合、モジュールはフェイルセーフとしてスコア 0.0 を採用する処理がありますが、長期的にはエラーログを監視して対処してください。
- DuckDB ファイルのバックアップやスキーママイグレーション方針を明確にしてください。
- ニュース収集や外部 API 呼び出しはレートや著作権に注意して利用してください。

---

もし README に追加したい内容（例: CI 実行方法、ローカル開発コマンドやサンプルデータの初期化スクリプト、より詳しい API の使用例など）があれば教えてください。必要に応じてセクションを追記します。