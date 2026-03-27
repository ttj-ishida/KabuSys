# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）のリポジトリ向け README。  
本ドキュメントはリポジトリ内のコードベース（src/kabusys）を元に作成しています。

目次
- プロジェクト概要
- 主な機能
- 前提・依存関係
- セットアップ手順
- 環境変数（.env）一覧
- 使い方（主な API 呼び出し例）
- ディレクトリ構成（主要ファイルの説明）
- 注意事項 / 実運用での留意点

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームと自動売買基盤のライブラリセットです。  
主に以下の領域をカバーします。

- J-Quants API を使用したデータ取得（株価・財務・市場カレンダー等）
- ETL パイプライン（差分取得／保存／品質チェック）
- ニュースの収集と LLM を用いたニュースセンチメント評価（銘柄別）
- 市場レジーム判定（ETF MA とマクロニュースセンチメントの合成）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 研究用ユーティリティ（ファクター計算、IC 計算、Z スコア正規化 等）

設計方針の一部：
- ルックアヘッドバイアスを避ける（内部で date.today() 等を不用意に参照しない）
- DuckDB を主要な分析 DB として利用
- OpenAI（gpt-4o-mini 等）を利用した JSON Mode を用いる LLM 呼び出しを含む
- idempotent な DB 保存（ON CONFLICT / DELETE→INSERT の取り扱い）

---

## 主な機能（機能一覧）

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - データ品質チェック（欠損、重複、スパイク、日付整合性）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day）
  - ニュース収集（RSS 取得、前処理、raw_news 保存用ユーティリティ）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize 等）
- ai/
  - ニュース NLP（score_news）: 銘柄ごとのニュースセンチメント算出・ai_scores への書き込み
  - 市場レジーム判定（score_regime）: ETF 1321 の MA200 とマクロニューススコアを合成
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）

---

## 前提・依存関係

最低限必要な主要 Python ライブラリ（抜粋）：
- Python 3.9+
- duckdb
- openai （OpenAI Python SDK）
- defusedxml
- （標準ライブラリ: urllib, json, logging 等）

インストールはプロジェクトの依存リストに合わせて行ってください（requirements.txt / pyproject.toml がある想定）。最低限の例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトに requirements.txt / pyproject.toml があれば:
# pip install -e .
```

DuckDB は Python パッケージ `duckdb` を利用します。システム側インストールは不要で、pip で利用可能です。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
2. 依存ライブラリをインストールする（上記参照）
3. 環境変数を用意する（下項「環境変数（.env）一覧」参照）
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を置くと、自動で読み込まれます
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
4. DuckDB ファイルなどデータフォルダを作成する（settings.duckdb_path のデフォルトは data/kabusys.duckdb）
5. 必要に応じて監査 DB を初期化する（例: data/audit.duckdb）
   - 例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 環境変数（.env）一覧

以下はコードで参照されている主要な環境変数です。`.env.example` を作成しておくと便利です。

必須（ライブラリ使用機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（jquants_client.get_id_token で利用）
- SLACK_BOT_TOKEN
  - Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID
  - Slack 通知を送る対象チャンネル ID
- KABU_API_PASSWORD
  - kabuステーション API を使う場合のパスワード

任意 / デフォルトあり:
- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - デフォルト: data/monitoring.db
- KABUSYS_ENV
  - 有効値: development / paper_trading / live（デフォルト development）
- LOG_LEVEL
  - 有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- OPENAI_API_KEY
  - OpenAI を使う操作（score_news, score_regime 等）で用いられる。関数へ api_key 引数で注入可能。
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 をセットするとパッケージ起動時の .env 自動ロードを無効化

自動ロード:
- パッケージの config モジュールは、プロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動読み込みします（OS 環境変数優先、`.env.local` は上書き）。テスト時は自動ロードを無効化できます。

---

## 使い方（代表的な API 呼び出し例）

以下は本ライブラリの主要な使い方のサンプルです。実行前に環境変数（OpenAI / J-Quants など）を設定してください。

- 設定値の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)     # Path オブジェクト
print(settings.is_live)         # bool
```

- DuckDB 接続と ETL（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 個別 ETL ジョブ（価格データのみ）
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

- OpenAI を使ったニューススコア（銘柄別）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すか、OPENAI_API_KEY を環境変数に設定
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"written: {n_written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査 DB の初期化（監査ログテーブル作成）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# 既定で UTC タイムゾーンを設定し、テーブルとインデックスを作成します
```

- J-Quants API から直接データ取得
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# id_token を明示的に取得することも可能
id_token = get_id_token()
quotes = fetch_daily_quotes(id_token=id_token, date_from=date(2026,3,1), date_to=date(2026,3,20))
```

注: 上記例はシンプルな呼び出しの例です。実運用では例外処理やログ、リトライ戦略を組み込んでください。

---

## ディレクトリ構成（主要ファイルと説明）

以下は src/kabusys 配下の主要モジュールとその役割です（抜粋）。

- src/kabusys/__init__.py
  - パッケージ定義。version 情報と公開サブパッケージ。

- src/kabusys/config.py
  - 環境変数 / .env の自動ロードと Settings クラスを提供。
  - 必須環境変数未設定時は ValueError を発生させる _require を使用。

- src/kabusys/ai/
  - news_nlp.py : ニュース記事の LLM による銘柄別センチメント算出（score_news）
  - regime_detector.py : ETF（1321）200日 MA とニュースセンチメントを合成して市場レジーム判定（score_regime）

- src/kabusys/data/
  - jquants_client.py : J-Quants API クライアント（取得・保存・認証・リトライ・レートリミット）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）と ETLResult データクラス
  - news_collector.py : RSS 取得・前処理・ID 生成・SSRF 対策
  - calendar_management.py : マーケットカレンダー管理（is_trading_day 等）
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py : 監査ログ（signal_events, order_requests, executions）の DDL と初期化ユーティリティ
  - stats.py : zscore_normalize 等の汎用統計関数
  - etl.py : パイプラインインターフェースの再エクスポート（ETLResult）

- src/kabusys/research/
  - factor_research.py : モメンタム・バリュー・ボラティリティ等のファクター計算
  - feature_exploration.py : 将来リターン、IC、統計サマリー等

（strategy, execution, monitoring などのサブパッケージは将来機能として想定されるものや公開 API の一部としてパッケージ初期化で名前が出ています）

---

## 注意事項 / 実運用での留意点

- OpenAI API 呼び出しはコストとレートリミットに注意してください。score_news / score_regime はリトライ・フォールバック（失敗時に 0.0 を返す等）を備えていますが、運用ルールを設けてください。
- J-Quants API の利用は API レートと認証（refresh token）管理に依存します。get_id_token は自動リフレッシュとキャッシュを備えています。
- DuckDB の executemany はバージョンにより制約（空リストを渡せない等）があるため、コード側でガードしています。DB バージョン差分に注意してください。
- ニュース収集は SSRF や Gzip/Bomb 対策を実装していますが、外部フィードの扱いには注意してください（信頼できるソースのみを RSS ソースに登録する等）。
- 本パッケージはバックテスト用のデータ取得 / ETL と、実口座での発注部分（発注 API 連携）は分離して設計されています。実際の売買実装時はさらに安全対策（発注の二重防止、最大発注量チェック、ドライラン機能等）を追加してください。

---

もし README に追加したい具体的な内容（運用手順、CI/CD、追加の初期化スクリプト、例の .env.example のテンプレートなど）があれば指示してください。必要に応じて README を拡張してサンプル .env.example やデプロイ手順も追記します。