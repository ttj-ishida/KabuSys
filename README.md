# KabuSys

日本株の自動売買・データプラットフォーム用ライブラリ / モジュール群です。  
ETL（J-Quants）・ニュース収集・ニュースNLP（OpenAI）・市場レジーム判定・ファクター計算・監査ログ等の主要処理を含みます。

---

## プロジェクト概要

KabuSys は日本株の運用・研究ワークフローを支援する内部ライブラリです。  
主な目的は以下です。

- J-Quants API からのデータ収集（株価・財務・市場カレンダー）
- DuckDB を用いたデータ格納・ETL（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（銘柄別 AI スコア）とマクロセンチメントを用いた市場レジーム判定
- 研究用途のファクター計算・特徴量探索ユーティリティ
- 発注・約定フローのための監査ログ（監査テーブルの初期化・管理）
- 設定管理（.env / 環境変数読み込み、Settings オブジェクト）

設計上の共通方針として、ルックアヘッドバイアス対策（時間に依存しない設計）、冪等性、外部 API の堅牢なリトライ制御、DuckDB を用いたローカル永続化が採用されています。

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env または環境変数から設定を読み込む（自動ロードありをデフォルト）
  - settings: J-Quants、kabu API、Slack、DB パス、環境フラグ等のプロパティ

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存ロジック、レートリミット、リトライ、トークン自動更新）
  - pipeline / etl: 日次 ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS フィード収集・前処理・raw_news への保存ロジック
  - calendar_management: JPX カレンダー管理・営業日判定・更新ジョブ
  - quality: データ品質チェック（欠損、重複、スパイク、将来日付等）
  - stats: 汎用統計ユーティリティ（zscore 正規化）
  - audit: 監査ログ（signal_events / order_requests / executions）DDL と初期化ユーティリティ

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出 → ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）MA とマクロセンチメントを合成した市場レジーム判定

- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算（prices_daily / raw_financials 利用）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー、rank（同順位平均処理）

---

## 前提 / 必要環境

- Python 3.10 以上（PEP 604 の union 型表記等を利用）
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

パッケージの厳密な requirements.txt はプロジェクトルートに用意してください。最低限は次のようにインストールできます（例）:

pip install duckdb openai defusedxml

※ 実際のプロジェクトでは setuptools/poetry による依存管理を行ってください。

---

## 環境変数（主要）

主に以下の環境変数を利用します（settings から取得）：

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API の base URL（省略可）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL — ログレベル ("DEBUG"|"INFO"|...)

自動で .env/.env.local をロードする仕組みがあり、モジュール起点でプロジェクトルート（.git または pyproject.toml を基準）を探索してロードします。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のサンプル（プロジェクトに .env.example を置く運用を想定）:

JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンしてチェックアウト

2. 仮想環境を作成・有効化（任意）

python -m venv .venv
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows

3. 必要パッケージをインストール

pip install -e .    # パッケージが setup 配下にある想定
# あるいは最低限
pip install duckdb openai defusedxml

4. .env を作成（プロジェクトルート）

.env に上記の必須キーを設定してください（JQUANTS_REFRESH_TOKEN 等）。

5. DuckDB データベース準備（初回はモジュール内の ETL がテーブルを作成する想定）  
   監査ログ専用 DB を初期化する場合は sample を参考に init_audit_db を実行します（下記参照）。

---

## 使い方（主な例）

以下は Python スクリプトや REPL からの利用例です。

- DuckDB 接続の作成

from pathlib import Path
import duckdb
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))

- 日次 ETL 実行（run_daily_etl）

from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- ニュースセンチメントスコア算出（銘柄別）

from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定（MA + マクロセンチメント）

from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))

- 研究系関数（ファクター算出）

from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))

- 将来リターン / IC / 統計サマリー

from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

fwd = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "ma200_dev"])

- 監査ログ DB 初期化

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# 監査テーブルが作成され、UTC タイムゾーンが設定されます

- RSS フィード取得（ニュース収集の一部）

from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# 取得された記事は NewsArticle 型（id, datetime, title, content, url）

注意点:
- score_news / score_regime の OpenAI 呼び出しは API キー（OPENAI_API_KEY）を必要とします。api_key を関数引数で直接渡すことも可能です。
- J-Quants API 呼び出しは JQUANTS_REFRESH_TOKEN を使って id_token を取得します。
- ETL / 保存処理は DuckDB テーブルの存在を前提としています。スキーマは pipeline や jquants_client の処理で作成される／または別実装の schema 初期化を行ってください。

---

## 注意・設計上の重要事項

- ルックアヘッドバイアス防止: ほとんどのモジュールが内部で date.today() を直接参照しない設計です（target_date を明示して処理する）。
- 冪等性: J-Quants 保存関数や監査テーブル初期化は冪等性を考慮（ON CONFLICT 等）して実装されています。
- フェイルセーフ: 外部 API（OpenAI, J-Quants）障害時はリトライやフォールバック（ゼロスコアなど）を行い、例外を上位に伝播しないケースがあります（ログ出力優先）。
- セキュリティ: news_collector は SSRF 対策、レスポンスサイズ制限、defusedxml による XML パース保護などを備えています。

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイルを抜粋）

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
    - etl.py
    - calendar_management.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
    - (他: 必要に応じて clients / utils 等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py

上記以外にもモジュール分割やユーティリティが含まれますが、主要な責務は上記に整理されています。

---

## テスト・開発メモ

- OpenAI への実際の API コールを伴う関数は、テスト時に内部の _call_openai_api を patch / mock して差し替えてテスト可能です（news_nlp, regime_detector それぞれ独立した実装を持つため、相互依存のモック共有を避けやすい設計）。
- .env 自動ロードはパッケージインポート時に有効になります。テストから自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB に対する executemany の空リストバインドに注意（コード内でチェック済み）。

---

## サポート / 追加情報

この README はコードベースの主要機能と利用方法を説明する簡易ドキュメントです。  
細かい API 引数や返り値の仕様（例: 各テーブルのスキーマや ETLResult のフィールド）はソースの docstring を参照してください。

必要であれば、以下を追記できます：
- インストール用の requirements.txt / pyproject.toml 例
- 各 DB スキーマ定義（CREATE TABLE）や初期化スクリプト
- CI / テスト実行方法
- 運用時の監視・運用手順（Slack 通知等）

ご希望があれば追加でセクションを展開します。