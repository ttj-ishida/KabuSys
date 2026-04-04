# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・AI 支援・監査ログを備えた自動売買支援ライブラリです。J-Quants API からのデータ取得、DuckDB による永続化、ニュースの NLP スコアリング（OpenAI）や市場レジーム判定、ファクター計算・特徴量探索、ETL パイプライン、監査ログスキーマの初期化などを提供します。

---

## 主な特徴

- J-Quants からの差分 ETL（株価日足 / 財務 / 市場カレンダー）
- DuckDB を用いたデータ保存（冪等保存・ON CONFLICT 対応）
- ニュース収集と NLP（OpenAI）による銘柄別センチメント（ai_scores）
- マクロニュース + ETF（1321）200 日 MA に基づく市場レジーム判定（bull / neutral / bear）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / executions）スキーマの初期化ユーティリティ
- News Collector：RSS 取得時の SSRF 対策、URL 正規化、トラッキングパラメータ除去

---

## 必要条件

- Python 3.10 以上
- 外部ライブラリ（主なもの）:
  - duckdb
  - openai (OpenAI の公式 SDK)
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI API）

推奨: 仮想環境（venv / poetry / pipenv 等）を利用してください。

---

## セットアップ手順

1. リポジトリをクローン / パッケージを展開
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   実プロジェクトでは requirements.txt / pyproject.toml を用意してインストールしてください。

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD ではなくパッケージの位置からプロジェクトルートを探索）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 必須の environment variables（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（score_news / regime 判定で使用）
   - KABU_API_PASSWORD: kabu ステーション API 用パスワード（発注等で使用）
   - そのほか任意:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/...）

サンプル .env（最低限）:
```
JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
OPENAI_API_KEY=あなたの_openai_api_key
KABU_API_PASSWORD=あなたの_kabu_api_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な API と実例）

以下は Python REPL やスクリプトから呼ぶ例です。事前に .env を配置しておくか、環境変数を設定してください。

- DuckDB 接続の作成例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（カレンダー・株価・財務・品質チェックを含む）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア（ai_scores への書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数か引数で指定
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれる
```

- ファクター計算（例：モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
# mom は各銘柄の辞書リスト
```

- 監査ログ DB の初期化（監査用 DuckDB を作成してスキーマを初期化）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブル(signal_events, order_requests, executions) とインデックスが作成される
```

- News Collector の RSS 取得（単体）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。API キーが必要です。
- ETL は J-Quants API を呼び出します。JQUANTS_REFRESH_TOKEN が必須です。
- DuckDB のテーブルスキーマはプロジェクト仕様に基づいている前提です（初期スキーマの作成ユーティリティが別に用意されている想定）。

---

## 提供されているモジュール（概要）

- kabusys.config
  - 環境変数管理、.env 自動読み込み、settings オブジェクト
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存関数）
  - pipeline: ETL パイプライン（run_daily_etl など）
  - news_collector: RSS 取得と raw_news 保存前処理
  - calendar_management: 市場カレンダー周りのユーティリティ（営業日判定等）
  - quality: データ品質チェック群
  - stats: zscore_normalize 等の汎用統計ユーティリティ
  - audit: 監査ログスキーマ初期化ユーティリティ
- kabusys.ai
  - news_nlp: ニュースの銘柄別センチメントスコアリング（score_news）
  - regime_detector: ETF + マクロニュースを用いた市場レジーム判定（score_regime）
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (ETLResult re-export)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/, strategy/, execution/ など（パッケージ API に含める想定）

この README はコードベースから主要ファイルを抜粋してまとめた概要です。実運用では、DB スキーマの初期化・マイグレーション、ロギング設定、資格情報の安全な保管（秘密管理）、および監視・アラート設定を整備した上で利用してください。

---

## 開発 / テストのヒント

- 自動で .env を読み込む機能は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テストなどで利用）。
- OpenAI 呼び出しや外部 API をテスト時に差し替えるため、各モジュールでは内部の _call_openai_api や _urlopen 等をモックしやすい設計になっています。unittest.mock.patch で差し替えてテストしてください。
- DuckDB を :memory: にすれば一時 DB でのユニットテストが可能です（audit.init_audit_db も ":memory:" をサポート）。

---

必要であれば README に以下を追加できます：
- requirements.txt / pyproject.toml のサンプル
- DB スキーマ作成スクリプト（raw_prices 等のテーブル定義）
- CI / GitHub Actions 用のワークフロー例
- 詳細な API リファレンス（関数別の引数説明・戻り値）