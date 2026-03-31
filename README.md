# KabuSys

KabuSys は日本株向けのデータ基盤とリサーチ / 自動売買補助ライブラリ群です。  
J-Quants からのデータ ETL、ニュース収集と LLM を用いたニュース・センチメント解析、市場レジーム判定、ファクター計算、監査ログ（発注／約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ収集 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得して DuckDB に保存（冪等）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース処理
  - RSS 取得、前処理、SSRF 対策、raw_news への保存（冪等）
  - 銘柄単位に集約して LLM（OpenAI）でセンチメントを算出し ai_scores に保存
- AI モジュール
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（ETF 1321 の MA200 + マクロニュースの LLM スコアを合成 → bull/neutral/bear）
  - OpenAI 呼び出しはリトライ・タイムアウト等の考慮済み
- リサーチ / ファクター
  - モメンタム、ボラティリティ、バリュー等の定量指標計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクターの統計サマリー
  - Z スコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions を中心とした監査テーブルを DuckDB に初期化
  - 発注ワークフローのトレーサビリティ（UUID ベース）を提供
- J-Quants クライアント
  - レート制御、認証（リフレッシュ）、ページネーション、保存用のユーティリティを実装
- 設定・環境変数管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定は Settings 経由で取得・検証

---

## 必要条件（推奨）

- Python 3.10+
- 必要なパッケージ（抜粋）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで多くを実装していますが、OpenAI クライアントや duckdb は必要です）

プロジェクトに requirements.txt がない場合は上記を手動でインストールしてください。

例:
```
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると、自動で読み込まれます（ただしテスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に使用
     - DUCKDB_PATH: データ用 DuckDB のファイルパス（デフォルト `data/kabusys.duckdb`）
     - SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV: `development` / `paper_trading` / `live`
     - LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`

5. データベース・監査テーブル初期化（必要に応じて）
   - 監査ログ用の DuckDB を初期化するサンプル:
     ```python
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db(settings.duckdb_path)
     # conn は duckdb.DuckDBPyConnection
     ```

---

## 使い方（例）

以下は代表的な API の使用例です。いずれも duckdb 接続（kabusys.settings で指定されたパス等）を渡して実行します。

- ETL（日次パイプライン）を実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```

- 市場レジーム判定を実行（1321 MA200 + マクロニュース）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（テーブル群）初期化（既存 DB にスキーマを作成）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect(str("data/kabusys.duckdb"))
  init_audit_schema(conn, transactional=True)
  ```

- 設定値の参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

注意:
- AI 機能（score_news / score_regime）は OpenAI API キー（OPENAI_API_KEY）または api_key 引数が必要です。未設定だと ValueError が送出されます。
- ETL / API 呼び出しはネットワークや認証に依存するため、例外処理やログを適切に行ってください。

---

## 自動環境変数読み込みについて

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` と `.env.local` を自動読み込みします（OS 環境変数が優先、.env.local は上書き）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利です）。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/__init__.py
  - パッケージ初期化、公開サブパッケージ宣言
- src/kabusys/config.py
  - 環境変数 / 設定管理（Settings）
  - .env 自動ロードロジック
- src/kabusys/ai/
  - news_nlp.py: ニュースの LLM ベースセンチメント解析（score_news）
  - regime_detector.py: ETF 1321 の MA200 とマクロニュースを使った市場レジーム判定（score_regime）
- src/kabusys/data/
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - jquants_client.py: J-Quants API クライアント（取得 & DuckDB への保存）
  - news_collector.py: RSS 取得・前処理・保存ロジック（SSRF 対策等）
  - calendar_management.py: 市場カレンダー管理・営業日判定
  - stats.py: 汎用統計ユーティリティ（zscore_normalize）
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py: 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - etl.py: ETL 公開インターフェース（ETLResult エクスポート）
- src/kabusys/research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py: 将来リターン、IC、統計サマリー等
  - __init__.py: 主要関数の再エクスポート
- src/kabusys/ai/__init__.py
  - AI 関連公開関数のエクスポート（score_news）

（各ファイルは docstring に設計方針・挙動・フォールバックを詳述しています）

---

## 開発上の注意・ベストプラクティス

- Look-ahead bias 回避:
  - 多くのモジュールは内部で date.today() を直接参照しない設計です。必ず target_date を引数で渡して処理してください。
- DuckDB の executemany には空リストを渡さない（コード内で対策済み）。
- 外部 API 呼び出しはリトライやバックオフを備えていますが、レート制限やネットワーク障害に対する適切な監視を行ってください。
- OpenAI 呼び出しのテストは内部の _call_openai_api をモックすることで可能です（各モジュールに記載あり）。
- .env の扱い:
  - OS 環境変数を優先し、.env.local は .env を上書きします。機密情報は .env.local に置き、リポジトリにコミットしないでください。

---

## ライセンス・貢献

この README はコードベースの概要説明です。実際の利用・配布に際してはプロジェクトの LICENSE ファイルや貢献ガイドラインを参照してください。

---

ご要望があれば、README にサンプル .env.example、詳細なクイックスタートスクリプト、ユニットテストの実行方法などを追加します。どの情報を追加しますか？