# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算・研究ユーティリティ、監査ログ（発注・約定トレーサビリティ）などを含むモジュール群を提供します。

---

## 主な特徴
- J-Quants API 経由での差分 ETL（株価日足、財務、JPX カレンダー）を実装（ページネーション・リトライ・レート制御済み）
- raw_news の RSS 収集と記事前処理（SSRF / トラッキングパラメータ除去・安全対策）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別の ai_score / マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ）と研究支援ユーティリティ（将来リターン・IC・統計サマリ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ用スキーマと初期化ユーティリティ（シグナル→発注→約定 を UUID で追跡）
- DuckDB を中心とした軽量なオンディスク DB 設計（監査用 DB 別途初期化可能）

---

## 機能一覧（抜粋）
- data/
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（日足・財務・カレンダー・上場銘柄情報）
  - カレンダ管理: is_trading_day / next_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: fetch_rss / ニュース前処理・保存ロジック
  - データ品質: run_all_checks（missing / spike / duplicates / date_consistency）
  - 監査ログ: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: MA200 乖離とマクロセンチメントで市場レジーム判定
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理: kabusys.config.settings（.env 自動読み込み・環境変数解決）

---

## 要件（例）
- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ以外の依存は setup 時に確認してください）

例（pip でのインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発用にパッケージを編集しながら使う場合:
pip install -e .
```

---

## セットアップ手順

1. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージのインストール
   ```bash
   pip install duckdb openai defusedxml
   # またはプロジェクトが配布されているなら:
   pip install -e .
   ```

3. 環境変数設定 (.env)
   - プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に `.env` を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL 用）
     - SLACK_BOT_TOKEN: Slack 通知（使用する場合）
     - SLACK_CHANNEL_ID: Slack チャネル ID（使用する場合）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能使用時）
     - OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector 使用時）
   - 任意 / デフォルト
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で自動 .env 読み込みを無効化
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - LOG_LEVEL: INFO 等（デフォルト: INFO）

   - サンプル .env 内容例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```

---

## 使い方（代表的な呼び出し例）

- DuckDB 接続を作成して ETL を実行する（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ai.score_news（ニュースセンチメントを計算して ai_scores に保存）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")
  # OPENAI_API_KEY は環境変数または api_key 引数で指定可能
  ```

- ai.regime_detector.score_regime（市場レジーム判定）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成
  ```

- 設定オブジェクト参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.env, settings.log_level)
  ```

注意:
- OpenAI を呼ぶ関数は api_key 引数で明示的に渡すこともできます（テストや分離用）。
- ライブラリは内部でルックアヘッドバイアスを避ける設計（関数は内部で date.today() を参照しない等）になっています。バックテスト等で使用する際は target_date を明示してください。

---

## 主要ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（銘柄別）スコアリング
    - regime_detector.py  — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch/save）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py   — RSS 収集・前処理
    - quality.py          — データ品質チェック
    - stats.py            — 汎用統計（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化
    - etl.py              — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py  — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・summary 等
  - other top-level modules:
    - execution/ monitoring/ strategy/ …（パッケージ公開用 __all__ に含まれるが、ここに収録される想定のモジュールを追加可能）

---

## 注意事項 / 設計上のポイント
- .env の自動読み込みはプロジェクトルート（.git あるいは pyproject.toml）を基準に行います。テストで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはリトライやフォールバック（失敗時はスコア 0.0 など）を備えていますが、API キーと使用料には注意してください。
- DuckDB の一部バージョンでは executemany に空リストを渡せない制約を考慮した実装になっています。
- ニュース収集では SSRF や XML 攻撃、巨大レスポンス対策（defusedxml、最大バイト数チェック、ホストのプライベートアドレス拒否）を実装しています。
- 監査ログは削除しない前提で設計され、order_request_id を冪等キーとして再送防止を実現しています。

---

もし README に追加したい使い方（CLI の例、CI 設定、Dockerfile、サンプル .env.example のテンプレート等）があればお知らせください。必要に応じて追記します。