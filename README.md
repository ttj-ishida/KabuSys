# KabuSys

KabuSys は日本株を対象としたデータプラットフォーム兼リサーチ／自動売買支援ライブラリです。J-Quants API からのデータ取得／ETL、ニュース収集と LLM によるセンチメント評価、ファクター算出、マーケットカレンダー管理、監査ログ（監査テーブルの初期化）などを備えています。

この README ではプロジェクト概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

主な目的：
- J-Quants API を用いた市場データ（OHLCV、財務データ、マーケットカレンダー等）の差分 ETL
- RSS ニュースの収集と前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント算出（銘柄別 ai_score）およびマクロセンチメントと ETF MA を合成した市場レジーム判定
- ファクター（モメンタム／バリュー／ボラティリティ等）計算と特徴量探索ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ用テーブル（signal / order_request / executions）を DuckDB に初期化するユーティリティ

設計上のポイント：
- ルックアヘッドバイアスに配慮した実装（内部で date.today() を無作為に参照しない等）
- DuckDB を主要な社内データベースとして使用
- 冪等性（ON CONFLICT / DELETE→INSERT の置換）を重視した保存ロジック
- ネットワーク/API 呼び出しに対するリトライ・バックオフ、レート制御、セーフフォールバック

---

## 機能一覧

- データ ETL
  - run_daily_etl（株価、財務、カレンダーの差分 ETL + 品質チェック）
  - 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants API クライアント（認証トークン自動更新、ページネーション、レート制限）
- ニュース処理
  - RSS フィード収集（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - ニュース NLP：銘柄別センチメント score_news（OpenAI によるバッチ解析、JSON Mode）
- マーケットレジーム判定
  - score_regime（ETF 1321 の MA200 乖離 + マクロニュース LLM スコアを合成）
- 研究／リサーチ
  - calc_momentum / calc_value / calc_volatility（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索）
  - zscore_normalize（正規化ユーティリティ）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（まとめて実行）
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（J-Quants からのカレンダー差分取得）
- 監査ログ（Audit）
  - init_audit_schema / init_audit_db（監査テーブルとインデックスの作成）

---

## 必要条件（推奨）

- Python 3.10+
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全化）
- 標準ライブラリの他に urllib, gzip, json などを使用

例（pip）:
```
pip install duckdb openai defusedxml
```

注: 実行環境に応じて追加の依存関係が必要になる場合があります（プロジェクトの packaging に依存）。

---

## 環境変数 / .env

config モジュールは自動でプロジェクトルートの `.env` と `.env.local`（存在すれば）を読み込みます。自動ロードを抑止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（README 用サンプル）:

- JQUANTS_REFRESH_TOKEN=xxxxx
  - J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD=xxxx
  - kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
  - kabuAPI のベース URL（省略可）
- OPENAI_API_KEY=sk-...
  - OpenAI API キー（score_news / score_regime で使用）
- SLACK_BOT_TOKEN=xoxb-...
  - Slack 通知用の Bot トークン（必須設定箇所がある場合）
- SLACK_CHANNEL_ID=C01234567
  - Slack 通知先チャンネル ID
- DUCKDB_PATH=data/kabusys.duckdb
  - デフォルトの DuckDB ファイルパス
- SQLITE_PATH=data/monitoring.db
  - 監視用 SQLite パス（使用箇所に応じて）
- KABUSYS_ENV=development | paper_trading | live
  - 実行環境（デフォルト development）
- LOG_LEVEL=INFO
  - ログレベル（DEBUG/INFO/...）

例: `.env.example`
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL_ID=your_slack_channel
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作る:
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール:
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

   もしプロジェクトに `pyproject.toml` / `requirements.txt` があればそちらを用いてください:
   ```
   pip install -e .
   ```

