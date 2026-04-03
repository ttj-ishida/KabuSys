# KabuSys

KabuSys は日本株向けのデータプラットフォーム／アルゴリズム取引支援ライブラリです。J-Quants からのデータ取得（ETL）、ニュース収集・NLP によるセンチメントスコアリング、研究（ファクター計算）および監査ログ／実行管理のためのユーティリティを提供します。

主な設計方針:
- Look‑ahead bias を防ぐ（内部で date.today()/datetime.now() を直接参照しない設計が多い）
- DuckDB をデータストアとして利用（ローカル / in‑memory）
- API 呼び出しはリトライ・レートリミッティングを実装
- 機能はモジュール単位で分離（ETL、データ品質、NLP、研究、監査ログ、etc.）

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API から日足（OHLCV）や財務データの差分取得・保存（kabusys.data.pipeline）
  - 市場カレンダー取得・更新（kabusys.data.calendar_management）
  - ETL 結果の集約（ETLResult 型）

- データ品質 / 管理
  - 欠損値・スパイク・重複・日付不整合チェック（kabusys.data.quality）
  - 汎用統計ユーティリティ（zscore_normalize 等）（kabusys.data.stats）
  - ニュース収集（RSS → raw_news）（kabusys.data.news_collector）
  - J-Quants API クライアント（kabusys.data.jquants_client）

- 監査 / 実行管理
  - 監査テーブル定義と初期化（init_audit_schema / init_audit_db）（kabusys.data.audit）
  - 実行（プロセス）監視設定（kabusys.config）

- AI / NLP
  - ニュースを銘柄毎にまとめて LLM に投げ、センチメントを ai_scores テーブルに書き込む（kabusys.ai.news_nlp）
  - マクロニュースと ETF（1321）200日MA乖離を組み合わせて市場レジーム判定（kabusys.ai.regime_detector）
  - OpenAI API（gpt-4o-mini）を用いた JSON Mode 呼び出し（リトライ・フォールバック実装）

- 研究（Research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算（kabusys.research）
  - 将来リターン計算、IC 計算、ファクター統計サマリー

---

## セットアップ手順

※ 以下は最小限の手順例です。プロジェクトで使う Python バージョンや仮想環境は適宜調整してください。

1. Python（3.10+ 推奨）をインストールし、仮想環境を作成・有効化します。
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要な依存パッケージをインストールします。コードベースから参照される代表的なパッケージ:
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

   ※ 実運用では requirements.txt や Poetry / PDM を用いて固定化してください。

3. パッケージを開発モードでインストール（プロジェクトルートが pyproject.toml を持つ想定の場合）:
   ```
   pip install -e .
   ```

4. 環境変数を設定します。プロジェクトルートに `.env` または `.env.local` を置くと自動でロードされます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。主要な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector で使用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注等を実装する場合）
   - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
   - KABUSYS_ENV: environment ('development'|'paper_trading'|'live'、デフォルト development)
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知に使用する場合

   例 .env（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

---

## 使い方（主な API 例）

以下は代表的な使い方例です。DuckDB の接続は `duckdb.connect(<path>)` で取得します。

- 日次 ETL を実行する（prices / financials / calendar + 品質チェック）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントを計算して ai_scores に保存（OpenAI API 必須）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM）:
  ```python
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用 DuckDB を初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降、conn を使って監査テーブルが利用可能
  ```

- 研究用ファクター計算の呼び出し:
  ```python
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  # momentum は辞書リストで返る
  ```

---

## 自動 .env ロードの挙動

- パッケージ読み込み時に `.env` と `.env.local` を自動で読み込みます（順序: OS 環境変数 > .env.local > .env）。
- 自動ロードはパッケージルート（.git または pyproject.toml のあるディレクトリ）基準で行います。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env のパースはシェル風の `export KEY=val`/quoting/# コメント等に対応しています。

---

## 主要な設定キー（Settings API）

kabusys.config.settings 経由でアクセスできます。いくつかのプロパティ例:

- settings.jquants_refresh_token  (必須)
- settings.kabu_api_password
- settings.kabu_api_base_url (default: http://localhost:18080/kabusapi)
- settings.line_channel_access_token, settings.line_user_id
- settings.duckdb_path (Path, default "data/kabusys.duckdb")
- settings.sqlite_path (Path, default "data/monitoring.db")
- settings.pid_file_path, settings.kill_flag_path
- settings.cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
- settings.env, settings.log_level, settings.is_live / is_paper / is_dev

未設定の必須環境変数（例: JQUANTS_REFRESH_TOKEN）にアクセスすると ValueError が発生します。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下に主要モジュールを配置しています。主なファイルと役割は以下の通り。

- src/kabusys/__init__.py
  - パッケージのエントリポイント（__version__ 等）

- src/kabusys/config.py
  - 環境変数・設定管理（自動 .env ロード、Settings クラス）

- src/kabusys/data/
  - jquants_client.py      : J-Quants API クライアント（取得・保存関数）
  - pipeline.py           : ETL パイプライン（run_daily_etl 等）
  - etl.py                : ETLResult 再エクスポート
  - news_collector.py     : RSS ニュース収集
  - calendar_management.py: 市場カレンダー管理（営業日判定など）
  - quality.py            : データ品質チェック
  - stats.py              : 汎用統計ユーティリティ
  - audit.py              : 監査ログ（監査テーブル定義、初期化）

- src/kabusys/ai/
  - news_nlp.py           : ニュースを銘柄別にまとめて LLM でセンチメントスコアリング
  - regime_detector.py    : ETF MA とマクロニュースを合成した市場レジーム判定

- src/kabusys/research/
  - factor_research.py    : モメンタム／ボラティリティ／バリュー等のファクター計算
  - feature_exploration.py: 将来リターン／IC／統計サマリー等
  - __init__.py           : 研究 API のエクスポート

- src/kabusys/ai/__init__.py
  - AI モジュールのエクスポート（score_news 等）

---

## 注意事項 / 運用メモ

- OpenAI の呼び出しには API キーが必要です。API 失敗時はフォールバック値（0.0）を使って継続する実装が多く、LLM の失敗で全体が停止しないよう設計されています。
- J-Quants API はレート制限（120 req/min）対応の RateLimiter を実装しています。ID トークンは自動リフレッシュされます。
- DuckDB の executemany() は空リストを受け付けないバージョンがあるため、コード内で空チェックが入っています。
- news_collector には SSRF 防御・XML パース保護（defusedxml）・受信サイズ上限などセキュリティ対策が組み込まれています。
- 監査ログは削除しない前提・UTC タイムスタンプ保存を想定しています。

---

## 貢献 / 開発

- 変更を加える場合はユニットテスト・静的解析を追加してください（テストフレームワークはプロジェクトポリシーに合わせて導入してください）。
- .env.example を用意して主要な環境変数をドキュメント化すると利用者に親切です。
- 実運用時は secrets の管理（Vault 等）を検討してください。

---

この README はコードベースの主要 API と使い方をまとめたものです。詳しい設計意図やデータスキーマ、運用ガイドは別途 Design / DataPlatform / Strategy ドキュメントを参照してください。