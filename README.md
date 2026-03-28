# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants や RSS / LLM（OpenAI）を用いたデータ収集・品質チェック・特徴量計算・AI ニューススコアリング・市場レジーム推定・監査ログ等のユーティリティを提供します。

---

## プロジェクト概要

KabuSys は日本株のバックテスト／運用パイプライン向けに設計されたモジュール群をまとめたライブラリです。主な目的は次の通りです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL
- RSS ニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントの銘柄別集約スコアリング
- マーケットレジーム判定（ETF MA とマクロニュースの組合せ）
- ファクター計算（モメンタム／バリュー／ボラティリティ等）とリサーチ用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース用テーブル定義・初期化）
- DuckDB を中心とした永続化（冪等保存を基本設計）

設計上の共通方針として、ルックアヘッドバイアスを防ぐ設計（内部で date.today()/datetime.today() を不用意に参照しない等）、外部 API 呼び出しのリトライとフェイルセーフ、冪等性を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save / 認証トークン管理、レートリミット、リトライ）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - ニュース収集（RSS の安全取得、前処理、raw_news への保存ロジック）
  - 品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ初期化（監査用テーブル・インデックス作成、init_audit_db）
  - 共通統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）と Settings（環境設定）

---

## 要件

- Python 3.10+
- 必要な Python パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

パッケージは pyproject.toml / requirements.txt がある想定です。開発環境では仮想環境を推奨します。

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得してください。

2. 仮想環境を作成してアクティベート：
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux)
   - .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール：
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements を用意している場合は pip install -r requirements.txt）

4. 環境変数設定：
   プロジェクトルートに .env を置くか、環境変数を直接設定します。config モジュールは自動でプロジェクトルート（.git または pyproject.toml の存在）を検出して `.env` / `.env.local` を読み込みます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   主要な環境変数（代表例）：
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注等で使用）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
   - DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

   .env の例（簡易）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマや監査 DB 初期化はアプリ側で呼び出します（下記参照）。

---

## 使い方（主要なユースケース）

以下はライブラリをインポートして使う最小例です。実運用ではログ設定や例外処理を適切に行ってください。

- 共通準備（接続と設定）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（前日 15:00 JST 〜 当日 08:30 JST の範囲）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {n_written}")
```

- マーケットレジーム判定（ETF 1321 の MA とマクロニュースの組合せ）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB を初期化する（別 DB にすることを推奨）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db("data/audit.duckdb")
# あるいは settings.duckdb_path を使って同一 DB 上に作ることも可能
```

- J-Quants から直接データ取得（低レベル API）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を利用
records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
```

- RSS フィード取得（ニュース収集の単体利用）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点:
- score_news / score_regime は OpenAI API を呼び出すため OPENAI_API_KEY が必要です。API 呼び出しはリトライとフォールバック（失敗時は 0.0 を採用）を組み込んでいますが、API レートやコストに注意してください。
- run_daily_etl は内部で calendar_etl → prices_etl → financials_etl → 品質チェック の順に実行します。各ステップは独立して例外処理され、失敗しても他のステップは継続されます（結果は ETLResult に保存されます）。

---

## 環境変数の自動ロードについて

kabusys.config はプロジェクトルート（.git または pyproject.toml）を探索し、プロジェクトルートの `.env` と `.env.local` を自動で読み込みます。優先順位は:

OS 環境変数 > .env.local > .env

自動ロードを無効にするには環境変数:
```
KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```
を設定してください（テスト等で利用）。

---

## ディレクトリ構成（要約）

以下は主要なモジュールと役割のツリー概略（src/kabusys）です。

- kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLP / score_news)
    - regime_detector.py (市場レジーム判定 / score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、取得・保存関数)
    - pipeline.py (ETL パイプライン・run_daily_etl 等、ETLResult)
    - etl.py (ETLResult の再エクスポート)
    - news_collector.py (RSS 取得・前処理)
    - calendar_management.py (マーケットカレンダー判定／更新ジョブ)
    - quality.py (データ品質チェック)
    - stats.py (z-score 等の統計ユーティリティ)
    - audit.py (監査ログテーブル DDL / 初期化 / init_audit_db)
  - research/
    - __init__.py
    - factor_research.py (モメンタム/ボラティリティ/バリュー等)
    - feature_exploration.py (将来リターン / IC / 統計サマリー)
  - ai/ (前述)
  - その他（strategy, execution, monitoring 等は __all__ に含まれる想定。実装は各モジュール内）

各ファイルの先頭に設計方針や注意点がドキュメントとして記載されています。実際のテーブル名（raw_prices, raw_financials, market_calendar, ai_scores, ai_scores など）やスキーマは各モジュールのコメント・DDL を参照してください。

---

## 開発・テストのヒント

- テスト時に環境変数の自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants の API 呼び出し部分は各モジュール内で _call_openai_api / _urlopen 等を分離しているため、 unittest.mock.patch による差し替えが容易です。
- DuckDB を使ったローカルテストでは ":memory:" を DB パスに指定してインメモリ DB を使用可能です（init_audit_db 等で対応）。

---

## 補足

- セキュリティ: news_collector は SSRF 対策や受信サイズの上限、defusedxml による XML パース保護など多くの防御策を実装していますが、 RSS ソースの信頼性やネイティブ外部依存（ネットワーク経路）には注意してください。
- 本リポジトリは外部 API キーとネットワークアクセスを前提とします。実運用ではキー管理・コスト管理・レート制御を適切に行ってください。

---

必要であれば、README に付けるサンプル .env.example、DB スキーマ初期化手順や具体的な CLI（例: etl を cron から呼ぶ方法）のサンプルも作成できます。どの情報を追加したいか教えてください。