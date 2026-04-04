# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリ群です。データの ETL、ニュースの NLP スコアリング、ファクター計算、監査ログ構築、J-Quants / OpenAI / kabu ステーション連携など、取引システム運用に必要なユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

主な目的は以下のとおりです。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と OpenAI を用いた銘柄ごとのニュースセンチメント（ai_scores）算出
- マクロセンチメントと ETF（1321）200日移動平均乖離から市場レジーム（bull/neutral/bear）を判定
- ファクター計算・特徴量探索（モメンタム／バリュー／ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ用テーブル／インデックスの初期化ユーティリティ（発注 → 約定のトレース）

設計上の特徴:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない等）
- API 呼び出しはリトライ / バックオフ / レート制御 を備える
- DuckDB を中心に SQL + Python で効率的に処理
- 自動で .env/.env.local をロード（必要に応じて無効化可能）

---

## 機能一覧

- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）
- ニュース処理
  - RSS 収集（kabusys.data.news_collector）
  - ニュース NLP（kabusys.ai.news_nlp）→ ai_scores テーブルへ書込
- 市場レジーム判定
  - kabusys.ai.regime_detector.score_regime（ETF 1321 とマクロセンチメントを合成）
- リサーチ / ファクター
  - calc_momentum / calc_value / calc_volatility（kabusys.research.factor_research）
  - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
  - zscore_normalize（kabusys.data.stats）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks（kabusys.data.quality）
- 監査ログ（監査テーブルの初期化）
  - init_audit_schema / init_audit_db（kabusys.data.audit）
- 設定管理
  - 環境変数読み込み・検証（kabusys.config.Settings）
  - 自動 .env / .env.local ロード（プロジェクトルート検出）

---

## 必要条件

- Python 3.9+（型ヒントに Path | None などが使われています）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ以外のパッケージがある場合は requirements.txt を参照してください

（プロジェクトに requirements.txt がない場合は上のパッケージをインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （requirements.txt があれば）pip install -r requirements.txt

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）に `.env` を配置すると自動でロードされます（.env.local は .env の後で上書き読み込み）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

推奨される .env に含める主要キー（例）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_api_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  (必要なら)
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO

注意: Settings クラスで必須とされる環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）は未設定だと ValueError を送出します。

---

## 使い方（主なユースケース・コード例）

以下は Python REPL やスクリプトから呼ぶサンプルです。

- DuckDB 接続の準備 / 監査 DB 初期化
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.audit import init_audit_db

  # settings.duckdb_path は Path オブジェクト
  conn = duckdb.connect(str(settings.duckdb_path))

  # 監査ログ用のテーブルを初期化して接続を取得する（ファイルがなければ作成）
  audit_conn = init_audit_db(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # conn は DuckDB 接続、OPENAI_API_KEY は環境変数または引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（OpenAI を使用）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

※ OpenAI 呼び出しを行う機能（news_nlp, regime_detector）は OPENAI_API_KEY を参照します。キーを引数で直接渡すことも可能です。

---

## 設定管理（自動 .env 読込の挙動）

- 起動時にパッケージファイル位置からプロジェクトルートを探索し、.env → .env.local の順で読み込みます。OS 環境変数が優先されます。
- テストや明示的制御のために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。
- 設定は kabusys.config.settings 経由で取得できます（プロパティごとにバリデーションあり）。

---

## 重要な注意点

- OpenAI（gpt-4o-mini）や J-Quants への API 呼び出しには個別の API キーが必要です。キーの管理は .env または環境変数で行ってください。
- DuckDB のスキーマやテーブルは ETL 実行前に作成しておく必要があります（プロジェクト側で schema 初期化ユーティリティが提供されている場合はそれを使用してください）。
- ETL / API 呼び出しはネットワークや外部サービスに依存するため、適切なエラーハンドリング・ログ監視を行ってください。
- リアルマネーでの運用を行う場合は paper_trading/live 等の環境設定を正しく行い、安全措置（発注冪等、監査、kill flag、PID 管理等）を徹底してください。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ定義（公開モジュール一覧）
  - config.py — 環境変数 / 設定管理（.env 自動ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（銘柄別センチメント計算、OpenAI 連携）
    - regime_detector.py — 市場レジーム判定（ETF + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL インターフェース再エクスポート（ETLResult）
    - news_collector.py — RSS 収集と raw_news 保存ロジック
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック
    - audit.py — 監査ログテーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - monitoring/ (未列挙の場合もあり) — 実行監視・プロセス管理関連モジュール
  - execution/, strategy/ など — 実行・戦略層の抽象（将来的に拡張）

---

## サポート / 連絡

この README はコードベースに基づいた概要・使い方をまとめたものです。具体的な導入・運用に関してはログ出力・例外メッセージ、各モジュールのドキュメント文字列（docstring）を参照してください。追加のドキュメントや要望があればお知らせください。

--- 

（以上）