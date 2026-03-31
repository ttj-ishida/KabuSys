# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データの ETL、ニュースによる NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）などを提供します。

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API など外部データソースからの差分取得（株価・財務・カレンダー）
- DuckDB を用いたデータ永続化と品質チェック
- ニュースを LLM（OpenAI）でスコアリングして銘柄ごとの AI スコアを生成
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用のファクター計算・特徴量探索ユーティリティ
- 発注・約定に至る一連の監査ログ（監査テーブルの初期化・管理）

設計上、バックテストでのルックアヘッドバイアスを防ぐ工夫や、外部 API への堅牢なリトライ／レート管理が施されています。

---

## 機能一覧

主なモジュール・機能：

- kabusys.config
  - .env / 環境変数から設定を読み取り（自動ロード機能あり）
- kabusys.data
  - ETL（pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（jquants_client）
  - market_calendar 管理（calendar_management）
  - ニュース収集（news_collector）
  - 品質チェック（quality）
  - 統計ユーティリティ（stats）
  - 監査ログ初期化・操作（audit）
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM でスコア化し ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースを合成して市場レジーム判定
- kabusys.research
  - ファクター計算（momentum/value/volatility）
  - 将来リターン / IC / 統計サマリー 等の研究ユーティリティ

主要な設計思想：
- DuckDB を主要なローカル DB として使用
- LLM（OpenAI）呼び出しは JSON Mode を利用し堅牢なバリデーションとリトライ処理
- ETL は差分取得・バックフィルをサポートし、品質チェックを行う

---

## 必要条件（主な依存）

- Python 3.10+
- duckdb
- openai（OpenAI の新しい SDK を想定）
- defusedxml
- そのほか標準ライブラリのみで多くを実装

インストール例（プロジェクトに setup/pyproject がある想定）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .            # 開発インストール（pyproject/TBD）
pip install duckdb openai defusedxml
```

（プロジェクトに requirements.txt / extras があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン、仮想環境を作成して依存をインストールします。

2. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置できます。`kabusys.config` は自動的にプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` を読み込みます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。
   - 主要な環境変数（例）:

```
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=yyy
SLACK_BOT_TOKEN=zzz
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

3. DuckDB ファイルの準備
   - 指定した `DUCKDB_PATH` に DB ファイルを作成して接続します（必要に応じて初期スキーマ作成機能を呼ぶ実装を提供してください）。
   - 監査用 DB を別 DB に分けたい場合は `kabusys.data.audit.init_audit_db(path)` を利用できます（パスの親ディレクトリは自動作成されます）。

---

## 使い方（主要な例）

以下は Python スクリプトからの利用例です。適宜ログ設定やエラーハンドリングを行ってください。

- DuckDB 接続の取得例：

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（差分取得・品質チェック含む）：

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（ai_scores テーブルへ書き込む）：

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数か api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（market_regime テーブルへ書き込み）：

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, target_date=date(2026, 3, 20))
print("score_regime result:", res)
```

- 監査ログ DB 初期化（監査用 DB を新規作成）：

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 必要なら audit_conn をアプリケーションに渡して使う
```

- market_calendar の夜間更新ジョブ（J-Quants から差分取得）：

```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("保存件数:", saved)
```

注意点：
- OpenAI は API キー（OPENAI_API_KEY）を必要とします。未設定の場合、score_news / score_regime は ValueError を送出します。
- J-Quants 認証は `JQUANTS_REFRESH_TOKEN` を利用するか、jquants_client.get_id_token に明示的に渡します。
- 実行環境のログレベルは `LOG_LEVEL` で制御できます（Settings.log_level）。

---

## 環境変数の挙動（自動ロード）

- 起動時、`kabusys.config` はプロジェクトルートを特定し `.env` → `.env.local` の順で読み込みます。
- OS 環境変数は上書きされません（`.env.local` は override=True で読み込まれますが、OS 環境変数は保護されます）。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（抜粋）

src/kabusys 以下の主要ファイル・モジュール：

- __init__.py
- config.py

- ai/
  - __init__.py
  - news_nlp.py           — ニュース NLP（score_news）
  - regime_detector.py    — 市場レジーム判定（score_regime）

- data/
  - __init__.py
  - jquants_client.py     — J-Quants API クライアント（fetch / save）
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETL 型の再エクスポート
  - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
  - news_collector.py     — RSS ニュース収集ユーティリティ
  - quality.py            — データ品質チェック（run_all_checks 等）
  - stats.py              — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py              — 監査ログ（監査スキーマ定義・初期化）
  - (その他: pipeline/etl 関連)

- research/
  - __init__.py
  - factor_research.py    — ファクター計算（momentum/value/volatility）
  - feature_exploration.py— 将来リターン・IC・統計サマリー 等

（上記は主要なモジュールの抜粋です。細部のファイル構成はリポジトリを参照してください）

---

## 開発・運用上の注意

- LLM（OpenAI）呼び出しはネットワークエラーやレート制限に備えたリトライロジックを持ちますが、API コストやレートに注意してください。
- DuckDB のバージョン差異（特に executemany の空リストの扱い等）に依存する箇所があるため、プロジェクトで指定された DuckDB バージョンを合わせてください。
- ETL・スコアリングは「ルックアヘッドバイアス防止」を意識した実装になっています（target_date 未満または指定ウィンドウのみ参照）。
- 監査ログのスキーマは冪等（IF NOT EXISTS）で作成され、UTC タイムゾーン保存を前提としています。

---

## ライセンス・貢献

（ここにライセンス情報、貢献ガイドライン、連絡先等を追記してください）

---

README は以上です。実際に運用する際は環境変数の管理（シークレット管理）、OpenAI/J-Quants API 使用料やレート制限、ログ設定などを十分に検討してください。必要であれば、例示スクリプトや初期スキーマ作成スクリプトの追加を支援します。