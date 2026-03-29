# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

## 主要な特徴
- J-Quants API 経由の株価・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた ETL パイプライン（差分更新、バックフィル、品質チェック）
- ニュース収集（RSS）とニュース単位 / 銘柄単位の前処理、OpenAI によるセンチメント評価（JSON mode）
- 市場レジーム判定（ETF 1321 の 200 日 MA とマクロニュースの LLM センチメントを合成）
- 研究用途のファクター計算・特徴量探索ユーティリティ（モメンタム・バリュー・ボラティリティ等）
- 監査（audit）テーブル群の初期化ユーティリティ（シグナル→発注→約定のトレーサビリティ）
- 環境変数 / .env による設定管理（自動読み込み対応、上書きルールあり）

---

## 機能一覧（抜粋）
- データ取得 / 保存
  - jquants_client.fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - jquants_client.save_daily_quotes, save_financial_statements, save_market_calendar
- ETL
  - data.pipeline.run_daily_etl (日次 ETL の統合エントリポイント)
  - 個別: run_prices_etl, run_financials_etl, run_calendar_etl
- 品質チェック
  - data.quality.run_all_checks（欠損、重複、スパイク、日付不整合）
- ニュース処理 / NLP
  - data.news_collector.fetch_rss（RSS 取得・前処理）
  - ai.news_nlp.score_news（銘柄別ニュースセンチメントの取得・ai_scores への書込）
- 市場レジーム
  - ai.regime_detector.score_regime（日次レジーム判定と market_regime への書込）
- 研究（Research）
  - research.calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize
- 監査ログ
  - data.audit.init_audit_schema / init_audit_db（監査用テーブルの初期化）

---

## セットアップ手順

前提: Python 3.9+（typing の一部機能を使用）。プロジェクトルートが .git または pyproject.toml で識別できる構成を想定します。

1. 仮想環境を作成・有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .\.venv\Scripts\activate
     ```

2. 必要パッケージをインストール（推奨）
   - 代表的な依存パッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。）

3. 環境変数の準備
   - プロジェクトルートに `.env` と（必要なら）`.env.local` を置くと、ライブラリ起動時に自動で読み込まれます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時などに有用）。

必須となる主な環境変数（用途とキー名）
- J-Quants（データ取得）
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- kabuステーション（発注等）
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL（省略時: http://localhost:18080/kabusapi）
- Slack（通知）
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- OpenAI
  - OPENAI_API_KEY（ai.news_nlp.score_news / ai.regime_detector.score_regime で使用）
- DB パス（任意デフォルトあり）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用: data/monitoring.db）
- その他
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL（DEBUG/INFO/...）

例: .env（最小）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下は DuckDB 接続を用いて ETL / NLP / レジーム判定 / 監査初期化を行う簡単な例です。

- 共通準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（対象日分）をスコアして ai_scores テーブルへ書き込む
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  print(f"written: {written}")
  ```

- 市場レジーム判定を実行し market_regime テーブルへ書き込む
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化（専用 DB を作る例）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで監査用テーブル（signal_events, order_requests, executions 等）が作成されます
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  # recs は各銘柄ごとの dict リスト (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)
  ```

注意:
- score_news / score_regime は OpenAI API を呼び出します。APIキーは引数 api_key で渡すか環境変数 OPENAI_API_KEY を使用します。
- ETL / 保存系は DuckDB 内のテーブルスキーマが前提です。初期スキーマ生成はプロジェクトの別モジュール（schema 初期化など）を利用してください。

---

## 主要モジュールとディレクトリ構成

リポジトリの主要なファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント取得（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロ NLP 合成）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 / 保存 / 認証 / レート制御）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL インターフェース再エクスポート（ETLResult）
    - news_collector.py      — RSS 取得・前処理・保存
    - calendar_management.py — 市場カレンダー管理（営業日判定 / calendar_update_job）
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログテーブル初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - research/*, ai/*, data/* の内部実装はそれぞれ注釈付きで堅牢性・フォールバック・ルックアヘッドバイアス排除を考慮して実装されています。

---

## 注意事項 / 運用上のポイント
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを無効にできます。
- OpenAI 呼び出し時はレスポンスのバリデーション・リトライが組み込まれていますが、API コストとレート制限に注意してください。
- jquants_client は API レート（120 req/min）や 401 リフレッシュなどに対応しています。ID トークンは内部キャッシュされます。
- ETL・保存処理は冪等性を重視しており、DuckDB 側で ON CONFLICT を利用した更新を行います。
- DuckDB テーブルスキーマや初期化処理は別途用意が必要です（schema 初期化スクリプトなど）。audit.init_audit_db は監査用スキーマを作成するユーティリティを提供します。

---

## 開発 / 貢献
- コードのスタイルやテスト、CI の基準はプロジェクトの CONTRIBUTING や pyproject.toml に従ってください（本 README には記載がないため、プロジェクトルートを参照してください）。
- ユニットテストや外部 API 呼び出しをモックするために、モジュール内で外部呼び出しを分離（例えば _call_openai_api をモック差し替え）しています。テストはこの仕組みを利用して実装してください。

---

必要であれば、README に以下の追加を作成できます：
- 完全な .env.example（各変数の説明とサンプル値）
- DuckDB スキーマ初期化スクリプト例
- よくあるトラブルシュート（OpenAI レスポンスエラー、J-Quants 認証エラー等）
- CLI / 管理コマンドの実行例

どの追加情報が必要か教えてください。