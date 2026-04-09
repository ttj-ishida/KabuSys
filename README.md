# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリセットです。  
DuckDB を中心とした ETL、ニュース収集・NLP スコアリング、ファクター計算、監査ログ（発注・約定追跡）、J-Quants / kabu API クライアントなどを含みます。

## プロジェクト概要
KabuSys は次の機能を統合して、日本株のアルゴリズム運用（データ取得 → 品質チェック → ファクター計算 → シグナル生成 → 発注監査）を支援する Python モジュール群です。  
設計方針として、以下を重視しています。

- Look-ahead bias を避ける日付設計（内部で date.today() 等を直接参照しない）
- DuckDB による高速かつローカルで完結するデータ格納
- 外部 API 呼び出し（J-Quants / OpenAI / RSS 等）は明示的に扱い、リトライ・フェイルセーフ装置を備える
- ETL・品質チェック・監査ログの冪等性を確保

## 主な機能一覧
- データ ETL（J-Quants から株価・財務・マーケットカレンダー取得） — kabusys.data.pipeline.run_daily_etl 等
- データ品質チェック（欠損・重複・スパイク・日付不整合） — kabusys.data.quality
- ニュース収集（RSS）と前処理・SSRF 対策 — kabusys.data.news_collector
- ニュース NLP スコアリング（OpenAI） — kabusys.ai.news_nlp.score_news
- 市場レジーム判定（ETF MA とマクロニュース LLM の合成） — kabusys.ai.regime_detector.score_regime
- ファクター計算（Momentum / Value / Volatility など） — kabusys.research.*
- 統計ユーティリティ（Z スコア正規化など） — kabusys.data.stats.zscore_normalize
- 監査ログスキーマ初期化・監査 DB（signal / order_request / executions） — kabusys.data.audit.init_audit_db / init_audit_schema
- J-Quants API クライアント（レートリミット・トークン自動リフレッシュ・ページネーション対応） — kabusys.data.jquants_client
- 環境設定管理（.env 自動読み込み、必須値チェック） — kabusys.config.settings

## セットアップ手順（開発環境向け）
※以下は一般的な手順例です。プロジェクト独自の requirements.txt がある場合はそちらを使用してください。

1. リポジトリを取得
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実際にはプロジェクト用に `requirements.txt` を用意してください。
   - `openai` は OpenAI API 呼び出し用、`defusedxml` は RSS パースの安全対策、`duckdb` はデータベース用です。

4. 環境変数 / .env ファイル
   - プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に `.env` / `.env.local` を配置すると、自動で読み込まれます（kabusys.config が担当）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（必須・推奨）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
   - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 使用時に必要）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE — paper trading の振る舞い（instant/partial/never/reject）
   - KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")
   - LOG_LEVEL — ログレベル ("DEBUG" / "INFO" / ...)

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   OPENAI_API_KEY=sk-xxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

## 使い方（代表的な呼び出し例）

- DuckDB 接続を作成して ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（OpenAI）でスコア付け
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数で設定済みであれば api_key 引数は不要
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（1321 の MA200 とマクロニュースの LLM 評価を合成）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済み DuckDB 接続を返す
  ```

- 設定値の参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.env, settings.log_level)
  ```

注意点・運用ヒント
- OpenAI 呼び出しは料金が発生します。テスト時はモック（unittest.mock.patch）で _call_openai_api を差し替えてください（news_nlp と regime_detector はそれぞれ独立した内部呼び出し関数を持ちます）。
- J-Quants API はレート制限があるため、jquants_client は内部でスロットリング・リトライ・トークン自動更新を行います。大量取得時は backfill 設定に注意してください。
- run_daily_etl は品質チェック結果（quality_issues）を返します。重大な品質エラーがある場合は運用ポリシーに従ってアラートや処理停止を行ってください。

## 主要モジュール・ディレクトリ構成
（抜粋。src/kabusys 以下に主要モジュールがあります）

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数・設定管理（.env 自動読み込み / 必須変数チェック）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース分類・銘柄別センチメントスコアリング（OpenAI 経由）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース LLM）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存用ユーティリティ含む）
    - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - quality.py — データ品質チェック（欠損、重複、スパイク、日付不整合）
    - news_collector.py — RSS ニュース収集 & 前処理（SSRF 対策）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py — 監査ログテーブル定義・初期化（signal / order_request / executions）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - etl.py — public API の再エクスポート（ETLResult 等）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（Momentum / Value / Volatility 等）
    - feature_exploration.py — 将来リターン・IC 計算・統計サマリー等
  - ai/（上記と同じフォルダ）
  - research/（上記と同じフォルダ）

各ファイルの冒頭に設計方針・引数仕様・戻り値・注意点が注釈されているため、実装を呼び出す際に参照してください。

## 環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- OPENAI_API_KEY — OpenAI 呼び出し用 API キー（news_nlp/regime_detector）
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード
- DUCKDB_PATH — メイン DuckDB ファイルパス（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite
- KABUSYS_ENV — "development" / "paper_trading" / "live"
- LOG_LEVEL — ログレベル
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化

## テスト / モックについて
- OpenAI 呼び出しやネットワーク I/O を行う箇所（news_nlp._call_openai_api、regime_detector._call_openai_api、news_collector._urlopen、jquants_client._request 等）はユニットテストでモック可能です。実装内に差し替えを想定した設計（関数切り出しや patch を想定）があります。
- DuckDB を ":memory:" で使用するとテストが簡単です（kabusys.data.audit.init_audit_db は ":memory:" をサポート）。

## ライセンス・貢献
- この README はコードベースの抜粋に基づく概要です。実運用前に各モジュールのドキュメント（ソース内 docstring）と型注釈を確認し、必要な権限・APIキーの管理、監査・ログ要件を満たしてください。

---

不明点や README に追記して欲しい箇所（例: 実際のコマンド例、requirements.txt、CI 設定、運用手順）を教えてください。必要に応じて環境変数のテンプレート（.env.example）や簡易の運用チェックリストを作成します。