README — KabuSys
===============

概要
----
KabuSys は日本株のデータプラットフォームとリサーチ／自動売買の基盤ライブラリです。  
J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）や、DuckDB を用いた ETL、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ（ファクター計算・特徴量探索）、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

主な目的
- データ収集（J-Quants、RSS ニュース）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュースによる銘柄センチメント評価（OpenAI）
- マーケットレジーム判定（ETF + マクロニュース）
- ファクター計算 / リサーチ用ユーティリティ
- 取引監査ログ用スキーマ（DuckDB）

機能一覧
--------
主要機能の一覧（モジュール名 / 概要）

- kabusys.config
  - 環境変数の自動読み込み（.env, .env.local）
  - 設定取得ヘルパ（J-Quants トークン、kabu API 設定、Slack、DB パス、環境切替等）

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 + DuckDB への保存）
  - pipeline / etl: 日次 ETL（prices / financials / calendar）の差分取得と保存
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector: RSS からニュース収集と前処理（SSRF 対策、サイズ制限）
  - calendar_management: 営業日判定・更新ロジック
  - audit: 取引監査ログテーブル定義と初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore 正規化 など）

- kabusys.ai
  - news_nlp.score_news: OpenAI を用いたニュースセンチメントの銘柄別スコア付与（ai_scores へ書き込み）
  - regime_detector.score_regime: ETF（1321）の MA とニュースセンチメントを合成して市場レジーム判定（market_regime へ書き込み）

- kabusys.research
  - factor_research: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー等

セットアップ
----------
前提
- Python 3.10+（typing の | 演算子などを利用しているため）を推奨
- DuckDB、OpenAI SDK、defusedxml 等の依存ライブラリが必要

例：仮想環境作成と依存インストール（pip）
1. 仮想環境作成・有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt や pyproject.toml があればそちらを利用してください）

環境変数 / .env
- リポジトリのプロジェクトルートに .env/.env.local を置くと自動で読み込まれます（優先順位: OS env > .env.local > .env）。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト等で利用）。
- 必須環境変数（Settings クラスで require されるもの）
  - JQUANTS_REFRESH_TOKEN    — J-Quants リフレッシュトークン
  - KABU_API_PASSWORD        — kabu ステーション API パスワード
  - SLACK_BOT_TOKEN          — Slack Bot Token
  - SLACK_CHANNEL_ID         — Slack Channel ID
- 任意／デフォルト
  - KABUSYS_ENV (development / paper_trading / live) — 実行環境（デフォルト development）
  - LOG_LEVEL (DEBUG/INFO/…) — ログレベル（デフォルト INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化フラグ

.env の簡単な例
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    KABU_API_PASSWORD=your_password
    DUCKDB_PATH=data/kabusys.duckdb

使い方（基本例）
----------------

1) DuckDB 接続を作成して ETL を実行する（デイリー ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメント（ai_scores）を生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} ai_scores")
```

3) 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB を初期化する（独立した監査 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring.db")
# これで監査テーブル（signal_events, order_requests, executions 等）が作成されます
```

5) J-Quants から株価を直接フェッチして保存する（テスト）
```python
from kabusys.data import jquants_client as jq
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2026, 1, 1), date_to=date(2026, 3, 20))
jq.save_daily_quotes(conn, records)
```

注意点 / 設計上の留意事項
- Look-ahead bias を避ける設計（関数は基本的に内部で date.today() を無条件に参照しない、ETL やスコアリングは target_date を明示して実行することを前提）
- OpenAI 呼び出しは API エラー時にフォールバック（例: マクロセンチメント失敗時は 0.0 を返す等）
- news_collector は SSRF / GZip bomb / XML attack 対策を実装
- DuckDB の一部バージョンに依存する制約（executemany の空リスト等）を考慮した実装

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py               — パッケージ初期化、バージョン定義
- config.py                 — 環境変数 / 設定管理（.env 自動ロード含む）

src/kabusys/ai/
- __init__.py
- news_nlp.py               — ニュース NLP スコアリング（score_news）
- regime_detector.py        — マーケットレジーム判定（score_regime）

src/kabusys/data/
- __init__.py
- jquants_client.py         — J-Quants API クライアント + DuckDB 保存関数
- pipeline.py               — ETL パイプライン（run_daily_etl 等）
- etl.py                    — ETL ユーティリティの再エクスポート（ETLResult 等）
- quality.py                — データ品質チェック
- news_collector.py         — RSS 収集・前処理
- calendar_management.py    — 市場カレンダー管理と営業日判定
- stats.py                  — 統計ユーティリティ（zscore_normalize 等）
- audit.py                  — 監査ログスキーマと初期化ヘルパ

src/kabusys/research/
- __init__.py
- factor_research.py        — ファクター計算（momentum/value/volatility）
- feature_exploration.py    — 将来リターン / IC / 統計サマリー 等

補足（開発者向け）
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行います。配布パッケージ化／テスト時に制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- OpenAI の呼び出し部分はテスト容易性を考慮して内部呼び出しを差し替え可能（ユニットテストでモックすることが想定されています）。

ライセンス
----------
（リポジトリに別途 LICENSE があればそちらを参照してください。）

以上。README の内容をプロジェクトの実装・運用ポリシーに合わせて補完・調整してください。必要ならサンプル .env.example や requirements.txt のテンプレートも作成できます。