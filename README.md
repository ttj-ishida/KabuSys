# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。ETL（J-Quants からの株価・財務・カレンダーの取得）、ニュース収集と NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログスキーマなどを含みます。

---

## プロジェクト概要

KabuSys は日本株のデータパイプライン、AI ベースのニュースセンチメント処理、リサーチ用ファクター生成、ならびに売買監査ログの雛形を提供する Python パッケージです。主な設計方針として以下を重視しています。

- Look-ahead バイアスを避けるため、内部で `date.today()` を直接参照しない（呼び出し側が日付を与える）。
- DuckDB をデータ永続化に使用し、クエリは可能な限り SQL で実行。
- J-Quants / OpenAI API に対してはリトライ・レートリミット・フェイルセーフを組み込み。
- 冪等性を重視した DB 保存（ON CONFLICT / idempotent 書き込み）。
- ニュース収集では SSRF / XMLBomb 等のセキュリティ対策を実施。

---

## 機能一覧

- 環境設定管理
  - .env ファイルを自動読み込み（プロジェクトルートの検出ロジック、無効化フラグあり）
  - 必須設定の検証（Settings オブジェクト）

- データ取得 / ETL（kabusys.data.pipeline）
  - J-Quants からの株価日足・財務・カレンダーの差分取得（ページネーション対応）
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付整合性）
  - calendar / prices / financials の個別 ETL と統合日次 ETL

- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（refresh token → id token）自動化
  - レートリミット、リトライ、ページネーション処理
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF/リダイレクト検査、gzip/サイズ制御）
  - 前処理（URL 除去・空白正規化）、記事ID生成（URL 正規化 + SHA256）
  - raw_news / news_symbols への冪等保存ロジックを想定

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI (gpt-4o-mini) を用いた銘柄別ニュースセンチメントスコア計算
  - バッチ処理、JSON モード、リトライ、レスポンス検証、スコアクリッピング
  - 指定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を対象

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で bull/neutral/bear を判定
  - レジームは market_regime テーブルへ冪等書き込み

- 研究（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ、Z スコア正規化ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査用 DB 初期化（UTC タイムゾーン固定、冪等 DDL 作成）

---

## 動作要件

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, OpenAI, RSS ソース）

実際の要件はプロジェクトの pyproject.toml / requirements.txt を参照してください（このリポジトリの提示内には明示ファイルはありませんが、ソースは上記のライブラリを使っています）。

---

## セットアップ手順

1. リポジトリをクローン、パッケージをインストール（編集可能インストール推奨）

   ```bash
   git clone <repo-url>
   cd <repo-dir>
   pip install -e .
   ```

2. Python バージョン確認（3.10+ 推奨）:

   ```bash
   python --version
   ```

3. 必要な環境変数を設定（.env をプロジェクトルートに置くか OS 環境変数で設定）

   例: .env（プロジェクトルート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id

   # 任意
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   - 自動ロードはデフォルトで有効です（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動ロードを無効化するには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB 用ディレクトリ作成（必要に応じて）

   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は Python セッションやスクリプトから利用する場合の例です。すべての関数は DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- DuckDB に接続する

  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（J-Quants からデータ取得・保存・品質チェック）

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores テーブルへ書き込む

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数で指定済みの想定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込件数: {written}")
  ```

- 市場レジームを評価して market_regime テーブルへ書き込む

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する

  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # テーブル作成済みの接続が返る
  ```

- カレンダーの夜間更新ジョブ実行（JPX カレンダーを取得して market_calendar を更新）

  ```python
  from datetime import date
  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn, lookahead_days=90)
  print(f"保存件数: {saved}")
  ```

- ニュース RSS をフェッチする（単体テストや収集前確認用）

  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  print(len(articles))
  ```

注意:
- OpenAI 呼び出しは API キー（環境変数 OPENAI_API_KEY）を必要とします。関数には api_key 引数を渡すこともできます。
- J-Quants への認証は環境変数 JQUANTS_REFRESH_TOKEN を使用します（get_id_token が内部で refresh token を使って id token を取得します）。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
  - KABU_API_PASSWORD: kabuステーション API 用パスワード（実行モジュールで使用）
  - SLACK_BOT_TOKEN: Slack 通知用（監視等で使用）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（通知先）

- オプション / デフォルト
  - KABU_API_BASE_URL: kabu API の基地 URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（モニタリング）パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 実行環境（development / paper_trading / live。デフォルト: development）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

---

## ディレクトリ構成（概略）

以下はパッケージ内の主要モジュール（提示されたコードベースに基づく）です。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / Settings 管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP（OpenAI 連携）
    - regime_detector.py               — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント & 保存ロジック
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETL の公開インターフェース（ETLResult）
    - news_collector.py                — RSS ニュース収集
    - calendar_management.py           — マーケットカレンダー管理（営業日ロジック等）
    - stats.py                         — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py                       — データ品質チェック
    - audit.py                         — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算（momentum/value/volatility）
    - feature_exploration.py           — 将来リターン / IC / summary 等

---

## 開発・テストについて（補足）

- 自動環境読み込みは .git または pyproject.toml を基準にプロジェクトルートを検出して .env / .env.local を読み込みます。テスト時に環境を汚したくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しやネットワーク I/O 部分はユニットテストでモックしやすいように設計されています（内部の _call_openai_api や _urlopen 等を差し替え可能）。
- DuckDB に対する executemany の互換性や空パラメータの扱いに注意（ソース内で回避ロジックあり）。

---

## サポート / 貢献

バグや改善提案は Issue を作成してください。Pull Request は歓迎します。設計思想（Look-ahead バイアス回避、冪等性、セキュリティ対策）を尊重した変更をお願いします。

---

README の内容に関して、特に詳しい利用シナリオ（例: バックテスト用のデータ初期化手順、kabuステーション実取引連携、Slack 通知フロー）を追加で記載したい場合は、用途に応じて追記します。どうしますか？