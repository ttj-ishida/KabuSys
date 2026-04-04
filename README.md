# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。J-Quants API や RSS、OpenAI（LLM）を組み合わせてデータ収集・ETL・品質検査・特徴量計算・市場レジーム判定・監査ログ管理などを行うためのモジュール群を提供します。

主な用途はデータパイプラインの構築、研究用ファクター計算、ニュース由来の AI スコアリング、ならびに取引監査ログの初期化・管理です。

---

## 主な機能

- データ取得 / ETL
  - J-Quants から株価（日足）、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル・ページネーション対応・トークン自動リフレッシュ・レート制御・冪等保存
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合を検出するチェック群
- ニュース収集 & NLP（OpenAI）
  - RSS 収集（SSRF 対策、トラッキング除去、内容前処理）
  - 銘柄ごとにニュースをまとめ、LLM によりセンチメント（ai_scores）を算出・書き込み
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成して日次で 'bull' / 'neutral' / 'bear' 判定
- 研究用モジュール
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリ、Zスコア正規化
- 監査ログ（オーディット）スキーマ
  - signal → order_request → execution の階層で永続的にトレーサビリティを保持する監査テーブルを DuckDB に作成・初期化

---

## 動作要件（推奨）

- Python >= 3.10（typing の | 演算子を使用）
- 必要なパッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

インストール例（仮の requirements）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

※ 実際の requirements.txt はプロジェクトに合わせて用意してください。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール
   ```bash
   git clone <repo-url>
   cd <repo-directory>
   pip install -e .
   ```

2. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（CWD ではなくソースファイル位置からプロジェクトルートを特定します）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

3. 必須環境変数（代表例）
   - J-Quants
     - `JQUANTS_REFRESH_TOKEN`（必須）
   - OpenAI
     - `OPENAI_API_KEY`（news_nlp / regime_detector を利用する場合）
   - kabuStation（発注等の別機能）
     - `KABU_API_PASSWORD`（必要に応じて）
   - その他（任意・デフォルトあり）
     - `KABU_API_BASE_URL`（デフォルト: http://localhost:18080/kabusapi）
     - `DUCKDB_PATH`（デフォルト: data/kabusys.duckdb）
     - `SQLITE_PATH`（監視 DB、デフォルト: data/monitoring.db）
     - `KABUSYS_ENV`（development / paper_trading / live、デフォルト: development）
     - `LOG_LEVEL`（DEBUG/INFO/...、デフォルト: INFO）

   例 `.env`（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret
   ```

---

## 使い方（代表的な利用例）

以下は Python から直接呼び出す簡単な例です。

- DuckDB 接続の作成と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（AI）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数にある場合は api_key を省略可
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで監査用テーブルとインデックスが作成されます
  ```

- J-Quants の id_token を明示的に取得する（必要に応じて）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
  ```

---

## よく使う API / 関数一覧

- Data / ETL
  - kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL（calendar, prices, financials, quality checks）
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.pipeline.run_financials_etl(...)
  - kabusys.data.pipeline.run_calendar_etl(...)

- J-Quants クライアント
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.fetch_financial_statements(...)
  - kabusys.data.jquants_client.fetch_market_calendar(...)
  - kabusys.data.jquants_client.save_daily_quotes(...)
  - kabusys.data.jquants_client.save_financial_statements(...)
  - kabusys.data.jquants_client.save_market_calendar(...)

- ニュース & AI
  - kabusys.data.news_collector.fetch_rss(...)
  - kabusys.ai.news_nlp.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)

- 研究用
  - kabusys.research.calc_momentum(...)
  - kabusys.research.calc_value(...)
  - kabusys.research.calc_volatility(...)
  - kabusys.research.calc_forward_returns(...)
  - kabusys.research.calc_ic(...)
  - kabusys.data.stats.zscore_normalize(...)

- 監査ログ
  - kabusys.data.audit.init_audit_schema(...)
  - kabusys.data.audit.init_audit_db(...)

---

## 実運用上の注意

- 自動 .env ロード
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を基準）を探索し `.env` / `.env.local` を読み込みます。テストなどで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Look-ahead Bias（将来情報利用）対策
  - 多くの関数は内部で datetime.today()/date.today() を直接参照しない設計です。呼び出し側が明示的に target_date を渡すことを推奨します。
- エラー・フェイルセーフ
  - LLM 呼び出しや外部 API 呼び出しで失敗した場合、システムは多くの箇所で例外を上位に投げずにフォールバック（0 スコアやスキップ）する設計です。重要処理では戻り値やログを確認してください。
- レート制御とリトライ
  - J-Quants クライアントはレートリミット（120 req/min）・リトライ・401 時の自動トークン更新などを内包しています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — 環境変数 / 設定読み込みロジック（自動 .env ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリング（ai_scores への保存ロジック）
    - regime_detector.py — 市場レジーム判定（ETF 1321 MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理（is_trading_day, next_trading_day 等）
    - news_collector.py — RSS 収集・前処理・raw_news 保存ロジック
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 汎用統計（zscore_normalize）
    - audit.py — 監査ログスキーマ定義・初期化（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等ファクター計算
    - feature_exploration.py — forward returns, IC, 統計サマリ等

（上記は主要ファイルの抜粋です。実際のプロジェクトではさらに補助モジュールがある場合があります）

---

以上がこのコードベースの概要および導入・利用方法の要点です。README に追記して欲しい項目（例: 実行スクリプト、CI 設定、サンプル .env.example、開発ルールなど）があれば教えてください。