3. 環境変数を設定（`.env` を作成）:
   - 上記の `.env.example` を参考に `.env` を作成してください。
   - テスト時に自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB データベースの準備:
   - ETL を実行する前に必要なスキーマを作成するスクリプト（存在する場合）を実行するか、初回 ETL 実行で必要テーブルが作成される前提で実行してください。
   - 監査ログ用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（基本例）

以下は Python REPL / スクリプトからの簡単な呼び出し例です。すべての例は `duckdb` パッケージを使い、`settings.duckdb_path` 等を参考にパスを設定します。

- ETL（日次 ETL）の実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリング
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら環境変数 OPENAI_API_KEY を使用
  print("written:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査テーブルにアクセス可能
  ```

- 研究系関数の呼び出し（例：モメンタム計算）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  print(records[:5])
  ```

注意点:
- OpenAI 呼び出しを使う関数（score_news, score_regime）は API キーが必要です（api_key 引数または環境変数 OPENAI_API_KEY）。
- J-Quants API を使う ETL は JQUANTS_REFRESH_TOKEN が必要です（settings.jquants_refresh_token）。
- DuckDB のスキーマ（テーブル）整備はプロジェクトの別スクリプト / MIGRATION を参照してください。ETL 実行前に期待テーブルが存在することを確認してください。

---

## ディレクトリ構成（主要ファイル・モジュールの説明）

（抜粋）プロジェクト内の主要モジュール:

- src/kabusys/__init__.py
  - パッケージのメタ情報（__version__）と主要サブパッケージのエクスポート

- src/kabusys/config.py
  - 環境変数管理（.env 自動ロード、必須変数チェック、settings オブジェクト）

- src/kabusys/data/
  - calendar_management.py : マーケットカレンダー管理、営業日判定、calendar_update_job
  - pipeline.py           : 日次 ETL の orchestration（run_daily_etl 等）
  - jquants_client.py     : J-Quants API クライアント（取得・保存関数）
  - news_collector.py     : RSS フィード取得・前処理・raw_news への保存ロジック
  - quality.py            : データ品質チェック（欠損/重複/スパイク/日付不整合）
  - stats.py              : 汎用統計ユーティリティ（zscore_normalize）
  - audit.py              : 監査ログ（signal / order_requests / executions）の DDL と初期化

- src/kabusys/ai/
  - news_nlp.py           : ニュースを LLM で解析して ai_scores へ書き込む（score_news）
  - regime_detector.py    : ETF とマクロニュースを元に市場レジーム判定（score_regime）

- src/kabusys/research/
  - factor_research.py    : ファクター計算（momentum, value, volatility）
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー、rank 等

- src/kabusys/ (その他)
  - data パッケージ、research パッケージの再エクスポート等

上記以外にも補助的なモジュールが含まれており、各モジュールの docstring に設計意図と処理フローが詳しく記載されています。

---

## 運用 / 開発時の注意点

- Look-ahead バイアスに注意：モジュールは設計上ルックアヘッドを避けるよう実装されていますが、利用時に target_date を誤って現在時刻で指定しないよう注意してください。
- OpenAI の使用は API コストがかかります。バッチサイズ、リトライ、ログを調整してください。
- J-Quants API はレート制限があるため、ETL は RateLimiter に基づいて安全に実行されますが、大量の同時実行は避けてください。
- DuckDB のバージョン互換性に依存する箇所があるため、推奨バージョンでの動作検証を行ってください（例: executemany の空リスト挙動等）。

---

## 付記

- 本 README はコード中の docstring を基に作成しています。実際の利用にあたっては実装の更新に合わせて README を更新してください。
- 追加で CLI スクリプトやユーティリティがある場合は、その使用方法（systemd / cron の設定例、ログ管理、バックアップ等）を別途ドキュメント化してください。

---

必要であれば、特定のユースケース（例: ETL の cron ジョブ化、監査ログのクエリ例、Slack 通知連携）についてのサンプル手順・スクリプトも作成します。どのセクションを詳しく作り込むか指示ください。