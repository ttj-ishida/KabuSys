# KabuSys

KabuSys は日本株のデータパイプライン、機械学習支援（ニュース NLP 等）、ファクター研究、監査ログ、及び取引判定補助ロジックを備えた自動売買／リサーチ基盤ライブラリです。本リポジトリは主に DuckDB をデータ層に用い、J-Quants / RSS / OpenAI 等外部サービスを統合して日次 ETL やニュースセンチメント評価、ファクター計算、マーケットレジーム判定などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける設計（内部で date.today() 等に依存しない）
- DuckDB を用いた高速なローカル分析
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを実装
- 冪等性を重視した ETL / DB 書き込み（ON CONFLICT / idempotent）

---

## 機能一覧

- データ ETL / 管理（J-Quants 経由）
  - 日次株価（OHLCV）取得・保存（差分更新、ページネーション対応）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - ETL の品質チェック（欠損・重複・スパイク・日付不整合）
  - ニュース収集（RSS）と前処理（SSRF 対策、URL 正規化、トラッキング除去）
- ニュース NLP / AI
  - 銘柄ごとのニュースセンチメント評価（OpenAI を用いたバッチ評価）
  - マクロニュースに基づく市場レジーム（bull / neutral / bear）判定
  - レスポンスのバリデーション・リトライ制御
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - シグナル → 発注 → 約定までのトレーサビリティテーブルと初期化ユーティリティ
  - order_request_id を冪等キーとして採用
- ユーティリティ
  - マーケットカレンダー操作（営業日判定 / 前後営業日取得 / 期間内営業日列挙）
  - J-Quants クライアント（レートリミット・トークン自動リフレッシュ・保存関数）
  - DuckDB 用スキーマ初期化ヘルパー

---

## 前提条件

- Python 3.10+
- 必要なライブラリ（例）
  - duckdb
  - openai (OpenAI Python client)
  - defusedxml
  - その他標準ライブラリ以外の依存がある想定（requests 等はコードベースで urllib を使用）

（requirements.txt はプロジェクトに合わせて作成してください）

---

## インストール（開発環境）

1. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

2. パッケージをインストール（プロジェクトルートに pyproject.toml / setup.py がある想定）
   ```
   pip install -e .
   # 必要な追加パッケージ（例）
   pip install duckdb openai defusedxml
   ```

---

## 環境変数 / 設定

KabuSys は環境変数（または .env / .env.local）から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から .env → .env.local の順で行われます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（Settings により要求されるもの）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（通知用、必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に参照）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（データベース初期化等）

1. DuckDB データベースファイル用ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

2. 監査ログ DB の初期化（Python から）
   ```python
   import kabusys.data.audit as audit
   conn = audit.init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

3.（任意）アプリケーション設定の確認
   ```python
   from kabusys.config import settings
   print(settings.duckdb_path, settings.env, settings.is_live)
   ```

---

## 基本的な使い方（例）

- 日次 ETL を実行（DuckDB 接続を渡す）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント評価（1 日分）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  # OPENAI_API_KEY を環境変数に設定しておくか、score_news に api_key を渡す
  ```

- マーケットレジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect(str("data/kabusys.duckdb"))
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- マーケットカレンダー操作
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  conn = duckdb.connect(str("data/kabusys.duckdb"))
  is_trade = is_trading_day(conn, date(2026, 3, 20))
  nxt = next_trading_day(conn, date(2026, 3, 20))
  ```

ログやエラーは Settings.log_level に従って出力されます。OpenAI / J-Quants の API 呼び出しはリトライやフェイルセーフが組み込まれていますが、APIキーやトークンは正しく設定してください。

---

## 開発者向けノート

- 自動で .env をロードする機能はプロジェクトルートを .git / pyproject.toml で探索します。テストでロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して下さい。
- OpenAI 呼び出し関数やネットワーク I/O 部分はテスト時にモックしやすいように内部の呼び出しをラップしています（例: kabusys.ai.news_nlp._call_openai_api を patch する等）。
- DuckDB への executemany に空リストを渡すとエラーになるバージョンがあるため、コードでは空チェックを行っています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント評価ロジック
    - regime_detector.py           — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得 / 保存）
    - pipeline.py                  — ETL パイプラインの実装（run_daily_etl など）
    - etl.py                       — ETLResult 再エクスポート
    - quality.py                   — データ品質チェック
    - news_collector.py            — RSS ニュース収集（SSRF 対策・正規化）
    - calendar_management.py       — マーケットカレンダー管理・営業日判定
    - stats.py                      — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                      — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー等
  - ai, data, research などのユニットは相互に依存しつつも、API 呼び出し部は分離してテストしやすい設計になっています。

---

## 貢献・ライセンス

本 README はコードベースに基づく概要と使い方をまとめたものです。実運用／本番発注を行う前に、必ず各モジュールのログ・トランザクション・例外ハンドリング・テストケースを確認してください。ライセンスはリポジトリの LICENSE を参照してください。

もし追加で「セットアップの自動化（systemd / cron ジョブ例）」「Docker 化」「requirements.txt の推奨一覧」「拡張機能（kabu ステーションとの実際の発注フロー）」などのセクションが必要であれば、用途に合わせて追記します。