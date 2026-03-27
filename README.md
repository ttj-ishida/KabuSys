# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
データ収集（J-Quants / RSS）、品質チェック、ETL、AI（ニュースセンチメント・市場レジーム判定）、リサーチ用ファクター計算、監査ログの初期化などを含むモジュール群を提供します。

主な用途：
- J-Quants からの株価・財務・カレンダー取得と DuckDB への永続化（ETL）
- RSS ニュース収集と銘柄紐付け
- OpenAI を用いたニュースセンチメント算出・市場レジーム判定
- ファクター計算・特徴量解析（研究用途）
- 発注・約定に関する監査テーブル初期化（トレーサビリティ）

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートを検索）
  - 必須環境変数の取得・検証
- データ取得 / ETL
  - J-Quants API クライアント（レート制限・リトライ・トークン自動更新対応）
  - 差分 ETL（株価/財務/カレンダー）、バックフィル
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース処理
  - RSS フィード収集（SSRF 対策、トラッキング除去、前処理）
  - ニュース -> 銘柄紐付け -> ai_scores への書き込み
- AI（OpenAI 経由）
  - ニュースセンチメント（銘柄ごと）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
  - 冪等・フォールバックロジック・リトライ実装
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z-score 正規化
- 監査（Audit）
  - signal_events / order_requests / executions テーブル DDL とインデックス定義
  - 監査DB初期化ユーティリティ（UTC タイムゾーン固定）

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意
   - 仮想環境を作成することを推奨します。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がない場合は主要パッケージをインストールしてください（例）:
     - pip install duckdb openai defusedxml

   - 開発環境として editable インストール（パッケージを配布する場合）:
     - pip install -e .

3. 環境変数を設定
   - プロジェクトルートの .env（または .env.local）に必要な環境変数を記述します。
   - 自動ロードはデフォルトで有効。無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN = <J-Quants リフレッシュトークン>
   - KABU_API_PASSWORD = <kabuステーション API パスワード>
   - SLACK_BOT_TOKEN = <Slack Bot Token>
   - SLACK_CHANNEL_ID = <Slack チャンネル ID>
   - OPENAI_API_KEY = <OpenAI API Key>  ※score_news / score_regime に必要
   - DUCKDB_PATH = data/kabusys.duckdb
   - SQLITE_PATH = data/monitoring.db
   - KABUSYS_ENV = development | paper_trading | live
   - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL

   注意: settings モジュールが未設定の必須変数は起動時に ValueError を投げます。

4. データベース用ディレクトリ作成
   - settings.duckdb_path の親ディレクトリを作成しておくか、モジュール側で自動作成されます。

---

## 使い方（例）

以下は代表的なユースケースの Python スニペットです。

- DuckDB 接続を作成して日次 ETL を実行する
  - run_daily_etl は ETLResult を返します。

  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に書き込む
  - OpenAI API キーは OPENAI_API_KEY または api_key 引数で指定。

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
  print(f"書き込み銘柄数: {count}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キー必須
  ```

- 監査ログ用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn = init_audit_db(settings.sqlite_path)  # または別ファイルパス
  ```

- リサーチ用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  ```

注意点：
- OpenAI 呼び出しは API エラー時にフォールバックやリトライを行いますが、API キーが未設定だと ValueError が発生します。
- ETL / API 呼び出しは外部ネットワークと I/O を伴います。ローカルテスト時はモック化を推奨します。

---

## ディレクトリ構成（主要ファイル）

（package ルート: src/kabusys/ 以下）

- __init__.py
- config.py
  - 環境変数読み込み・設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント算出（score_news）
  - regime_detector.py  — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（fetch / save 関数群）
  - pipeline.py         — ETL パイプライン実装（run_daily_etl 他）
  - etl.py              — ETLResult 型の再エクスポート
  - news_collector.py   — RSS フィード収集・前処理
  - quality.py          — データ品質チェック（各チェック関数）
  - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - audit.py            — 監査テーブル DDL / 初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py  — Momentum / Value / Volatility 等
  - feature_exploration.py — 将来リターン / IC / summary / rank

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取る関数を多く提供します。DB 操作は SQL を直接実行しており、外部 API 呼び出しは jquants_client / OpenAI クライアント経由で行われます。

---

## 設定・運用の補足

- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml をルート判定）から .env と .env.local を自動読み込みします。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- 環境（KABUSYS_ENV）
  - 有効値: development / paper_trading / live
  - settings.is_live / is_paper / is_dev で判定可能

- ログレベル
  - LOG_LEVEL 環境変数で設定（DEBUG / INFO / WARNING / ERROR / CRITICAL）

- セキュリティ注意事項
  - news_collector は SSRF 対策・レスポンスサイズ制限・XML パースの安全対策を実装していますが、外部 URL 取得は運用者の責任で管理してください。
  - OpenAI / J-Quants API キーは適切に保護してください（.env を .gitignore に登録）。

---

README に記載の無い内部実装や拡張点について知りたい場合は、特定のモジュール・関数名を指定して質問してください。