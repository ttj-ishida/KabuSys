# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（発注・約定トレーサビリティ）など、取引システムに必要な主要機能をモジュール化して提供します。

- ライセンスや配布方法はこのリポジトリのルールに従ってください（ここでは実装コードのドキュメントのみを記載します）。

---

## 目次

- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要な関数・例）
- 環境変数 / .env 例
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は、日本株を対象とした以下の処理を備えたライブラリセットです。

- J-Quants API から株価・財務・市場カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と記事の前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント解析（銘柄単位の ai_score）およびマクロセンチメントとテクニカル指標を組み合わせた「市場レジーム判定」
- ファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量探索ツール（将来リターン、IC、統計サマリー）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ用テーブル（signal_events, order_requests, executions）と初期化ユーティリティ

設計方針として、ルックアヘッドバイアスの排除、冪等性（ON CONFLICT 等）、外部 API 呼び出しの堅牢なリトライ・レート制御、テストしやすい実装を重視しています。

---

## 機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - market_calendar 管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - news_collector（RSS 取得・前処理・保存ロジック）
  - quality（データ品質チェック）
  - audit（監査ログスキーマ初期化・DB 初期化）
  - stats（zscore_normalize 等）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄ごとのニュースセンチメント算出と ai_scores 書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime テーブルへ書き込み
- research/
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

その他、設定管理モジュール（kabusys.config）やユーティリティを含みます。

---

## セットアップ手順

前提:
- Python 3.10 以上（Union 型記法や型ヒントにより3.10+を想定）
- DuckDB を利用（ローカルファイルまたは :memory:）

1. リポジトリをクローン（またはプロジェクト直下で作業）
2. 仮想環境を作成して有効化（推奨）
   - python -m venv venv
   - source venv/bin/activate  （Windows: venv\Scripts\activate）
3. 依存パッケージをインストール

例（最低限の依存）:
```bash
pip install duckdb openai defusedxml
# または開発用に:
pip install -e .
```

4. 環境変数またはプロジェクトルートの .env/.env.local を準備（後述の .env 例を参照）

5. データベースディレクトリ作成（必要に応じて）
```bash
mkdir -p data
```

注意:
- config モジュールはプロジェクトルート（.git または pyproject.toml を起点）から .env の自動読み込みを行います。自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数 / .env 例

必須・想定される環境変数の一例:

- JQUANTS_REFRESH_TOKEN=...       # J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD=...          # kabuステーション API パスワード（必須）
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）
- SLACK_BOT_TOKEN=...            # Slack 通知用（必須）
- SLACK_CHANNEL_ID=...           # Slack 通知先（必須）
- OPENAI_API_KEY=...             # OpenAI（AI モジュールで未指定時に参照）
- DUCKDB_PATH=data/kabusys.duckdb # デフォルトパス
- SQLITE_PATH=data/monitoring.db  # 監視用 SQLite（オプション）
- KABUSYS_ENV=development|paper_trading|live  # 環境（デフォルト development）
- LOG_LEVEL=INFO|DEBUG|...       # ログレベル

例 (.env.example):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

※ 機密情報は Git 管理しないでください（.gitignore に .env を追加）。

---

## 使い方

以下は代表的な利用例（Python スクリプト内での呼び出し例）です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を受け取ります。

- DuckDB 接続の作成例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイルがなければ作成されます
```

- ETL を日次で実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 個別 ETL（株価のみ）
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
print(f"fetched={fetched}, saved={saved}")
```

- ニュースセンチメント（銘柄ごとの ai_scores 生成）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} ai_scores")
```
- 市場レジーム判定（market_regime テーブルへ書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（audit）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/kabusys_audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- ファクター計算（研究用）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
# momentum は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
```

- 設定参照例
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- AI 関連関数（score_news, score_regime）は OpenAI API キーを引数で渡すことが可能です（api_key）。引数未指定時は環境変数 OPENAI_API_KEY を参照します。未設定だと ValueError を送出します。
- J-Quants クライアント関数は内部でトークンを自動リフレッシュしますが、テストや特殊用途では id_token を明示的に渡すことも可能です。
- 多くのデータ操作は DuckDB のテーブル（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar など）を前提とします。スキーマは実行時にプロジェクトの初期化コードで作成するか、ETL で自動生成するワークフローを用意してください。

---

## ロギング / 環境設定

- 設定値は環境変数から読み込まれます（kabusys.config.Settings を参照）。.env ファイルはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動読み込みされます。
- 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利です）。
- 利用可能な KABUSYS_ENV: `development`, `paper_trading`, `live`
- LOG_LEVEL は `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` のいずれか。

---

## ディレクトリ構成

主要なソースツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py            # ニュース NLP（score_news）
      - regime_detector.py     # 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（fetch / save / get_id_token）
      - pipeline.py           # ETL パイプライン（run_daily_etl など）
      - news_collector.py     # RSS ニュース収集（fetch_rss 等）
      - calendar_management.py# 市場カレンダー管理（is_trading_day 等）
      - quality.py            # データ品質チェック
      - audit.py              # 監査ログスキーマ／初期化
      - etl.py                # ETLResult 再エクスポート
      - stats.py              # 統計ユーティリティ（zscore_normalize）
    - research/
      - __init__.py
      - factor_research.py    # モメンタム / ボラティリティ / バリュー計算
      - feature_exploration.py# 将来リターン / IC / 統計サマリー
    - research/ (他のモジュール)
    - (その他 strategy, execution, monitoring 等のパッケージは __all__ に示されているがここでは省略)

--- 

## 開発・運用上の注意点

- Look-ahead バイアスの回避: 多くの関数は内部で datetime.today() や date.today() を直接参照しない設計です。バックテスト等で過去の date を明示的に渡して利用してください。
- 冪等性: J-Quants からの保存処理は ON CONFLICT DO UPDATE 等で冪等実装になっています。ETL は差分取得とバックフィルを組み合わせて運用してください。
- 外部 API のリトライ / レート制御: J-Quants クライアントや OpenAI 呼び出しはリトライ・バックオフやレートリミットを実装していますが、運用時は API 利用制限を十分に考慮してください。
- セキュリティ: .env に機密情報を保存する場合は適切に管理し、リポジトリにコミットしないでください。news_collector では SSRF 対策や XML インジェクション対策（defusedxml）を取り入れています。

---

もし README に追加したい点（例: CI / テスト実行方法、具体的なスキーマ DDL、サンプルデータの作成手順、Slack 通知の使い方など）があれば教えてください。必要に応じて追記・調整します。