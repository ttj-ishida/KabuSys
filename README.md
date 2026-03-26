# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、バックテストおよび運用に必要な機能群を提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得・ETL
  - J-Quants API からの株価日足 / 財務データ / 市場カレンダー取得（ページネーション・レート制御・リトライ・トークン自動リフレッシュ）
  - DuckDB への冪等保存（ON CONFLICT / INSERT … DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）

- ニュース収集・NLP
  - RSS 取得・前処理、raw_news 保存（SSRF / Gzip / サイズ制限 / トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント集約（score_news）
  - マクロ記事を用いた市場レジーム判定（ETF 1321 の MA200 と LLM を合成、score_regime）

- 研究（Research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- データ品質チェック
  - 欠損データ、スパイク（前日比）、主キー重複、日付不整合（未来日付・非営業日データ）を検出し QualityIssue を返す

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定までのトレーサビリティ用テーブル定義・初期化ユーティリティ（init_audit_db / init_audit_schema）

- 設定管理
  - .env または環境変数から設定を自動ロード（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
  - 環境変数の厳格チェック（必須項目の検証、KABUSYS_ENV / LOG_LEVEL のバリデーション）

---

## セットアップ手順

前提
- Python 3.10+（型ヒントで | 型を使用しているため）
- OpenAI API キー（LLM を使用する場合）
- J-Quants のリフレッシュトークン（データ ETL を行う場合）

1. リポジトリをクローンしてプロジェクトディレクトリへ移動します。

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール
   - 最低限必要な外部依存:
     - duckdb
     - openai
     - defusedxml
   ```
   pip install duckdb openai defusedxml
   ```
   プロジェクトを editable インストールできる場合は:
   ```
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可）。
   - 主要な環境変数（必須）:

     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（運用時）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

   - 任意 / デフォルトあり:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABUS_API_BASE_URL: kabu API の base（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

   - `.env` の例:
     ```
     JQUANTS_REFRESH_TOKEN="xxxxxxx"
     OPENAI_API_KEY="sk-..."
     KABU_API_PASSWORD="your_kabu_password"
     SLACK_BOT_TOKEN="xoxb-..."
     SLACK_CHANNEL_ID="C12345678"
     DUCKDB_PATH="data/kabusys.duckdb"
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（簡易ガイド）

以下はライブラリをプログラムから呼び出す一例です。実行前に必要な環境変数や DB（DuckDB ファイル）を用意してください。

- DuckDB に接続して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを生成（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（1321 MA200 とマクロ記事の LLM を統合）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ユーティリティ（ファクター計算例）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, date(2026, 3, 20))
  ```

注意:
- LLM 呼び出しはコストとレート制限が発生します。テスト時は内部の _call_openai_api をモックして外部呼び出しを無効化できます（unittest.mock.patch を利用）。
- データベースのテーブルスキーマはアプリ側で作成する前提です（ETL や各モジュールは既存テーブルを参照します）。ETL 実行前にスキーマ初期化スクリプトが必要な場合があります（本 README はスキーマ DDL を含みませんが、各モジュールに SQL が含まれています）。

---

## 実装上の注意点 / 設計ポリシー（抜粋）

- Look-ahead バイアス防止：
  - 各モジュールは date.today() / datetime.today() を直接参照せず、呼び出し側から target_date を明示的に渡す設計になっています。
  - ETL や LLM スコアリングは target_date 未満のデータのみを参照するように実装されています。

- フェイルセーフ：
  - 外部 API（OpenAI / J-Quants）障害時は可能な限り安全にフォールバック（LLM の失敗時はスコア0.0など）して処理継続する設計になっています。

- 冪等性：
  - 保存処理は可能な限り冪等（ON CONFLICT DO UPDATE / 存在チェックなど）を意識して実装されています。

- セキュリティ：
  - ニュース収集では SSRF 対策、受信サイズ制限、defusedxml を使用した XML パース等の安全対策を実装しています。

---

## ディレクトリ構成（主要ファイル）

（パスはリポジトリの src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（OpenAI）
    - regime_detector.py             — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch / save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL の公開インターフェース（ETLResult）
    - stats.py                       — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py                     — データ品質チェック
    - calendar_management.py         — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py              — RSS 収集と前処理
    - audit.py                       — 監査ログテーブルの定義・初期化
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum/value/volatility）
    - feature_exploration.py         — 将来リターン、IC、統計サマリー
  - ai/__init__.py
  - research/__init__.py
  - data/__init__.py

各モジュールは docstring に処理フロー・設計方針・想定する DB テーブルを記載しています。詳細は該当ファイルのドキュメントを参照してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須: ETL 用)
- OPENAI_API_KEY (必須: news_nlp/regime_detector を使う場合)
- KABU_API_PASSWORD (必須: 発注連携等)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須: Slack 通知を使う場合)
- SLACK_CHANNEL_ID (必須: 同上)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化します

---

## テスト / 開発ヒント

- OpenAI 呼び出しは _call_openai_api を patch してモック化することが想定されています。ユニットテストでは外部 API へのアクセスを避けるためにモックを使用してください。
- DuckDB を使ったユニットテストでは ":memory:" 接続を利用できます（init_audit_db などは ":memory:" に対応しています）。
- ETLResult / QualityIssue はデバッグログやアサーションに便利です。

---

## 最後に

この README はコードベースの概要・使い方・設計方針の要点をまとめたものです。各モジュールの詳細な使用方法やテーブルスキーマ、DB 初期化 SQL などはソース内 docstring を参照してください。質問や追加のドキュメント化が必要であればお知らせください。