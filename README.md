# KabuSys

日本株向けのデータプラットフォーム＆自動売買支援ライブラリ（部分実装）。  
このリポジトリはデータ収集（J-Quants）、ETL、データ品質チェック、監査ログ、ニュースに対する LLM ベースのセンチメント評価、リサーチ／ファクター計算などのユーティリティ群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引やリサーチでよく使う処理をまとめた内部ライブラリ群です。主に以下の機能を提供します。

- J-Quants API と連携した株価・財務・カレンダーの差分取得（Rate-limit/リトライ/トークン自動更新対応）
- DuckDB を使った ETL パイプライン（差分更新・バックフィル・品質チェック）
- 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
- ニュース収集（RSS）と LLM によるニュースセンチメント計算
- マーケットレジーム判定（ETF MA とマクロニュースの LLM センチメントの合成）
- 監査ログ（signal → order_request → execution）用のスキーマ初期化ユーティリティ
- リサーチ向けのファクター計算・特徴量解析ユーティリティ（モメンタム、ボラティリティ、バリュー、IC 等）
- 汎用統計関数（Zスコアなど）

設計方針:
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を不用意に参照しない）
- 冪等性（ETL/save 関数は基本的に ON CONFLICT / upsert を想定）
- 戻り値やログで安全に継続可能なフォールバックを行う（API失敗時はスキップして進める等）

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API からの取得（prices, financials, calendar など）、DuckDB への保存関数
  - pipeline / etl: 日次 ETL（差分取得・保存・品質チェック）と個別 ETL ヘルパー
  - calendar_management: market_calendar を用いた営業日判定、calendar_update_job
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策、サイズ制限 等）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: シグナルから約定までトレース可能な監査テーブル定義と初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約して OpenAI（JSON Mode）でセンチメントを算出し ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込み
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

（パッケージ階層は src/kabusys 以下を参照）

---

## セットアップ手順

1. システム要件
   - Python 3.9 以上（コードは typing の新記法を使用）
   - DuckDB（Python パッケージ）
   - OpenAI Python SDK（AI 機能を使う場合）
   - defusedxml（RSS パースの安全確保）
   - その他標準ライブラリに依存（urllib 等）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使ってください。
   開発時は pip install -e .（セットアップ済みパッケージ）を利用できます。

4. 環境変数設定
   - 本ライブラリは多数の環境変数を参照します。代表的なもの:

     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須: data.jquants_client.get_id_token）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注系利用時）
     - KABU_API_BASE_URL: kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知用（必須に設定している箇所あり）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV: environment (development / paper_trading / live)
     - LOG_LEVEL: (DEBUG, INFO, WARNING, ERROR, CRITICAL)

   - プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（src/kabusys/config.py が .git または pyproject.toml を探索してプロジェクトルートを検出して読み込みます）。
   - 自動ロードを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定してください。

5. .env の例（プロジェクトルートに置く）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易ガイド）

以下は主要な利用例です。各関数は DuckDB 接続（duckdb.connect(...) が返す接続オブジェクト）を受け取ります。

- DuckDB 接続準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  - run_daily_etl は calendar / prices / financials の差分取得・保存・品質チェックを順次実行します。
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=None)  # target_date を None にすると今日が使われます
  print(result.to_dict())
  ```

- ニュースセンチメント評価（AI）
  - OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または api_key 引数）。
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（AI + ETF MA）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作りたい場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 監査テーブルが作成されます
  ```

- ファクター計算（研究用途）
  ```python
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records: list[dict]（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
  ```

- 統計正規化
  ```python
  from kabusys.data.stats import zscore_normalize

  normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])
  ```

注意点:
- AI 関連関数は OpenAI SDK（JSON mode）を利用します。API レスポンスの失敗やパース失敗時はログに WARNING を出して安全にフォールバックする実装です（ゼロスコア等）。
- jquants_client は API のレート制御とリトライ、401 時のトークン自動更新を行います。JQUANTS_REFRESH_TOKEN の設定が必要です。
- ETL は部分失敗（例: news の取得失敗）でも他処理を継続する設計です。戻り値の ETLResult でエラーや品質問題を確認してください。

---

## ディレクトリ構成

（プロジェクトの src/kabusys 配下の主なファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / 設定管理（.env 自動ロード）
    - ai/
      - __init__.py
      - news_nlp.py                 — ニュースを銘柄ごとに集約して LLM でセンチメント評価、ai_scores に書込
      - regime_detector.py          — ETF MA200 とマクロニュースを合成して市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py           — J-Quants API クライアント（fetch / save / get_id_token 等）
      - pipeline.py                 — ETL パイプライン実装（run_daily_etl を含む）
      - etl.py                      — ETL 型の公開再エクスポート（ETLResult）
      - calendar_management.py      — market_calendar 管理、営業日判定、calendar_update_job
      - news_collector.py           — RSS 収集・前処理（SSRF 対策、ID 正規化）
      - quality.py                  — データ品質チェック（欠損・スパイク・重複・日付不整合）
      - audit.py                    — 監査ログ用テーブル DDL と初期化ユーティリティ
      - stats.py                    — zscore_normalize 等の統計ユーティリティ
    - research/
      - __init__.py
      - factor_research.py          — Momentum / Volatility / Value の計算
      - feature_exploration.py      — 将来リターン計算、IC、factor_summary、rank
    - (その他)
      - strategy/ (パッケージ参照のみ: __all__ に含まれるがコード未提示)
      - execution/ (同上)
      - monitoring/ (同上)

---

## 注意事項 / 補足

- 本 README はリポジトリ内の実装ファイルから仕様を抜粋して作成しています。実運用ではさらに堅牢な設定、テスト、シークレット管理（Vault など）、監視が必要です。
- AI 機能を使う際は API コストとレート制限に注意してください。実装はリトライ/バックオフを備えていますが、費用と制限はプロジェクト運用側で管理してください。
- DuckDB の SQL や型挙動はバージョンに依存する部分があるため、プロジェクトで利用する DuckDB のバージョンを固定することを推奨します。
- news_collector は RSS の XML パースに defusedxml を使い、SSRF 対策やレスポンスサイズチェックなどを実装しています。外部ネットワークアクセス関係の権限設定に注意してください。

---

もし README に追加したいチュートリアル（例: 初回 ETL のフルフロー、監査ログでの発注フロー例、より具体的な .env.example）や、strategy / execution / monitoring パッケージの実装がある場合は、その内容を教えてください。README をさらに具体化します。