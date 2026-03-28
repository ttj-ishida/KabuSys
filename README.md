# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）のリポジトリ内 README。  
本ドキュメントはコードベース（src/kabusys/...）を元に作成しています。

---

## プロジェクト概要

KabuSys は日本株のデータ取得、ETL、データ品質チェック、特徴量計算、ニュースNLP（LLMを用いたセンチメント評価）、市場レジーム判定、監査ログ（トレーサビリティ）、および発注監視のためのユーティリティ群を提供する Python モジュール群です。  
主に以下用途を想定しています：

- J-Quants API からのデータ取得（株価日足・財務・カレンダー等）
- DuckDB を用いたデータ蓄積と ETL（差分更新、バックフィル対応）
- ニュース収集・前処理と LLM（OpenAI）による銘柄センチメントの算出
- 市場レジーム判定（ETF + マクロ記事の LLM 評価の合成）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース）テーブル定義と初期化
- 研究用途のファクター計算・統計ユーティリティ

---

## 主な機能一覧

- data
  - J-Quants API クライアント（rate limit / リトライ / トークン自動リフレッシュ）
  - ETL パイプライン（日次 ETL の統合エントリ）
  - 市場カレンダー管理（営業日判定、next/prev 関数）
  - ニュース収集（RSS、SSRF 対策、前処理）
  - データ品質チェック（QualityIssue を返す）
  - 監査ログ初期化・DB 作成ユーティリティ（DuckDB）
  - 汎用統計ユーティリティ（Z-score 正規化）
- ai
  - ニュース NLP（gpt-4o-mini を想定した JSON Mode 呼び出し）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロ記事センチメントの合成）
- research
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
- config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）と Settings オブジェクト

---

## 前提 / 推奨環境

- Python 3.10+
- 必要外部ライブラリ（最低限）:
  - duckdb
  - openai
  - defusedxml

（実行環境により追加の依存が必要な場合があります。プロジェクトの pyproject.toml / requirements を参照してください。）

---

## インストール（開発環境例）

1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. （任意）パッケージを編集可能にインストール
   - pip install -e .

---

## 環境変数 / .env

本ライブラリは起動時にプロジェクトルート（.git または pyproject.toml の存在箇所）を探索し、以下の優先度で .env ファイルを自動ロードします:

- OS 環境変数（最優先）
- .env.local（存在すれば既存 OS 環境変数を上書きしないが .env を上書きする）
- .env（存在すれば未設定のキーを設定）

自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

代表的な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL      : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot Token（必須）
- SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）
- OPENAI_API_KEY         : OpenAI API キー（ai モジュールで利用）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : SQLite path（監視用途など）
- KABUSYS_ENV            : 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL              : ログレベル ("DEBUG", "INFO" ...)

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定値は Python コード上で次のように参照できます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # pathlib.Path
```

---

## セットアップ手順（データベース初期化例）

監査ログ用の DuckDB を初期化する例:
```python
from kabusys.data.audit import init_audit_db

# ファイルに保存する場合
conn = init_audit_db("data/audit.duckdb")

# メモリ DB を使う場合
conn = init_audit_db(":memory:")
```

DuckDB の接続は ETL や関数呼び出しに渡して利用します。

---

## 使い方（主要ワークフロー例）

以下は代表的な操作例です。すべての API は DuckDB 接続（duckdb.connect() で得られる接続オブジェクト）を引数に取ります。

- 日次 ETL を実行する（価格 / 財務 / カレンダー / 品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を算出して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（ETF 1321 + マクロニュース）を実行し market_regime に書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026, 3, 20)))
print(next_trading_day(conn, date(2026, 3, 20)))
```

- 監査ログスキーマを既存 DB に追加
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 注意点 / 設計上の留意事項

- Look-ahead Bias 対策: 多くの関数は内部で datetime.today() / date.today() を安易に参照しない設計です（外部から target_date を渡すことを前提）。
- API 呼び出し: J-Quants・OpenAI 呼び出しはレート制限とリトライロジックを内包していますが、API キー/トークンは環境変数で適切に管理してください。
- LLM 呼び出し: ai モジュールは OpenAI の Chat Completions（gpt-4o-mini を想定）を JSON Mode で使用します。料金やレートに注意してください。
- .env 自動ロードはプロジェクトルートを探索して行います。テストなどで自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成（主要ファイルと概要）

src/kabusys/
- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数 / .env 自動読み込み, Settings オブジェクト
- ai/
  - __init__.py — ai 公開 API
  - news_nlp.py — ニュースの LLM ベースセンチメント算出（ai_scores 書き込み）
  - regime_detector.py — 市場レジーム判定（ETF MA200 + マクロ LLM）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 & DuckDB 保存関数）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — market_calendar 管理・営業日判定
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（各種 check_...）
  - audit.py — 監査ログスキーマ定義と初期化ユーティリティ
  - news_collector.py — RSS 取得・前処理・raw_news 挿入
- research/
  - __init__.py — 研究用 API エクスポート
  - factor_research.py — ファクター計算（momentum / value / volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

---

## サポート / テスト

- テスト用のモックポイントがコード内に用意されている（例: OpenAI 呼び出しを簡単に差し替え可能）ため、ユニットテストの作成が容易です。
- DuckDB を使うため、軽量にローカルでの回帰テストが可能です。

---

必要に応じて README に追記します。特に導入手順（pip / pyproject.toml ベースのインストール）、CI / テスト手順、サンプルデータの初期化スクリプトなどを追加希望があれば教えてください。