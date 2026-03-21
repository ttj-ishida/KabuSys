# KabuSys — 日本株自動売買システム

軽量な研究・データプラットフォームと戦略実行基盤を含んだ日本株向け自動売買ライブラリです。  
主に DuckDB をデータレイヤに使い、J-Quants API / RSS ニュース等からデータを収集し、特徴量生成 → シグナル生成 → 発注（実行レイヤ設計）といったワークフローを想定しています。

注意: ここにあるのはライブラリ実装のコードベースであり、証券会社APIや実運用向けのフルスタック実装（ブローカー連携 CLI 等）は含まれていません。実運用時はリスク管理・安全対策を十分に行ってください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数 / 設定
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は市場データ取得、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ設計までを含む日本株自動売買のためのモジュール群です。
- DuckDB をローカルのデータストアとして利用し、J-Quants API から日足や財務データ、カレンダー等を取得します。
- 研究用（research）ロジックと実行用（execution）ロジックを分離して設計されています。ルックアヘッドバイアスを防ぐため、target_date 時点のみのデータで計算する方針です。

主な機能一覧
- 環境変数/設定読み込み（.env/.env.local の自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants API クライアント（認証・ページネーション・レート制御・再試行・保存ヘルパ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- DuckDB スキーマの定義と初期化（init_schema）
- ETL パイプライン（差分更新、バックフィル、品質チェックフック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- 特徴量計算（research/factor_research）
  - モメンタム / ボラティリティ / バリュー等の算出関数
- 特徴量正規化（zscore_normalize）
- 戦略層
  - build_features: 生ファクターを統合・正規化して features テーブルへ保存
  - generate_signals: features + ai_scores を統合して BUY/SELL シグナルを signals テーブルへ保存
- ニュース収集（RSS）
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
  - SSRF 対策、トラッキングパラメータ除去、gzip/サイズ制限、XML パースの安全対策等を実装
- マーケットカレンダー管理（営業日判定・次/前営業日取得・夜間カレンダー更新ジョブ）
- 監査ログスキーマ（signal_events / order_requests / executions 等の定義）

---

セットアップ手順（ローカル開発向け）
1. Python 環境
   - 推奨: Python 3.9+（コードは typing | from __future__ annotations を使用）
2. 依存パッケージをインストール
   - main: duckdb, defusedxml（その他標準ライブラリのみを想定）
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - 実プロジェクトでは requirements.txt / pyproject.toml を用意してください。
3. リポジトリをクローンしてパッケージをインストール（開発モード）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```
4. 環境変数の設定
   - リポジトリルート（.git または pyproject.toml のある階層）を基準に .env/.env.local が自動で読み込まれます（OS 環境変数が最優先）。
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数の例は下記「環境変数 / 設定」参照。
5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)  # デフォルトは data/kabusys.duckdb
     ```
   - :memory: を渡すとインメモリ DB で初期化できます（テスト時に便利）。

---

使い方（簡易サンプル）
- 基本的な日次 ETL 実行（市場カレンダー → 日足 → 財務 → 品質チェック）:
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量の構築（features テーブルへ保存）:
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection  # 既存DBへ接続
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  cnt = build_features(conn, target_date=date(2025, 1, 31))
  print(f"upserted features: {cnt}")
  ```

- シグナル生成（signals テーブルへ保存）:
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025,1,31))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブの実行（既知銘柄セットがあれば紐付け可能）:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に用意した銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- カレンダー夜間更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar rows saved: {saved}")
  ```

- J-Quants API を直接扱う例（トークン取得／データ取得）:
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使用
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,12,31))
  ```

ログレベル・挙動の切り替え
- KABUSYS_ENV: development / paper_trading / live（settings.env プロパティで検証済み）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

---

環境変数 / 設定（Settings）
必須（.env などで設定すること）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token で使用）
- KABU_API_PASSWORD — kabuステーション API (発注層) のパスワード
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（値を設定すれば有効）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — Monitoring 用 SQLite（デフォルト data/monitoring.db）

.env の例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

自動 .env ロードの挙動
- パッケージは起動時、.git または pyproject.toml のあるプロジェクトルートを探索し、以下の順でロードします:
  - OS 環境変数（最優先）
  - .env.local（override=True）
  - .env（override=False）
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動ロードをスキップします（テスト用に便利）。

---

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義、version など
  - config.py — 環境変数 / Settings の管理（自動 .env ロード・検証）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（認証・取得・保存）
    - news_collector.py — RSS 収集・前処理・DB保存
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理・ジョブ
    - features.py — data.stats の再エクスポート
    - audit.py — 監査ログ（signal_events / order_requests / executions 等）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ の計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー等
  - strategy/
    - __init__.py — build_features, generate_signals を公開
    - feature_engineering.py — ファクター統合・ユニバースフィルタ・正規化・保存
    - signal_generator.py — final_score 計算、BUY/SELL 生成、signals テーブル書き込み
  - execution/ — （発注・ブローカー連携用の拡張向けに空のパッケージ）
  - monitoring/ — （監視・モニタリング用 DB / ロジックを想定）
- その他:
  - README.md（本ファイル）
  - pyproject.toml / setup.cfg 等（プロジェクトルートにある想定）

---

設計上の注意事項・運用メモ
- ルックアヘッドバイアス対策が随所に組み込まれており、基本的に target_date 時点までの情報のみを参照して計算します。
- DuckDB のスキーマは冪等に作成されます（init_schema は既存テーブルを上書きしません）。
- J-Quants へのリクエストは固定間隔レートリミッタと再試行ロジックを備えています（120 req/min を想定）。
- ニュース収集は SSRF や XML 攻撃対策を施してありますが、外部ソースを運用する際は監査とホワイトリスト運用を推奨します。
- 実運用での発注は重大なリスクを伴います。paper_trading フラグやテスト環境で十分に検証した上で live 環境に切り替えてください。

---

貢献 / 拡張
- execution 層（ブローカー API 実装）やリスク管理、ポートフォリオ最適化モジュールの追加が想定されます。
- 品質チェック（data.quality）が参照される箇所があります。品質チェックの実装を追加し、ETL の品質レポートを強化してください。

ご不明な点や README に追記してほしい内容があれば教えてください。