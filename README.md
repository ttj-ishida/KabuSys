# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ。  
J-Quants / kabuステーション / RSS / OpenAI を組み合わせて、データ収集（ETL）・品質チェック・ニュースのAI評価・市場レジーム判定・監査ログ管理などを行うためのユーティリティ群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とする Python パッケージです。

- J-Quants API からの市場データ（株価・財務・カレンダー等）の差分取得と DuckDB への冪等保存（ETL）
- ニュース RSS の収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（銘柄別）とマクロセンチメント評価
- 市場レジーム（bull / neutral / bear）判定ロジック
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）用のスキーマ初期化ユーティリティ
- 研究用途のファクター計算・特徴量探索ユーティリティ

設計上の特徴:
- Look-ahead バイアス対策（内部で date.today()/datetime.today() による安易な参照を避ける）
- ETL や保存処理は冪等（重複回避）に配慮
- API 呼び出しはリトライ／バックオフ・レート制限を実装
- DuckDB ベースでローカル保存・高速クエリ

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（取得 / 保存関数）
  - market calendar 管理（営業日判定、next/prev）
  - news_collector（RSS 取得・前処理・SSRF 対策）
  - quality（品質チェック: 欠損 / スパイク / 重複 / 日付不整合）
  - audit（監査ログスキーマ初期化）
  - stats（zscore_normalize などの統計ユーティリティ）
- ai/
  - news_nlp.score_news（銘柄別ニュースセンチメントを ai_scores に保存）
  - regime_detector.score_regime（ETF 1321 の MA200 とマクロセンチメントを使って market_regime を書き込み）
- research/
  - factor_research（momentum / value / volatility などのファクター計算）
  - feature_exploration（将来リターン計算、IC、統計サマリー）
- config.py
  - .env/.env.local 自動読み込み（プロジェクトルート検出）
  - settings オブジェクトによる環境変数管理

---

## 前提 / 必要環境

- Python 3.10+
  - コード中で型ヒントに `|` を使用しているため 3.10 以上を想定しています。
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

例: pip でのインストール例
```bash
python -m pip install duckdb openai defusedxml
```

（プロジェクトに requirements.txt / packaging があればそれに従ってください）

---

## 環境変数（主なもの）

設定は .env（または .env.local）または OS 環境変数から読み込まれます。パッケージはプロジェクトルート（.git または pyproject.toml を検索）を基準に自動的に .env を読み込みます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

最低限設定が必要な環境変数（例）
- JQUANTS_REFRESH_TOKEN ・・・ J-Quants のリフレッシュトークン（必須）
- SLACK_BOT_TOKEN         ・・・ Slack 通知に使うボットトークン（必須：通知を使う場合）
- SLACK_CHANNEL_ID        ・・・ Slack チャンネル ID（必須：通知を使う場合）
- KABU_API_PASSWORD       ・・・ kabuステーション API パスワード（必須：kabu API を使うモジュールがある場合）
- OPENAI_API_KEY          ・・・ OpenAI を環境変数で提供する場合に設定（score_news / score_regime で参照）
- DUCKDB_PATH             ・・・ DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH             ・・・ 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV             ・・・ "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL               ・・・ "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカルでの基本）

1. リポジトリをクローン / 作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
3. 必要パッケージをインストール
   ```bash
   pip install -U pip
   pip install duckdb openai defusedxml
   ```
4. .env を作成して前項の必要環境変数を設定
5. DuckDB 用ディレクトリを作成（必要なら）
   ```bash
   mkdir -p data
   ```
6. （任意）監査用 DB の初期化やスキーマ作成はコードから実行

---

## 使い方（主要なユースケース例）

Python REPL やスクリプトから直接呼べます。以下は利用例です。

- DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を使ってもOK
```

- 日次 ETL の実行（J-Quants から差分取得して保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日を使います（内部ロジックで営業日に調整されます）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースのAIスコアリング（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date に対するニュースウィンドウを処理し、ai_scores テーブルへ書き込みます
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を利用
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DB を作成してスキーマを投入）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または init_audit_schema(conn) を既存 conn に対して呼ぶ
```

- ファクター計算 / 研究ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "ma200_dev"])
```

---

## ETL 実行結果の扱い（ETLResult）

run_daily_etl は ETLResult オブジェクトを返します。主要フィールド:
- target_date: 対象日
- prices_fetched / prices_saved: 株価の取得数・保存数
- financials_fetched / financials_saved: 財務データの取得数・保存数
- calendar_fetched / calendar_saved: カレンダー取得/保存数
- quality_issues: 品質チェックで検出された問題のリスト（QualityIssue オブジェクト）
- errors: ETL 中に発生したエラーの簡易メッセージリスト

例: result.to_dict() で辞書化してログ出力に使えます。

---

## 注意事項 / 設計上のポイント

- OpenAI 呼び出しにはレート・エラー耐性（リトライ/バックオフ）が組み込まれていますが、API 利用料や利用制限に注意してください。
- J-Quants からのデータ取得は rate limiter を実装していますが、実運用では API 利用規約に従ってください。
- DuckDB の executemany に関するバージョン依存の注意（コード内で互換性対策をしています）。
- 自動ロードされる .env はプロジェクトルート検出に依存します（.git または pyproject.toml）。テストや特殊環境で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- score_news / score_regime は OpenAI API キーが必要です。api_key 引数で注入するか環境変数 OPENAI_API_KEY を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール一覧と簡単な説明。

- src/kabusys/__init__.py
- src/kabusys/config.py
  - settings: 環境変数ラッパー、.env 自動読み込みロジック
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py         : ニュースを銘柄別に集約して OpenAI でスコアリング、ai_scores へ保存
  - regime_detector.py  : ETF 1321 の MA200 とマクロセンチメントを合成して market_regime へ保存
- src/kabusys/data/
  - __init__.py
  - calendar_management.py : market_calendar 管理、営業日ロジック
  - etl.py (re-export)
  - pipeline.py            : 日次 ETL パイプライン（run_daily_etl 等）
  - stats.py               : zscore_normalize 等
  - quality.py             : データ品質チェック群
  - audit.py               : 監査ログ用テーブル/インデックス定義・初期化
  - jquants_client.py      : J-Quants API クライアント + DuckDB 保存関数
  - news_collector.py      : RSS 取得・前処理・保存ユーティリティ（SSRF 対策、gzip 制限等）
- src/kabusys/research/
  - __init__.py
  - factor_research.py     : Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー

プロジェクトルート（想定）
- pyproject.toml / setup.cfg / setup.py（パッケージ設定）
- .git/
- .env (または .env.local)
- src/
  - kabusys/...
- data/ （デフォルトのデータ保存先）

---

## 最後に

この README はコードベースの主要機能・使い方を要約したものです。実運用・詳細な設定やスキーマなどは各モジュール（kabusys.data.jquants_client / pipeline / audit / ai.news_nlp / ai.regime_detector など）の docstring を参照してください。必要であればサンプルスクリプトや運用手順（cron / GitHub Actions / Airflow などでの定期実行例）も追加できます。