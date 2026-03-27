# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、リサーチ用ファクター計算、監査ログスキーマなどを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の要素を提供します。

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
- リサーチ用ファクター計算（モメンタム、バリュ―、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用の DuckDB スキーマ初期化

設計方針としては、Look-ahead bias を避けるために内部で現在時刻を参照しない設計を採用し、DuckDB を単一の分析 DB として利用します。外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備えています。

---

## 機能一覧

- データ取得・保存
  - J-Quants から日次株価（raw_prices）、財務（raw_financials）、マーケットカレンダー（market_calendar）を取得・保存
  - 差分更新・バックフィル対応（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース処理
  - RSS 取得（SSRF 対策、gzip 上限、トラッキング除去）
  - ニュース前処理（preprocess_text）
  - OpenAI による銘柄別センチメント（score_news）
- AI / レジーム判定
  - マクロニュースと ETF 1321 の MA200 乖離を合成して市場レジーム判定（score_regime）
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC 計算、統計サマリ（calc_forward_returns / calc_ic / factor_summary）
  - Z スコア正規化ユーティリティ（zscore_normalize）
- データ品質チェック
  - 欠損 / スパイク / 重複 / 日付不整合チェック（run_all_checks）
- 監査ログ
  - signal_events / order_requests / executions のテーブル定義と初期化（init_audit_schema / init_audit_db）

---

## システム要件 / 依存関係

- Python >= 3.10
- 必須パッケージ（代表）
  - duckdb
  - openai
  - defusedxml

（その他標準ライブラリの urllib/ssl 等を使用します。実際のプロジェクトでは requirements.txt を用意してください。）

例:
pip install duckdb openai defusedxml

---

## 環境変数（主なもの）

KabuSys は .env / .env.local をプロジェクトルートから自動読み込みします（.git または pyproject.toml を探索）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- J-Quants / データ関連
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

- OpenAI / NLP
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を環境変数で使う場合）

- kabuステーション（発注等）
  - KABU_API_PASSWORD: kabu API のパスワード（必須）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

- 通知
  - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

- その他
  - KABUSYS_ENV: environment (development | paper_trading | live), デフォルト: development
  - LOG_LEVEL: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)

注: Settings は `kabusys.config.settings` から参照できます。必須値が未設定のときは ValueError が発生します。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml を用意してください）

4. 環境変数を設定
   - プロジェクトルートに .env を作成し、必要な変数を記載
     例:
       JQUANTS_REFRESH_TOKEN=xxx
       OPENAI_API_KEY=sk-...
       KABU_API_PASSWORD=...
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=CXXXXXX

   - 開発時に自動ロードを使わない場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB データベース準備（任意）
   - デフォルトの DUCKDB_PATH を使うか、明示的にパスを指定
   - 監査 DB のみを準備する例:
       from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な API と例）

以下は簡単な Python 例です。実行前に必要な環境変数を設定してください。

- ETL（日次パイプライン）を実行
  - 目的: J-Quants からデータを差分取得し DuckDB に保存、品質チェックを実行

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア（銘柄別）
  - score_news は OpenAI API キー（api_key 引数または OPENAI_API_KEY 環境変数）を使用します。

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- マーケットレジーム判定（マクロセンチメント + MA200）
  - score_regime は OpenAI を使用してマクロセンチメントを評価します。

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化
  - 監査用 DuckDB を作成しスキーマを初期化します。

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  ```

- リサーチ用ファクター計算
  - calc_momentum / calc_volatility / calc_value は DuckDB 接続と対象日を渡します。

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- データ品質チェック
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.quality import run_all_checks

  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for issue in issues:
      print(issue)
  ```

---

## 自動 .env 読み込み挙動

- プロジェクトルートは、該当ファイルの位置から親ディレクトリを辿り `.git` または `pyproject.toml` を見つけることで決定します。見つからない場合は自動読み込みをスキップします。
- 読み込み順: OS 環境変数（既存） > .env.local（override=True） > .env（override=False）
- `.env` の書式は bash 互換（export KEY=val、コメント行 # など）をサポートします。
- 自動読み込みを無効にする環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## ディレクトリ構成

主要なファイルとモジュールは以下のとおりです（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの OpenAI スコアリング（銘柄別）
    - regime_detector.py     — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS ニュース収集
    - calendar_management.py — マーケットカレンダー管理
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - research/ 以下はリサーチユーティリティを提供

（上記は主要ファイルのみ抜粋しています。実際のプロジェクトでは追加のモジュールやユーティリティが存在する可能性があります。）

---

## 注意点・ベストプラクティス

- OpenAI / J-Quants の API キーは必ず安全に管理してください（.env を利用する場合はリポジトリにコミットしないでください）。
- score_news / score_regime 等は API 呼び出しを伴うため、テスト時は各モジュールの内部 `_call_openai_api` をモックすることを推奨します。
- DuckDB の executemany に対して空リストを渡すとエラーになるバージョンがあるため、本コードは空チェックを行っています。DuckDB バージョン互換性に注意してください。
- 監査ログは削除しない前提です。スキーマ変更や運用ルールに注意してください。
- 本ライブラリは Look-ahead bias を避ける設計を意識していますが、バックテスト等で使用する際はデータの取得日時（fetched_at）や保存タイミングに留意してください。

---

## 開発・テスト

- ユニットテストでは外部 API（J-Quants / OpenAI / ネットワーク呼び出し）をモックすることを推奨します。
- news_collector や OpenAI 呼び出し部分はそれぞれ `_urlopen` / `_call_openai_api` を差し替えてテスト可能です。

---

もし README に追加したいサンプルや CI / デプロイ手順、requirements.txt / pyproject.toml のテンプレートが必要であれば教えてください。