# KabuSys — 日本株自動売買プラットフォーム（README）

このリポジトリは日本株のデータ基盤・リサーチ・自動売買に関するコアライブラリ群を含むプロジェクトです。
主要コンポーネントは ETL（J-Quants からのデータ取得）、ニュース収集と NLP（OpenAI を使用したセンチメント評価）、ファクター計算、マーケットカレンダー管理、監査ログ（発注／約定トレーサビリティ）などです。

以下は本コードベースに基づく README。セットアップ方法、主要機能、使い方例、ディレクトリ構成などを日本語でまとめています。

目次
- プロジェクト概要
- 機能一覧
- 必要な環境変数
- セットアップ手順
- 使い方（簡易サンプル）
  - DuckDB 接続
  - 日次 ETL 実行
  - ニュースセンチメントスコアリング
  - 市場レジーム判定
  - 監査DB初期化
- ディレクトリ構成（主要ファイル一覧）
- 実装上の注意点 / 設計方針

---

## プロジェクト概要

KabuSys は「データ収集 → 品質チェック → ファクター生成 → シグナル生成 → 発注／監査」という流れを想定した日本株向けの自動売買基盤のコアモジュール群です。  
主に以下を目的とします：

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL と DuckDB への保存
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去等）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（銘柄別）とマクロセンチメント評価
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- マーケットカレンダー管理（営業日判定、next/prev 等）
- 監査ログ用スキーマ（signal / order_request / executions）と初期化ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）

---

## 機能一覧（抜粋）

- data/
  - jquants_client: J-Quants API クライアント（取得／保存／ページネーション／リトライ／レート制限）
  - pipeline: 日次 ETL 実行（run_daily_etl、個別 ETL 関数）
  - news_collector: RSS 取得・前処理・raw_news 保存
  - calendar_management: market_calendar 管理、営業日判定、calendar_update_job
  - quality: データ品質チェック（missing / spike / duplicates / date consistency）
  - audit: 監査ログスキーマの作成・監査DB初期化
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄毎ニュースセンチメントを OpenAI で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）MA とマクロニュース LLM を合成して市場レジームを判定
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config.py
  - .env 自動読み込み（.env, .env.local）ロジック / Settings クラス

---

## 必要な環境変数

主に次の環境変数が使用されます（必須は README 中に明記）:

必須（少なくとも実行対象により必要）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知を使う場合
- KABU_API_PASSWORD — kabuステーション API を使う場合

任意 / デフォルトあり
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env 読み込みを無効化
- KABUSYS_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

注意: パッケージの config.Settings は .env（プロジェクトルートの .env/.env.local）を自動読み込みします（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化）。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 必要パッケージをインストール
   本コードベースでは少なくとも以下が必要です：
   - duckdb
   - openai
   - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```

   （実運用では logging 設定やその他ライブラリが追加される可能性があります。requirements.txt があればそちらを利用してください）

4. 環境変数設定
   プロジェクトルートに `.env` または `.env.local` を作成し必須キーをセットしてください。例：
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

   自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. データベースディレクトリ作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（簡易サンプル）

以下は Python REPL やスクリプトから直接呼び出す簡易例です。各操作は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を引数に取ります。

注意: 実際の運用ではロギング設定や例外処理を行ってください。

- DuckDB 接続作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（prices / financials / calendar を順に取得して品質チェックを実行）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア付け（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # target_date に対応するニュースウィンドウ（前日15:00 JST 〜 当日8:30 JST）をスコア
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {n_written} ai_scores")
  ```

- 市場レジーム判定（ETF 1321 を使った MA とマクロニュースの合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  res = score_regime(conn, target_date=date(2026, 3, 20))
  print("done", res)
  ```

- 監査ログ用 DuckDB を初期化（監査専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db

  # ファイルパスまたは ":memory:" が指定可能
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants からデータを個別に取得（低レベル）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  token = get_id_token()  # settings.jquants_refresh_token が必要
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールとファイル（今回のコードベース）です。

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py (re-export)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（各種ファクター計算・解析ユーティリティ）

各ファイル内に詳細な docstring と設計方針が記載されています。実装は DuckDB を中心に SQL を多用し、外部 API についてはキャッシュ・レートリミット・リトライ等に配慮しています。

---

## 実装上の注意点 / 設計方針（抜粋）

- Look-ahead bias 回避
  - バックテストや解析で将来情報を参照しないよう、関数は内部で datetime.today() や date.today() を直接参照しない設計（target_date を受け取る）。
- 冪等性
  - DB への保存は基本的に ON CONFLICT DO UPDATE（重複回避）で実行します（jquants_client.save_* 等）。
- フェイルセーフ
  - 外部 API 呼び出しで失敗した場合、多くの処理は例外を直接上げずに警告ログを出しフォールバックする実装（例: LLM の失敗はスコアを 0 にするなど）。
- セキュリティ対策（news_collector）
  - RSS の URL 正規化・トラッキングパラメータ除去、SSRF 対策（リダイレクト先検査・プライベート IP 拒否）、受信サイズ上限などを実装しています。
- OpenAI 呼び出し
  - gpt-4o-mini と JSON Mode を利用する設計。レスポンスの検証やリトライ（429/ネットワーク/5xx）を行います。
- カレンダー
  - market_calendar が未取得の場合は曜日ベースのフォールバックを使用する等、DB が部分的にしか整備されていない運用でも一貫した挙動をとるようにしています。

---

## 参考（トラブルシューティング）

- .env の自動ロードが効かない／テストしたい場合：
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効にできます。
- OpenAI 呼び出しのテスト：
  - モジュール内の _call_openai_api をモックしてユニットテストが可能な設計です（news_nlp, regime_detector で独立実装）。
- DuckDB バージョン依存：
  - executemany に空リストを渡せない制約を考慮しているコードがあるため（DuckDB 0.10 へ配慮）、空パラメータの扱いに注意してください。

---

以上です。必要であれば README にインストール済みパッケージのバージョン要件（requirements.txt）や具体的な運用手順（cron/airflow での ETL スケジュール、Slack 通知の設定例、kabuAPI 発注フロー）を追加できます。どの情報を優先して追記するか教えてください。