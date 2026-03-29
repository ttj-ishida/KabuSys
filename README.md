# KabuSys

日本株向けの自動売買・データ基盤ユーティリティ群です。  
ETL（J-Quants からの市場データ収集）・ニュース収集・LLM を使ったニュースセンチメント評価・市場レジーム判定・リサーチ用ファクター計算・データ品質チェック・監査ログ管理などの機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存（冪等）。
  - 日次 ETL パイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを順次実行。

- ニュース収集・NLP
  - RSS からのニュース取得（SSRF 対策、トラッキングパラメータ削除、前処理）。
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（score_news）。

- 市場レジーム判定
  - ETF（1321）の200日移動平均乖離とマクロニュースの LLM センチメントを合成し日次で 'bull' / 'neutral' / 'bear' を判定（score_regime）。

- リサーチ補助
  - モメンタム / ボラティリティ / バリュー等のファクター計算。
  - 将来リターン計算、IC（情報係数）や統計サマリー、Zスコア正規化など。

- データ品質チェック
  - 欠損・重複・スパイク・日付不整合の検出（QualityIssue オブジェクトで返却）。

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化ユーティリティ。
  - 監査 DB 初期化（init_audit_db）で監査スキーマを作成。

- 設定管理
  - .env または環境変数を自動読み込み（プロジェクトルート検出、.env ロード順: .env → .env.local、無効化フラグあり）。

---

## 要件

- Python 3.10+（typing の | 記法等を使用）
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, logging, datetime 等）

インストール時に依存関係を明示している場合はそちらに従ってください。最小限は上記ライブラリ群が必要です。

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーを用意

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

3. 依存パッケージをインストール

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。ここでは最低限の例）

   ```bash
   pip install duckdb openai defusedxml
   ```

4. パッケージを開発モードでインストール（任意）

   ```bash
   pip install -e .
   ```

5. 環境変数設定

   プロジェクトルートに `.env`（または `.env.local`）を作成します。必須キーの例:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注周りを使う場合）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知を使う場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）

   任意 / デフォルト値:

   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: データ用 DuckDB パス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。

---

## 使い方（主要な API とサンプル）

以下は簡単な利用例です。各関数は duckdb の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- 共通インポート例

  ```python
  import duckdb
  from kabusys.config import settings
  ```

- 日次 ETL 実行（株価・財務・カレンダー取得と品質チェック）

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコアの取得（LLM）

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数または api_key 引数で与える
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（MA200 とマクロニュースを合成）

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（監査用 DuckDB 初期化）

  ```python
  from kabusys.data.audit import init_audit_db

  # ファイルベース DB を作成してスキーマを初期化
  audit_conn = init_audit_db("data/audit_duckdb.db")
  ```

- 研究用ファクター計算の呼び出し例

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect(str(settings.duckdb_path))
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- 設定の参照

  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)
  print(settings.env, settings.log_level)
  ```

注記:
- OpenAI 呼び出しを行う関数（score_news, score_regime）は API キーを必須とします。api_key 引数に渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- ETL や API 呼び出しはネットワーク・API 依存です。リトライやフォールバックの実装は各モジュール内にありますが、運用上は API レートやエラーの取り扱いに注意してください。
- DuckDB の executemany は空リストを受け付けないバージョンがあります（モジュール内で保護済み）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- OPENAI_API_KEY (必須 for NLP) — OpenAI API キー（score_news 等）
- KABU_API_PASSWORD (必須 if using kabuAPI) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
- LOG_LEVEL — ログレベル（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング）パス（default: data/monitoring.db）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（set=1 で無効）

設定はプロジェクトルートの `.env` / `.env.local` に記載するか、システム環境変数で設定してください。config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env を読み込みます。

---

## 重要な設計・運用上の注意点

- ルックアヘッドバイアス対策:
  - 日付の扱いは内部で datetime.today() / date.today() を不用意に参照しない設計（関数は target_date を明示的に受け取る）になっています。バックテスト・研究用途での利用時は注意してください。
- 冪等性:
  - ETL の保存処理は基本的に ON CONFLICT / DO UPDATE 等で冪等化されています。
- エラーハンドリング:
  - LLM / API の一時エラー・5xx 等はモジュール内でリトライやフェイルセーフ（デフォルトスコア=0 等）にフォールバックする実装があります。
- テスト:
  - 自動 .env ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテスト等で使用）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（LLM）処理
  - regime_detector.py — 市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
  - etl.py — ETL インターフェース再エクスポート
  - pipeline.py — ETL パイプライン / run_daily_etl 等
  - stats.py — 統計ユーティリティ（zscore 等）
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマの初期化
  - jquants_client.py — J-Quants API クライアント（フェッチ・保存）
  - news_collector.py — RSS ニュース収集
- research/
  - __init__.py
  - factor_research.py — ファクター計算
  - feature_exploration.py — forward returns, IC, summary 等

この README はコードベースの主要 API と設計方針を簡潔にまとめたものです。各モジュール内にはより詳細な docstring と設計注記が含まれていますので、実装や運用に際しては該当モジュールのドキュメント（ソース中の説明）を参照してください。

もし README に加えたい具体的な運用手順（例: CI/CD、cron ジョブでの ETL 実行サンプル、Docker 化手順、または .env.example のテンプレート）などがあれば教えてください。追記します。