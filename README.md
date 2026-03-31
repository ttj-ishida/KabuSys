# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ

本リポジトリは「KabuSys」と呼ばれる日本株のデータ取得・前処理・研究・AIスコアリング・監査ログ機能を提供する Python パッケージです。J-Quants API や OpenAI を利用したニュースセンチメント評価、DuckDB を用いた ETL/品質チェック、監査ログ（発注／約定のトレーサビリティ）など、投資運用のための基盤処理群を含みます。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() に依存しない設計）
- 冪等性（ETL／DB保存は ON CONFLICT で上書き）
- フェイルセーフ（外部 API 失敗時はスキップやゼロフォールバック）
- 再利用しやすい DuckDB ベース API（テスト容易性を重視）

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）／Settings クラスでアクセス
- データ取得・ETL（J-Quants API）
  - 日次株価（OHLCV）、財務データ、マーケットカレンダーの差分取得・保存
  - レートリミット・リトライ・トークン自動更新等の堅牢な HTTP クライアント
- ニュース収集
  - RSS からのニュース収集、URL 正規化、SSRF 対策、raw_news/ news_symbols への格納設計
- AI 活用
  - ニュース NLP（gpt-4o-mini を想定）による銘柄別センチメントスコアリング（score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアを合成：score_regime）
  - API 呼び出しは堅牢にリトライ・バックオフ対応
- リサーチ／ファクターエンジン
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
  - Z スコア正規化ユーティリティ
- データ品質チェック
  - 欠損、重複、スパイク（前日比）、日付整合性チェック（run_all_checks）
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化
  - init_audit_db / init_audit_schema で DuckDB に監査スキーマを作成

---

## セットアップ手順

前提:
- Python 3.9+（typing の新表記を使用）
- OS によっては libssl 等のネイティブ依存が必要な場合があります（OpenAI, urllib 等に伴う）。

1. リポジトリをチェックアウトしてインストール（開発インストール推奨）
   ```
   git clone <this-repo>
   cd <this-repo>
   pip install -e .
   ```

2. 必要な依存パッケージ（代表例）
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトの requirements.txt がある場合はそちらを利用してください。）

3. 環境変数（.env ファイル）
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な必須/推奨環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token 用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携用）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
     - DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）デフォルトあり
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視設定

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース準備（監査DB の初期化例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（簡単な例）

以降は Python スクリプト / コンソールから呼び出す例です。すべての関数は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- Settings による設定取得
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコアリング（score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  status = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  print("完了:", status)
  ```

- 監査スキーマ初期化（既存 DB への追加）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema
  conn = duckdb.connect(str(settings.duckdb_path))
  init_audit_schema(conn, transactional=True)
  ```

- データ品質チェックの実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

注意点:
- OpenAI 呼び出しは gpt-4o-mini（JSON Mode）想定。API の失敗は安全側で macro_sentiment=0 やスキップで継続します。
- J-Quants API はレート制限（120 req/min）に対応した内部 RateLimiter を使用します。
- ETL / 保存は冪等性を考慮しています（ON CONFLICT DO UPDATE 等）。

---

## ディレクトリ構成（主要ファイル/モジュール）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings（J-Quants / kabu / Slack / DB / 監視設定）
- ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメントの LLM スコアリング（score_news）
  - regime_detector.py  — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（is_trading_day / next_trading_day 等）
  - etl.py                — ETL のインターフェース再エクスポート
  - pipeline.py           — 日次 ETL の実装（run_daily_etl, run_prices_etl, ...）
  - stats.py              — zscore_normalize 等の統計ユーティリティ
  - quality.py            — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py              — 監査ログスキーマ初期化 / init_audit_db
  - jquants_client.py     — J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py     — RSS ニュース収集・正規化・保存
- research/
  - __init__.py
  - factor_research.py    — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py— 将来リターン / IC / 統計サマリー 等
- research.* 他ユーティリティ参照

（上記以外に execution / monitoring / strategy 等のパッケージが __all__ に列挙されていますが、このコードスニペットの範囲外で実装されます）

---

## 運用上の注意 / ベストプラクティス

- 環境変数は機密情報を含みます。`.env` は git 管理下に置かないこと（.gitignore を利用）。
- 本ライブラリは実行環境（特に実運用での約定/発注）での利用を想定しているため、発注周りは別途リスク管理層を実装してください。
- OpenAI / J-Quants の API キーはレート・料金・利用ポリシーに注意して運用してください。
- DuckDB のパスはバックアップ/スナップショットポリシーに沿って管理してください。
- テスト時は自動 .env ロードを無効化できます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）および _call_openai_api 等の内部呼び出しはモック可能です。

---

## 参考 / 連絡

この README はリポジトリ内のコードコメント・ドキュメント文字列に基づいて作成しています。詳細な設計は各モジュールの docstring を参照してください。質問や不明点があれば、開発チームにお問い合わせください。

--- 

（必要ならばサンプル .env.example、requirements.txt、起動用スクリプトなどを別途作成してください。）