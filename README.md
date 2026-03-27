# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータストアとして利用し、J-Quants API 等からの ETL、ニュース収集・NLP、LLM を使ったセンチメント評価、ファクター計算、監査ログなどを備えたモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つサブシステム群を提供します。

- データ収集（J-Quants API）と差分 ETL（株価、財務、マーケットカレンダー）
- ニュースの収集と前処理（RSS → raw_news）
- ニュースに対する LLM ベースのセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離 × マクロセンチメント）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / execution）用スキーマと初期化ユーティリティ
- 環境・設定管理（.env 自動読み込みを含む）

設計上の共通方針としては、Look-ahead バイアス回避、冪等性、フェイルセーフ（API失敗でも部分的継続）を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（トークン自動リフレッシュ、レート制御、ページネーション、保存関数）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS → raw_news 前処理、SSRF 対策、gzip 上限など）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize など）
- ai/
  - news_nlp.score_news: 銘柄毎のニュース統合センチメントを OpenAI（gpt-4o-mini）で評価し ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを組み合わせて market_regime を更新
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config.py
  - .env 自動読み込み（プロジェクトルート検出：.git または pyproject.toml）
  - 必須環境変数取得ヘルパ（settings オブジェクト）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに union | を使用しているため少なくとも 3.10 推奨）
- インターネット接続（J-Quants / OpenAI API 用）

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール（例）
   ```bash
   pip install -e .              # パッケージ化されている場合
   pip install duckdb openai defusedxml
   ```
   ※ 実際の requirements.txt / pyproject.toml に従ってください。

3. 環境変数の設定  
   プロジェクトルートの `.env` または `.env.local` に必要なキーを設定します。config モジュールは自動的にプロジェクトルート（.git または pyproject.toml のある場所）を探し、以下の順で読み込みます:
   - OS 環境変数（優先）
   - .env.local（存在すれば上書き）
   - .env（存在すれば読み込み、既存の OS 環境変数は上書きしない）

   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API パスワード（利用する場合）
   - SLACK_BOT_TOKEN — Slack 通知用（利用する場合）
   - SLACK_CHANNEL_ID — Slack チャンネル ID
   - OPENAI_API_KEY — OpenAI API キー（ai.score_* を実行する場合）

   任意:
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動 .env ロードを無効化

4. データベース初期化（監査ログ用の例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は DuckDB 接続。必要に応じてスキーマ初期化やマイグレーションを行ってください。
   ```

---

## 使い方（主要ユースケース例）

以下は簡単な Python スニペット例です。実行前に env を整えてください。

- 日次 ETL を実行する（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を計算して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"wrote {n_written} ai_scores")
  ```

- 市場レジームスコア（1321 MA200 + マクロセンチメント）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- ファクター計算（モメンタム）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  # records は [{ "date": ..., "code": "XXXX", "mom_1m": ..., "ma200_dev": ... }, ...]
  ```

- 監査ログスキーマの初期化（既存 DuckDB に追加）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- RSS フィード取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```
  ※ fetch_rss は記事の正規化・SSRF 検査・サイズチェック等を実装しています。DB への永続化は別関数で行われます（raw_news への保存処理）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール利用時に必須）
- KABU_API_PASSWORD — kabu API パスワード（kabu 実行時）
- SLACK_BOT_TOKEN — Slack ボットトークン（通知）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス
- KABUSYS_ENV — environment (development / paper_trading / live)
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読み込みを無効化

config.Settings を通して settings.jquants_refresh_token 等でアクセスできます。また config モジュールは自動的にプロジェクトルートの .env / .env.local を読み込みます（CWD に依存しない実装）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py — 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + 保存関数
    - pipeline.py — ETL パイプラインと run_daily_etl
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集・前処理（SSRF 対策等）
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - quality.py — データ品質チェック
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — forward returns / IC / summary / rank
  - research/* / ai/* / data/* のその他補助モジュール

各モジュールは DuckDB 接続や API キーを外部から注入できる設計になっており、テストやバッチ処理から直接呼び出して利用できます。

---

## 実運用上の注意

- OpenAI / J-Quants の API 呼び出しには課金やレート制限があります。API キー管理と使用量監視を行ってください。
- LLM 結果のバリデーション・フォールバック（失敗時は 0.0 など）を行う設計ですが、運用では結果を人手で監視する仕組みを併用することを推奨します。
- DuckDB の executemany に関するバージョン依存の挙動（空リスト不可等）に注意しています。運用環境の DuckDB バージョンで動作確認してください。
- 監査ログは削除しない前提の設計です。ディスクサイズ・保管ポリシーを検討してください。

---

もし README に追加したい具体的な実行手順（Docker 化、CI/CD、より詳しい .env.example、SQL スキーマ定義の完全版、テストの実行方法など）があれば教えてください。必要に応じて追記・テンプレートを作成します。