# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリセットです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、監査ログ用スキーマなどを含みます。

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からの株価 / 財務 / カレンダー取得（差分ETL・保存・品質チェック）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント解析（銘柄ごとの ai_score、マクロセンチメント）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 研究（ファクター計算・将来リターン・IC 計算・統計ユーティリティ）
- 監査ログ（信号→発注→約定のトレーサビリティ用 DuckDB スキーマ）

設計上の特徴：

- Look-ahead bias を防ぐ設計（内部で date.today() を直接参照しない等）
- DuckDB をデータストアに利用（ETL / 解析 / 監査テーブル）
- 冪等性の確保（ON CONFLICT / idempotent 保存）
- ネットワーク / API 呼び出しに対するリトライ・レート制御・フェイルセーフ

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ユーティリティ
- データ取得・ETL（kabusys.data.*）
  - J-Quants クライアント（rate limiting / token refresh / pagination）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - market_calendar 管理・営業日ロジック
  - ニュース収集（RSS）と前処理（SSRF 対策、正規化）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化・専用 DB 初期化（監査スキーマ）
- AI（kabusys.ai.*）
  - ニュースセンチメント解析（score_news）
  - マクロセンチメント + MA で市場レジーム判定（score_regime）
  - OpenAI 呼び出しは安全なリトライ処理を実装
- 研究用ユーティリティ（kabusys.research.*）
  - momentum / value / volatility 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 汎用統計（kabusys.data.stats）
  - Z スコア正規化など

---

## セットアップ手順

必要条件
- Python 3.10+
- DuckDB（Python パッケージ）
- OpenAI Python SDK（openai）
- defusedxml
- その他（標準ライブラリ以外の外部依存がある場合は適宜追加）

例: 仮想環境を作って依存を入れる（requirements.txt がない場合は個別インストール）

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# もしパッケージをローカルで編集して使うなら
pip install -e .
```

環境変数（最低限必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（本リポジトリ内の利用箇所に応じて）
- SLACK_BOT_TOKEN: Slack 通知に利用する Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")（任意、デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を配置すると自動的に読み込まれます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

データベースパス（デフォルト）
- DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可能）
- 監視用 SQLite: data/monitoring.db（SQLITE_PATH）

---

## 使い方（代表的な例）

以下は Python REPL / スクリプトから機能を呼ぶ基本例です。すべて duckdb 接続を渡して利用します。

1) DuckDB へ接続

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) ETL 日次パイプラインを実行（例: 今日分）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントをスコア化（score_news）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY を設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"wrote {n_written} ai_scores")
```

4) 市場レジーム判定（score_regime）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ DB の初期化（監査専用 DB を作る例）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は初期化済みの DuckDB 接続
```

注意点
- OpenAI を用いる関数は api_key を引数で受け取るか、環境変数 OPENAI_API_KEY を参照します。
- 日付の扱いは Look-ahead を避けるため関数に target_date を明示して呼ぶ設計です（内部で date.today() を直接参照しない実装方針）。
- ETL / API 呼び出しはネットワークエラー時にリトライを行いますが、失敗時はログや戻り値で検知してください。

---

## 環境変数の一覧（主要）

必須と思われる環境変数：
- JQUANTS_REFRESH_TOKEN
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- KABU_API_PASSWORD（kabu API を利用するモジュールがある場合）
- OPENAI_API_KEY（AI モジュールを利用する場合）

オプション：
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- KABUSYS_ENV（development/paper_trading/live）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env ロードを無効化する場合は 1）

設定ファイル:
- .env, .env.local（プロジェクトルートに置くと自動で読み込まれます）

---

## ディレクトリ構成

主要ファイルと役割を抜粋します（src 以下）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py       — ニュースセンチメント解析（score_news）
    - regime_detector.py— マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / rate limiting）
    - pipeline.py       — ETL パイプライン (run_daily_etl 他)
    - etl.py            — ETLResult 再エクスポート
    - news_collector.py — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - quality.py        — データ品質チェック
    - stats.py          — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py          — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility 等
    - feature_exploration.py— 将来リターン / IC / 統計サマリー等
  - monitoring/ (パッケージ上では __all__ に含まれている想定)
  - execution/, strategy/, monitoring/ (パッケージ名が __all__ に含まれている箇所あり)

（上記はリポジトリ内の主要モジュールの役割を示した一覧です）

---

## 開発 / テストに関するメモ

- 型注釈と Python 3.10 の構文（X | Y）を使用しています。Python バージョンに注意してください。
- OpenAI SDK は JSON Mode / response_format を使用する箇所があり、SDK のバージョン差異に注意が必要です（API の戻り値構造が変更されるとパースに影響します）。
- ニュース収集では defusedxml を使っているため XML 関連の安全対策は組み込まれています。
- .env のパースはシェル風のクォートやコメントに対応する独自実装が含まれます（kabusys.config）。
- 自動 env 読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（ユニットテスト等で便利です）。

---

## ライセンス / 貢献

（この README に元のライセンス情報は含まれていません。実際のリポジトリに LICENSE ファイルがあればそこを参照してください。）

貢献方法や Issue / PR の流れはリポジトリの CONTRIBUTING.md や Issue テンプレートを参照してください。

---

この README はコードの主要機能と使用方法の概要を示しています。詳細は各モジュールの docstring（ソース）を参照してください。必要であれば、実行例や CI 手順、より詳しい環境設定のテンプレート（.env.example）の追記を作成します。