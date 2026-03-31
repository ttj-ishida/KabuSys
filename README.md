# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤のコアライブラリです。J-Quants / RSS / OpenAI 等と連携してデータ収集・品質チェック・特徴量計算・ニュースNLP・市場レジーム判定・監査ログ管理などを行うモジュール群を提供します。

---

## 概要

KabuSys は以下の機能群を持つ内部ライブラリです。

- J-Quants API 経由の株価・財務・カレンダー取得（ページネーション・認証・リトライ・レート制御対応）
- RSS によるニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI を用いたニュースセンチメント（ai_scores）とマクロセンチメントを組み合わせた市場レジーム判定
- ETL パイプライン（差分取得、保存、品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ファクター計算・研究用ユーティリティ（モメンタム、バリュー、ボラティリティ、将来リターン、IC、統計サマリー）
- 監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ
- 設定読み込みユーティリティ（.env の自動読み込み、環境変数保護）

設計上の主要ポイント:
- ルックアヘッドバイアス防止（内部で datetime.today()/date.today() を不必要に参照しない）
- 冪等性（DB への保存は ON CONFLICT などで対処）
- フェイルセーフ（外部 API 失敗時もなるべく処理継続）
- レート制御・指数バックオフ・リトライ戦略
- セキュリティ配慮（RSS の SSRF 対策、defusedxml で XML の安全化）

---

## 主な機能（機能一覧）

- データ取得・保存
  - J-Quants: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - 保存: save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB へ冪等保存）
- ETL
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - ETL 結果を ETLResult として返却
- ニュース収集
  - fetch_rss（RSS 取得・正規化・前処理・ID 生成）
- ニュース NLP / マクロスコア
  - score_news (銘柄別ニュースセンチメント → ai_scores)
  - score_regime (1321 の MA200 乖離 + マクロ NLP を合成して market_regime に保存)
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ
  - init_audit_schema / init_audit_db（監査用テーブルの初期化）
- 研究用ユーティリティ
  - factor 計算: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - stats: zscore_normalize
- 設定管理
  - kabusys.config.settings（.env の自動読み込み、重要な環境変数取得）

---

## 依存関係（主なライブラリ）

- Python 3.9+
- duckdb
- openai (OpenAI SDK)
- defusedxml
- （標準ライブラリのみで動くユーティリティが多い）

実行環境に応じて追加の依存がある場合があります（例: CI / 実運用スクリプト）。

---

## セットアップ手順

1. リポジトリをクローン（既にローカルにある前提なら不要）

2. 仮想環境の作成と有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. パッケージのインストール
   (プロジェクトの setup がある場合は editable install が可能)
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   pip install -e .
   ```
   ※ requirements.txt があればそれを利用してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（score_news/score_regime で使用）
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（発注処理系で使用）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（モニタリング等）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルトを持つ:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト `INFO`
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`
     - PID_FILE_PATH — デフォルト `data/execution.pid`
   - 例 (.env)
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-xxx
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

---

## 使い方（簡単なコード例）

以下は Python REPL やスクリプトから利用する例です。事前に環境変数を設定し、duckdb がインストールされていることを前提とします。

- DuckDB 接続準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（OpenAI API キーを環境変数 OPENAI_API_KEY に設定）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書込み銘柄数:", n_written)
  ```

- 市場レジームスコアの計算（1321 MA200 + マクロセンチメント）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # init_audit_db は指定パスに DB ファイルを作成して接続を返します
  ```

- 市場カレンダー更新ジョブ（J-Quants から差分取得）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from datetime import date

  saved = calendar_update_job(conn, lookahead_days=90)
  print("saved calendar rows:", saved)
  ```

注意点:
- score_news / score_regime は OpenAI を用いるため、API 利用料が発生します。API レートやコストに注意してください。
- J-Quants API 呼び出しにもレート制限が実装されています（デフォルト 120 req/min）。

---

## 設計上の注意・動作ポリシー（短い説明）

- Look-ahead バイアス防止:
  - バックテストやスコア計算で datetime.today()/date.today() を不用意に参照しない設計。
  - データクエリは target_date 未満／以下の境界を厳密に扱います。
- 冪等性:
  - DB 保存は可能な限り ON CONFLICT（UPsert）で行っているため、再実行しても既存データを上書きして整合性を保ちます。
- フェイルセーフ:
  - OpenAI や J-Quants の API エラー時は必要に応じてデフォルト値（例: macro_sentiment=0.0）へフォールバックし、処理全体を停止させない設計が多く採用されています。
- リトライ & バックオフ:
  - ネットワーク/429/5xx 系に対して指数バックオフでリトライします。
- セキュリティ:
  - RSS 取得時の SSRF 対策、defusedxml による XML パース保護、公開設定は .env で管理。

---

## ディレクトリ構成

（src 配下の主要モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 読み込み
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（銘柄別スコア）
    - regime_detector.py            — 市場レジーム判定（1321 MA200 + マクロ）
  - data/
    - __init__.py
    - calendar_management.py        — マーケットカレンダー管理
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の再エクスポート
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - news_collector.py             — RSS ニュース収集
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン / IC / 統計等
  - ai, data, research は high-level API を提供するためのサブパッケージです。

---

## 追加情報 / 運用メモ

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）で行われます。テスト時や明示的に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON Mode を利用（モデル名や挙動は実行時の SDK 仕様に依存します）。
- J-Quants の認証はリフレッシュトークン → id token を取得するフローを組み込み、401 でトークンを自動更新します。
- DuckDB のバージョンによっては executemany の空配列バインドに制約があるため、実装は空チェックを行っています。

---

必要ならば README に以下を追記できます:
- CI / テストの実行方法
- スキーマ定義・DDL（raw_prices / raw_financials / market_calendar / ai_scores / market_regime 等）
- 運用手順（cron / systemd / 監視ルール）
- サンプル .env.example ファイル

追記や具体的な環境向けのセットアップ（例: Docker, systemd unit, サンプル data ディレクトリの初期化手順）が必要であれば教えてください。