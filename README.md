# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群（KabuSys）。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログなど、バックテスト／運用に必要な基盤機能を提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策・サイズ制限など）
- OpenAI を用いたニュースセンチメント（銘柄ごと / マクロ）評価（gpt-4o-mini を想定）
- 市場レジーム判定（ETF の MA とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定をトレースするスキーマ・初期化ユーティリティ）
- 環境設定管理（.env 読み込み、環境変数取得ラッパー）

設計上の特徴：
- DuckDB を主要なオンディスク DB として使用
- Look-ahead bias 回避（date/times の扱いに注意）
- 冪等性を重視した保存ロジック（ON CONFLICT / DELETE→INSERT 等）
- API 呼び出しに対する堅牢なリトライ・バックオフ・レート制御

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save / token refresh, rate limit 対応）
  - news_collector（RSS 取得・前処理・記事ID生成・SSRF 対策）
  - quality（データ品質チェック）
  - calendar_management（営業日判定、next/prev_trading_day 等）
  - audit（監査テーブル初期化、監査 DB 作成）
  - stats（zscore_normalize 等汎用統計）
- ai
  - news_nlp.score_news（銘柄ごとのニュースセンチメント生成）
  - regime_detector.score_regime（市場レジーム判定）
- research
  - factor_research（モメンタム・バリュー・ボラティリティ算出）
  - feature_exploration（将来リターン、IC、統計サマリー）
- config
  - Settings（環境変数ラッパー、自動 .env 読み込み）

---

## セットアップ手順

1. リポジトリをクローン（あるいはパッケージを配置）

2. 仮想環境を作成・有効化（推奨）

   - macOS / Linux
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール

   - 最小依存（例）
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発中にパッケージを使う場合はプロジェクトルートで editable install
     ```
     pip install -e .
     ```
     （pyproject.toml / setup が用意されている場合、この方法でパッケージとしてインストールできます）

4. 環境変数を設定

   - プロジェクトルートに `.env`（または `.env.local`）を作成することで `kabusys.config` が自動で読み込みます（ただしテストや明示的制御のため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化可）。
   - 必要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用 BOT トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI API キー（news/regime 呼び出しで使用）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite 監視DB（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ（必要に応じて）  
   - データ格納用スキーマは ETL 実行前に用意することが推奨されます（DDL 用ユーティリティ等がある場合はそちらを利用）。  
   - 監査テーブルは `kabusys.data.audit.init_audit_db` / `init_audit_schema` で初期化できます（下記 usage 参照）。

---

## 使い方（簡単な例）

以下は主要ユースケースの Python コード例です。先に仮想環境を有効にし、必要なパッケージと環境変数を設定してください。

- 共通準備
  ```python
  import duckdb
  from kabusys.config import settings

  db_path = str(settings.duckdb_path)  # Path オブジェクトを文字列化
  conn = duckdb.connect(db_path)
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると今日の日付が使われます
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）生成
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # api_key を引数で渡すか、OPENAI_API_KEY 環境変数を設定してください
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"Written scores for {written} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査 DB の初期化（監査専用 DB を生成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで監査用テーブルが作成されます
  ```

- audit schema を既存 conn に追加
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注意点：
- OpenAI 呼び出しは API レート・課金に関係するため、テスト時はモック（unittest.mock.patch）で差し替えることを推奨します。モジュール内の _call_openai_api はユニットテスト用に差し替え可能に設計されています。
- ETL や news の関数は DuckDB の特定テーブル（raw_prices / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等）を前提とします。実行前にスキーマが存在することを確認してください。

---

## 設定（config）について

- 自動 .env 読み込み
  - `kabusys.config` はパッケージルートからプロジェクトルート（.git または pyproject.toml）を探索し、`.env` → `.env.local` の順で読み込みます。
  - OS 環境変数が優先されます。`.env.local` は既存 OS 環境変数を上書き可能（上書き可フラグ）。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで便利です）。

- 必須値未設定時
  - Settings のプロパティ（例 `settings.jquants_refresh_token`）は未設定時に ValueError を投げます。`.env.example` を参考に `.env` を準備してください。

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が未設定
  - `.env` に設定しているか、シェルで export されているか確認してください。`KABUSYS_DISABLE_AUTO_ENV_LOAD` を誤ってセットしていないかも確認。

- DuckDB テーブルが無い / SQL エラー
  - ETL やニュースモジュールは事前に期待されるテーブル（raw_prices/raw_news 等）が存在することを想定しています。スキーマ初期化の手順（別途提供している場合）を実行してください。

- OpenAI API 呼び出し失敗（RateLimit / Timeout）
  - モジュール内でリトライ・バックオフ処理がありますが、API キーと割当量が十分か確認してください。テスト時はモック推奨。

- RSS 取得時の SSRF/接続問題
  - news_collector は SSRF 対策を行っており、プライベートアドレスや不正なスキームをブロックします。外部接続環境（プロキシ等）が影響している場合はログを確認してください。

---

## ディレクトリ構成

（主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境設定・.env 読み込み
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（銘柄別）
    - regime_detector.py       — 市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py              — ETL パイプライン / run_daily_etl 等
    - jquants_client.py        — J-Quants API クライアント（fetch/save 等）
    - news_collector.py        — RSS 収集・前処理
    - quality.py               — データ品質チェック
    - calendar_management.py   — 市場カレンダー管理（営業日判定等）
    - stats.py                 — zscore_normalize 等統計ユーティリティ
    - audit.py                 — 監査ログスキーマ初期化
    - etl.py                   — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — IC / forward returns / summary
  - research/  （その他 research 用ユーティリティ）
  - その他：execution, monitoring, strategy 等（パッケージ設計上のエントリあり）

---

## 開発 / 貢献

- ユニットテスト: OpenAI / ネットワーク呼び出し部分はモックしてテストを行ってください。モジュール内の private な _call_openai_api / _urlopen などは差し替えやすく設計されています。
- コードスタイル: ログ出力・例外ハンドリング・型注釈を重視しています。DuckDB の SQL はパラメータバインド（?）を使用してインジェクションを回避してください。

---

必要に応じて README にサンプル .env.example、SQL スキーマ初期化スクリプト、実行用 CLI 例などを追加できます。追加してほしい項目があれば教えてください。