# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（注文→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得・ETL
  - J-Quants API からの株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得（ページネーション・リトライ対応）
  - DuckDB への冪等保存（ON CONFLICT / INSERT/UPDATE）
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、主キー重複、日付整合性チェック
- ニュース収集
  - RSS フィードの取得・前処理・SSRF 対策・トラッキングパラメータ除去・raw_news への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に投げ、センチメントスコアを ai_scores に保存（バッチ・リトライ・レスポンス検証）
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次で bull/neutral/bear を判定・保存
- リサーチ用ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Z スコア正規化等
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルを含む監査スキーマの初期化ユーティリティ（DuckDB）
  - 発注フローのトレーサビリティ確保（UUID ベース、created_at UTC、冪等キー）

---

## 前提・依存関係

主な Python パッケージ（抜粋）:

- duckdb
- openai (OpenAI Python SDK)
- defusedxml

その他、標準ライブラリで多くを実装しています。requirements.txt を用意している場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリを取得する（例）
   - git clone <リポジトリ_URL>
   - cd <repo>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発中であれば）pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml の位置）に `.env` / `.env.local` を置くと自動読み込みされます（優先順: OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効化するには: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 認証）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等）
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（必要に応じて）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視関連）

   - .env の例（簡易）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（簡易サンプル）

以下は主要な機能を Python から呼び出す例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続を作る例:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI 必須）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数を渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  ret = score_regime(conn, target_date=date(2026, 3, 20))
  print("完了", ret)
  ```

- 監査ログ DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 設定値参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)          # Path オブジェクト
  print(settings.is_live, settings.log_level)
  ```

---

## 注意点 / 設計上のポイント

- Look-ahead バイアス回避:
  - 多くの関数は date.today() 等に依存せず、呼び出し側が target_date を明示的に渡す設計です。バックテスト等での使用時は target_date を適切に渡してください。
- OpenAI 呼び出し:
  - news_nlp / regime_detector は OpenAI の JSON Mode を利用し、レスポンスのバリデーションを行います。API 失敗時はフェイルセーフ（スコア 0.0 など）で継続する実装です。
- ETL の堅牢性:
  - J-Quants API 呼び出しはリトライ・レートリミット制御（120 req/min）・トークン自動リフレッシュ等を実装しています。
- DB 操作は冪等性を重視（ON CONFLICT 等）しています。部分失敗時のデータ保護を考慮した実装が各所にあります。

---

## ディレクトリ構成

主要ファイル・モジュールの配置（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py       — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch / save）
    - pipeline.py              — ETL パイプライン（run_daily_etl など）
    - etl.py                   — ETLResult 再エクスポート
    - calendar_management.py   — マーケットカレンダー管理
    - news_collector.py        — RSS ニュース収集（SSRF 対策等）
    - quality.py               — データ品質チェック
    - stats.py                 — 統計ユーティリティ（zscoreなど）
    - audit.py                 — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py       — Momentum / Value / Volatility 等
    - feature_exploration.py   — 将来リターン・IC・統計サマリー
  - ai/ (上記)
  - その他: strategy/ execution/ monitoring の名前空間が __all__ に定義されていますが、今回のコード抜粋では詳細実装が存在しない可能性があります。

（フルツリーはリポジトリを参照してください。README は主要モジュールに焦点を当てています。）

---

## トラブルシューティング

- 環境変数が見つからない（ValueError）
  - config.Settings は必須の環境変数が未設定だと ValueError を投げます。`.env` を作成するか、OS 環境変数に設定してください。
- OpenAI 呼び出し失敗
  - API キーが無効、レート制限、ネットワークエラーなどが原因になり得ます。news_nlp / regime_detector は失敗時にスコアを安全にフォールバックする設計ですが、ログを確認してください。
- DuckDB 接続・SQL エラー
  - スキーマが未作成の場合は save_* 関数で期待通りのテーブルがないと失敗することがあります。必要なスキーマ初期化（audit.init_audit_schema 等）を実行してください。

---

## 参考

- 環境設定ファイルの自動読み込み:
  - プロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（ただしテスト等で無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
  - 読み込み順: OS 環境変数 > .env.local > .env
- OpenAI: gpt-4o-mini を想定した JSON Mode を利用する実装が含まれます。API の仕様変更に注意してください。
- J-Quants API: rate limit と認証（refresh token → id token）の扱いを内包しています。J-Quants の利用規約・API ドキュメントを参照してください。

---

必要であれば、README に「インストール可能な requirements.txt」「例の .env.example」「より詳細な API 使用例（各関数のパラメータ詳細）」を追加できます。どの部分を拡張しますか？