# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注／約定トレーサビリティ）などを提供します。

---

## 概要

KabuSys は日本株のデータパイプラインとリサーチ・自動売買基盤のためのモジュール群です。主な目的は次のとおりです。

- J-Quants API からの株価・財務・市場カレンダー等の取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（銘柄別 ai_score）とマクロセンチメントの評価
- 市場レジーム（bull / neutral / bear）の日次判定（ETF MA とマクロセンチメントの合成）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査テーブル（signal → order_request → executions のトレース）を持つ DuckDB 初期化支援

設計上の特徴として、ルックアヘッドバイアス回避のため日付参照を明示的な target_date に依存させる方針、API 呼び出しの冗長性対策（リトライ / バックオフ / レートリミット）、DuckDB を使った冪等保存の実装などがあります。

---

## 機能一覧

- data
  - ETL（daily ETL / prices / financials / calendar）
  - J-Quants クライアント（取得・保存・トークンリフレッシュ・レート制御）
  - market calendar 管理（営業日判定・next/prev/get）
  - news_collector（RSS 取得、前処理、SSRF 対策）
  - quality（欠損・スパイク・重複・日付整合性チェック）
  - stats（z-score 正規化 等）
  - audit（監査ログ DDL / 初期化ユーティリティ）
- ai
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄別ニュースセンチメントを ai_scores に書込み
  - regime_detector.score_regime(conn, target_date, api_key=None): 市場レジームを market_regime に書込み
- research
  - ファクター算出（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - Settings（環境変数から設定を取得、.env 自動読み込みの仕組み）

---

## セットアップ

前提: Python 3.10+ を想定（型ヒントに union 型等を利用）。実際の最小要件はプロジェクト運用方針に合わせて調整してください。

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要なライブラリ（例）
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   > 本リポジトリに requirements.txt / pyproject.toml があればそれに従ってください。

3. パッケージをローカルインストール（開発時）
   - プロジェクトルート（pyproject.toml がある場所）で:
     - pip install -e .

4. 環境変数設定
   - プロジェクトルートの .env / .env.local を自動読み込みします（config モジュール）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の主な環境変数（config.Settings より）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（必要に応じて）
- SLACK_BOT_TOKEN — Slack通知用（必要に応じて）
- SLACK_CHANNEL_ID — Slack チャネル ID
- OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時）
- その他（任意）: DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等

例: .env のサンプル
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env の読み込みについて:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env を自動読み込みします。
- .env.local が存在すれば .env の設定を上書きします（OS 環境変数は保護されます）。
- export KEY=val、クォート、インラインコメントなどの一般的な .env 構文に対応しています。

---

## 使い方（主要な利用例）

以下は代表的な Python からの利用例です。実行前に必要な環境変数を設定しておいてください。

1) DuckDB 接続と日次 ETL の実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path 型でデフォルト data/kabusys.duckdb
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄別）を生成
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {count}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) ファクター計算（例: momentum）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
print(len(records))
```

5) 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 別ファイルに監査専用 DB を作る場合:
audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" 可能
```

6) RSS フィード取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
# raw_news テーブルへ保存するロジックは環境に依存します（ETL の pipeline 側で整備）
```

注意:
- ai モジュール（news_nlp / regime_detector）は OpenAI の JSON mode を利用する設計です。API キーの設定と利用制限にご注意ください。
- ETL や AI 呼び出しはネットワークを使うため、実行環境のネットワーク / API 利用制限を確認してください。

---

## 主要 API（関数）早見

- data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, ... ) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl
- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- data.news_collector
  - fetch_rss(url, source, timeout=30)
- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None)
- data.audit
  - init_audit_db(db_path) / init_audit_schema(conn)
- ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（src/kabusys 以下、抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - pipeline.py
      - jquants_client.py
      - news_collector.py
      - quality.py
      - stats.py
      - calendar_management.py
      - audit.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py

各モジュールは責務ごとに分割されており、ETL / データ品質 / ニュース処理 / AI スコアリング / リサーチが独立して呼び出せる設計です。

---

## 設定と運用の注意点

- 環境（KABUSYS_ENV）は "development" / "paper_trading" / "live" のいずれか。settings.is_live などのフラグで分岐できます。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは外部 API に依存します。失敗時のフォールバックやリトライの挙動は各モジュール内に実装されていますが、API 利用コストやレート制限には注意してください。
- J-Quants API はレート制御と 401 リフレッシュ処理を組み込んでいます。get_id_token 等でトークン管理が行われます。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を基本としていますが、ETL 実行時はバックアップやロック方針を運用ポリシーに合わせて設計してください。
- ニュース収集では SSRF 対策（ホスト検査、リダイレクト検査）と受信サイズ制限を実装しています。外部 RSS を追加する場合は信頼できるソースに限定してください。

---

## 貢献・拡張

- モジュールは比較的分離されているため、新しい ETL 対象、ニュースソース、AI モデルの差し替え、研究アルゴリズムの追加などが容易です。
- テストはネットワーク呼び出しをモックして行う方針が推奨されます（各モジュール内で外部呼び出しを差し替えるフックが用意されています）。

---

不明点や README に追加したい実行例・運用手順があれば教えてください。必要に応じてコマンド例やサンプル .env.example を追記します。