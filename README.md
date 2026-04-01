# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリです。J-Quants / kabuステーション / OpenAI 等と連携して、データ収集（ETL）、データ品質チェック、ファクター計算、ニュースNLP（LLM）によるスコアリング、監査ログ管理、マーケットカレンダー管理、そして市場レジーム判定などを提供します。

主にバックテスト用データプラットフォームや自動売買システムのインフラ層（データ収集・前処理・監査・リサーチ・AI スコアリング）を担います。

## 主な機能

- データ取得（J-Quants API）
  - 株価日足（OHLCV）
  - 財務（四半期 BS/PL）
  - JPX マーケットカレンダー
  - 上場銘柄情報
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付整合性）
  - ETL 実行結果を ETLResult として集約
- データ品質チェック（quality モジュール）
- ニュース収集（RSS）と前処理（news_collector）
  - トラッキングパラメータ除去、SSRF 対策、XML 脆弱性対策
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメント（ai.news_nlp.score_news）
  - マクロニュース＋ETF MA による市場レジーム判定（ai.regime_detector.score_regime）
- リサーチ用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC / 統計サマリー
  - Z スコア正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
- 市場カレンダー管理（calendar_management）
  - 営業日判定、次/前営業日取得、夜間カレンダー更新ジョブ

## 要件（主な依存）

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （標準ライブラリ：urllib, json, datetime, logging など）

実際にはプロジェクトの requirements.txt / pyproject.toml を参照してください（本リポジトリでは抜粋コードを元に説明しています）。

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   - pyproject.toml/requirements.txt がある場合はそれを使ってください。無ければ主要依存を手動でインストールします:
   ```bash
   pip install duckdb openai defusedxml
   ```
4. パッケージを開発モードでインストール（任意）
   ```bash
   pip install -e .
   ```
5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロード無効）。
   - 必須の環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（使用箇所に応じて）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必要時）
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（ai.score 系を使う場合）
   - データベースパス（任意、デフォルトあり）
     - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH: デフォルト `data/monitoring.db`
   - ログ等の設定
     - KABUSYS_ENV: development | paper_trading | live
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

   例 .env（最低限の例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxx
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   ```

## 使い方（簡単な例）

以下はライブラリの代表的なユースケースの例です。実行前に必要な環境変数が設定されていることを確認してください。

- DuckDB 接続作成（共通）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL（データ取得＋品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定しない場合は今日が対象
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとのニューススコアを ai_scores テーブルへ書き込む）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数で設定するか、api_key 引数に渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースで判定）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  # OpenAI API のキーを渡すか環境変数 OPENAI_API_KEY を設定
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可
  ```

- カレンダー操作（営業日判定など）
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print("営業日?", is_trading_day(conn, d))
  print("次の営業日:", next_trading_day(conn, d))
  ```

注意:
- 多くの関数は Look-ahead bias を避けるため date / target_date を明示的に受け取ります。内部で datetime.today() / date.today() を直接参照しない設計です（ETL の target_date には注意してください）。
- OpenAI 呼び出しは外部依存のため、テスト時は該当関数をモックすることを想定しています（例: unittest.mock.patch）。

## 環境変数の自動ロード

- `kabusys.config` はプロジェクトルート（.git または pyproject.toml のあるフォルダ）を探索し、`.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 読み込み順は OS 環境変数 > .env.local（上書き） > .env（未設定のみ）です。

## ディレクトリ構成（主要ファイル）

（src 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — 銘柄ニュースの LLM スコアリング
    - regime_detector.py         — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント & DuckDB 保存ユーティリティ
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult 再エクスポート
    - news_collector.py          — RSS ニュース収集・前処理
    - calendar_management.py     — 市場カレンダー管理（営業日判定、update_job）
    - quality.py                 — データ品質チェック
    - stats.py                   — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                   — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py         — Momentum/Value/Volatility 等の計算
    - feature_exploration.py     — 将来リターン、IC、統計サマリー
  - ai/、research/、data/ の各モジュールはそれぞれの責務に分かれています。

（実際のプロジェクトでは tests/, scripts/, docs/ 等が追加されることが想定されます）

## 注意事項 / 運用上のポイント

- API レート制御・リトライ
  - J-Quants クライアントと OpenAI 呼び出しにはリトライやバックオフ・レート制御が実装されていますが、運用時のリクエスト量やトークン管理には注意してください。
- Look-ahead バイアス対策
  - 多くの関数は明示的な target_date を受け取り、過去データのみ参照するよう実装されています。バックテストや本番で日時取り扱いを誤るとバイアスが入るため設計方針に沿って利用してください。
- セキュリティ
  - news_collector は SSRF や XML Bomb などに対する対策が入っていますが、公開環境で実行する場合はネットワークアクセス制御・認証情報の取り扱いに注意してください。
- DuckDB の executemany 空リスト制約など、利用する DuckDB のバージョン依存の挙動に注意してください（コード内でも互換性対策が含まれています）。

---

詳細な API（関数一覧や引数仕様）は各モジュールの docstring コメントを参照してください。追加の利用例や運用手順（cron / Airflow / systemd でのスケジューリング、Slack 通知の設定等）が必要であれば、用途に応じた README の拡張を行います。