# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。  
ETF・株価・ニュース・財務データの ETL、ニュースの LLM ベースセンチメント分析、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

本 README ではプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からのデータ取得（株価日足、財務、上場銘柄情報、JPX カレンダー）
- DuckDB を用いた差分 ETL（冪等保存・品質チェック付き）
- RSS ニュース収集と記事前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄別）とマクロセンチメント評価
- ETF（1321）ベースの移動平均乖離と LLM マクロセンチメントの合成による「市場レジーム判定」
- 研究用ファクター・特徴量探索ユーティリティ（モメンタム、ボラティリティ、バリュー、IC 等）
- 監査ログスキーマ（signal / order_request / execution）と初期化ユーティリティ
- 環境設定管理（.env 自動ロード、必須鍵チェック、実行環境フラグ）

設計上の特徴：
- ルックアヘッドバイアス防止のため日時参照やクエリ条件に注意（target_date ベース）
- DuckDB 上で SQL と Python を組み合わせて効率的に処理
- API 呼び出しに対する冪等性、リトライ、レート制御、フェイルセーフ設計

---

## 機能一覧

主なモジュールと機能（抜粋）:

- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）／設定オブジェクト（settings）
  - 必須環境変数チェック

- kabusys.data
  - jquants_client: J-Quants API クライアント（認証、ページング、保存関数）
  - pipeline: ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）と ETLResult
  - news_collector: RSS 収集・前処理・保存ユーティリティ（SSRF対策、gzip上限）
  - calendar_management: 市場カレンダー管理（営業日判定、next/prev 等）と calendar_update_job
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - stats: zscore_normalize 等の汎用統計ユーティリティ
  - audit: 監査ログスキーマ作成・初期化（init_audit_schema / init_audit_db）

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）200日 MA 乖離 + マクロ LLM 評価で市場レジーム判定（market_regime に保存）

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats から zscore_normalize を利用可能

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子などを使用）
- インターネット接続（J-Quants / OpenAI / RSS）

1. リポジトリをクローンまたはプロジェクトディレクトリへ移動

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最小限の依存例:
     - duckdb
     - openai (OpenAI SDK)
     - defusedxml
   - 例:
     pip install duckdb openai defusedxml

   プロジェクトを editable インストール（セットアップ済みの setup/pyproject があれば）:
     pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（ただしテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（このプロジェクトで参照される主なもの）:

     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL     : kabuステーション API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN       : Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
     - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 実行時に省略可）
     - DUCKDB_PATH           : DuckDB ファイルパス（省略可、デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite（監視用）パス（省略可、デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : 実行環境 ("development" | "paper_trading" | "live")（省略可、デフォルト development）
     - LOG_LEVEL             : ログレベル ("DEBUG","INFO",...)（省略可）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

---

## 使い方（基本例）

以下はライブラリ API を直接利用する簡単な例です。実運用ではエラー処理や認証周りを適切に行ってください。

1. DuckDB 接続を作って日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュースセンチメントをスコアして ai_scores テーブルに保存

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
# conn は DuckDB 接続、OPENAI_API_KEY は環境変数か api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み銘柄数:", n_written)
```

3. 市場レジーム判定を実行して market_regime に書き込む

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4. 監査ログ用 DuckDB を初期化する

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は必要なテーブルとインデックスを作成します
```

5. 市場カレンダー操作例

```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print("is trading:", is_trading_day(conn, d))
print("next trading day:", next_trading_day(conn, d))
```

注意点:
- score_news / score_regime など OpenAI を呼ぶ処理は、API キーとレート制限に注意（本実装はリトライと一定のバックオフを実装）。
- J-Quants API 呼び出しは rate limiter と 401 -> refresh の処理を含みます。JQUANTS_REFRESH_TOKEN を設定してください。
- ETL / 保存処理は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar 等）が事前に作られていることを前提とする箇所があります。スキーマ初期化用のユーティリティが別にある想定です（ここに含まれたコード群は保存用関数を実装済み）。

---

## ディレクトリ構成

主要なファイル・モジュール構成（簡易表示）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # ニュースの LLM スコアリング（score_news）
    - regime_detector.py    # ETF + マクロ LLM を合成した市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py           # ETL パイプライン、run_daily_etl 等、ETLResult
    - jquants_client.py     # J-Quants API クライアント（fetch_* / save_*）
    - news_collector.py     # RSS 収集、前処理、SSRF 対策
    - calendar_management.py# 市場カレンダー管理、営業日判定
    - quality.py            # データ品質チェック
    - stats.py              # zscore_normalize 等の統計ユーティリティ
    - audit.py              # 監査ログスキーマ初期化（signal / order_requests / executions）
    - pipeline.py
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py    # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py# calc_forward_returns / calc_ic / factor_summary / rank
  - monitoring/ (パッケージ一覧に示されているが詳細は実装ベースで追加可能)
  - execution/, strategy/, monitoring/ (README 用語では主要サブシステムとして存在を想定)

（注）実際のリポジトリには上記以外に pyproject.toml / requirements.txt / scripts 等が存在する場合があります。

---

## 注意事項・トラブルシューティング

- 環境変数が不足していると Settings のプロパティで ValueError が発生します。必須の鍵は .env に設定してください。
- .env はプロジェクトルート（.git または pyproject.toml を探索して決定）を基準に自動読み込みされます。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは料金・レートに関係するため、テスト時は API キーを限定して使用してください。score_news / regime_detector では失敗時はフェイルセーフにより 0.0 などで継続する設計です。
- J-Quants API については利用規約・レート制限を遵守してください。get_id_token / _request は 401 リフレッシュと指数バックオフ、固定間隔レート制御を実装済みです。
- DuckDB のバージョン差異（executemany の挙動など）があるため、コード内に互換処理が含まれています。DuckDB をアップデートする場合は互換性に注意してください。

---

もし README に追加したい内容（例: CI / テスト実行方法、スキーマ定義ファイル、サンプル .env.example、より詳しい API リファレンス等）があれば教えてください。必要に応じてサンプルコマンドやスクリプトの記載を追加します。