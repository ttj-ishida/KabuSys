# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群（KabuSys）。  
データ収集（J-Quants）、ETL、ニュースNLP、リサーチ（ファクター計算）、監査ログ、マーケットカレンダー、AIを用いた市場レジーム判定などの機能を提供します。

---

## 主な特徴（機能一覧）

- データ収集・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、上場銘柄情報、マーケットカレンダーを差分取得・保存
  - 差分取得、バックフィル、ページネーション、再取得・品質チェック機構を備えた日次ETL（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェック（qualityモジュール）
- 市場カレンダー管理
  - JPX カレンダー取得・更新、営業日判定・前後営業日探索、SQ判定など（calendar_management）
- ニュース収集とNLP
  - RSS からの収集（SSRF対策、URL正規化、トラッキングパラメータ除去）、raw_news保存（news_collector）
  - OpenAI を用いたニュースセンチメント解析（銘柄ごとのスコア付け: news_nlp.score_news）
- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュースの LLMセンチメントを合成して日次で市場レジーム判定（ai.regime_detector.score_regime）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算、将来リターン計算、IC算出、統計サマリー（research）
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution の監査テーブル定義と初期化ユーティリティ（data.audit）
- 設定管理
  - .env / .env.local の自動読み込み、環境毎設定、必須環境変数の検証（config）

---

## 要件

- Python 3.10 以上（コード中での型記法（`X | Y`）を使用）
- 主な依存パッケージ
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS ソース）

（インストールはプロジェクトの packaging / requirements に従ってください。ここでは主要パッケージを示しています）

---

## セットアップ手順

1. リポジトリをクローンし、ソースツリーのルートに移動します。
   (パッケージは `src/kabusys` 配下に配置されています)

2. 仮想環境を作成・有効化：
   - macOS / Linux:
     python -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

3. パッケージ依存をインストール：
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください: pip install -e .[dev] など）

4. 環境変数の準備：
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成します。自動ロードはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主に必要となる環境変数（例）:
     - JQUANTS_REFRESH_TOKEN （必須: J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD （kabu API パスワード）
     - OPENAI_API_KEY （OpenAI API キー、news_nlp / regime_detector で使用）
     - KABU_API_BASE_URL （省略可。デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID （通知用、任意）
     - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH （監視 DB、デフォルト: data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH 等（監視用）
   - 必須の環境変数が未設定の場合は config.Settings のプロパティで ValueError が発生します。

5. データディレクトリを作成（必要に応じて）:
   mkdir -p data

---

## 使い方（代表的なユースケース）

以下は Python スクリプト上で KabuSys の主要機能を利用する最小例です。

- DuckDB 接続を作成して日次ETLを実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- OpenAI を使ってニューススコアを生成（ai.news_nlp）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # 必要なら api_key を明示的に渡す（None の場合は環境変数 OPENAI_API_KEY を参照）
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")
  ```

- 市場レジームを判定して保存（ai.regime_detector）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査DBを初期化する（audit テーブル作成）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は監査用の DuckDB 接続（UTC タイムゾーン設定済み）
  ```

- マーケットカレンダー（営業日判定）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- いずれの関数もルックアヘッドバイアス対策として内部で `date.today()` 等を盲目的に参照しない設計になっています（呼び出し側が target_date を明示することを推奨）。
- OpenAI API 呼び出しを行う機能を使う場合は必ず `OPENAI_API_KEY` を設定してください。API レート制限やエラーは内部でリトライ・フォールバックしますが、コストに注意してください。

---

## 設定（環境変数の詳細）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client.get_id_token() のために必要。

- OPENAI_API_KEY (必要に応じて)  
  news_nlp / regime_detector など OpenAI を使用する処理で必要。

- KABU_API_PASSWORD, KABU_API_BASE_URL  
  kabu ステーションAPIに接続する場合に使用。

- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb

- その他:
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - KABUSYS_ENV (development|paper_trading|live)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

config.Settings クラス経由でアクセスできます（例: from kabusys.config import settings）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント解析（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント & DuckDB 保存
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL インターフェース再エクスポート
    - news_collector.py       — RSS 収集・前処理・保存
    - calendar_management.py  — 市場カレンダー、営業日ロジック
    - quality.py              — データ品質チェック
    - stats.py                — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログ（テーブルDDL・初期化）
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum, value, volatility）
    - feature_exploration.py  — 将来リターン、IC、統計サマリー等

---

## トラブルシューティング（よくある問題）

- 環境変数が見つからない / ValueError が出る  
  - settings の必須プロパティは環境変数が未設定だと ValueError を送出します。`.env` を作成し必要なキーをセットしてください。自動ロードされない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認。

- OpenAI / J-Quants の認証エラー  
  - トークンや API キーが正しいか確認。J-Quants は refresh token → id token の流れがあります（get_id_token）。jquants_client は 401 を検出した場合一度自動リフレッシュします。

- DuckDB テーブルがない / SQL エラー  
  - 初回は schema を作成するユーティリティや migration が必要です（audit などは init_audit_schema / init_audit_db を参照）。ETL の前にスキーマ初期化を行ってください。

- RSS 取得でファイル取得に失敗する / SSRF ブロックに引っかかる  
  - news_collector はリダイレクト先のスキーム・プライベートアドレスを厳密にチェックします。RSS URL が正しく外部ホストを指しているか確認してください。

---

## 開発・テスト

- 単体テストやモックを利用して OpenAI / J-Quants 呼び出しを差し替える設計になっています（各モジュールで呼び出し箇所を patch 可能）。
- 環境変数の自動ロードはプロジェクトルート判定（.git / pyproject.toml）に依存します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にすると .env の自動読み込みを抑制できます。

---

この README はコードベースの主要機能と利用方法を簡潔にまとめたものです。詳細は各モジュール（src/kabusys/**）の docstring を参照してください。必要であれば、セットアップのスクリプト例や Docker 化の手順、CI 設定例などの追加ドキュメントも作成できます。