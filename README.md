# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
データ取得・ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ等を含む一連の基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下の層で構成されるシステム基盤を提供します。

- Data layer：J-Quants API からのデータ取得、Raw → Processed → Feature の ETL、DuckDB スキーマ
- Research layer：ファクター計算 / 特徴量探索（ルックアヘッドバイアスに配慮）
- Strategy layer：特徴量を統合してシグナル（BUY/SELL）を生成
- Execution / Audit：発注・約定・ポジション用スキーマ、監査ログ（トレーサビリティ）
- News collection：RSS フィード収集と記事と銘柄の紐付け
- Config：.env 自動読み込みと設定ラッパー

設計方針として、ルックアヘッドバイアスを防ぐために「target_date 時点で利用可能なデータのみ」を扱い、DuckDB を永続ストレージおよび高速集計基盤として利用します。API 呼び出しはレート制御・リトライ・トークン自動更新等の堅牢な実装を持ちます。

---

## 主な機能一覧

- DuckDB スキーマ定義・初期化（init_schema）
- J-Quants API クライアント（fetch / save）＋レート制御・リトライ・トークン自動更新
- 日次 ETL パイプライン（run_daily_etl）：市場カレンダー・株価・財務データの差分取得と保存、品質チェック
- 特徴量計算（research.factor_research）：
  - Momentum / Volatility / Value 等のファクター
- 特徴量正規化（z-score クロスセクション）
- 特徴量組み合わせとシグナル生成（strategy.build_features / strategy.generate_signals）
- ニュース収集（RSS）と raw_news / news_symbols 保存（news_collector）
- マーケットカレンダー管理（calendar_update_job / is_trading_day / next_trading_day 等）
- 監査ログ・オーダー/約定のためのスキーマ（audit）
- 環境設定管理（kabusys.config）と .env 自動読み込み（プロジェクトルートの .env/.env.local）

---

## セットアップ手順

前提：Python 3.9+（型ヒントに Union Type、typing の使用があるため少なくとも 3.9 以上を想定）

1. レポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール  
   このコードベースは明示的な requirements.txt を含みませんが、最低限以下をインストールしてください：
   ```
   pip install duckdb defusedxml
   ```
   パッケージ配布（pyproject/セットアップ）がある場合は開発インストール：
   ```
   pip install -e .
   ```

4. 環境変数の設定  
   プロジェクトルートに `.env`（および必要に応じて .env.local）を置くと自動読み込みされます（自動ロードを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須の環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API を使う場合のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack の投稿先チャネルID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）デフォルトあり
   - SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルトは development
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト INFO

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL やスクリプトで：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルを作成・テーブルを初期化
   conn.close()
   ```

---

## 使い方（主要な例）

以下はライブラリを利用するための代表的なコード例です。スクリプト化して Cron や Airflow から呼ぶことを想定しています。

- DuckDB 接続 & スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL の実行（市場カレンダー→株価→財務→品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())
  ```

- 特徴量の作成（features テーブルへ書き込み）
  ```python
  from kabusys.strategy import build_features
  from datetime import date

  n = build_features(conn, date(2025, 1, 15))
  print(f"features upserted: {n}")
  ```

- シグナル生成（signals テーブルへ書き込み）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date

  total = generate_signals(conn, date(2025, 1, 15))
  print(f"signals written: {total}")
  ```

- ニュース収集（RSS）と銘柄紐付け
  ```python
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新バッチ（夜間）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- J-Quants からの取得 & 保存（個別呼び出し例）
  ```python
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,15))
  saved = jq.save_daily_quotes(conn, records)
  ```

注意点：
- すべての公開 API は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。接続のライフサイクル（close 等）は呼び出し側で管理してください。
- generate_signals / build_features は target_date 時点のデータのみを利用するため、ETL を先に走らせて最新データを投入しておく必要があります。

---

## 環境変数一覧（要点）

主要な環境変数と意味：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用
- SLACK_CHANNEL_ID (必須) — Slack 投稿先チャンネル
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development", "paper_trading", "live")
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合は 1 をセット

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内の src/kabusys を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動読み込み / Settings
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - news_collector.py       — RSS 取得・前処理・DB 保存
    - schema.py               — DuckDB スキーマ定義と init_schema
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - pipeline.py             — 日次 ETL パイプライン（run_daily_etl 等）
    - features.py             — features インターフェース再エクスポート
    - calendar_management.py  — カレンダー更新 / 営業日判定
    - audit.py                — 監査ログ用 DDL
    - execution/               — 発注関連モジュール（空のパッケージ）
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Volatility / Value の計算
    - feature_exploration.py  — forward returns / IC / summary utilities
  - strategy/
    - __init__.py
    - feature_engineering.py  — features を作成し features テーブルに保存
    - signal_generator.py     — features + ai_scores を統合し signals を作成
  - execution/                — 発注・実行層用（パッケージ）
  - monitoring/               — 監視用 DB / ロジック（ディレクトリ placeholder）

※ 各モジュールに詳細な docstring が付与されており、実装方針・設計注釈が豊富です。まずは schema.init_schema → pipeline.run_daily_etl → strategy.build_features → strategy.generate_signals の流れで動作確認することを推奨します。

---

## 運用上の注意点

- DuckDB ファイルは適切なバックアップを行ってください。複数プロセスからの同時書き込みは注意が必要です（接続の競合回避）。
- J-Quants API はレート制限があり、jquants_client は固定間隔スロットリングとリトライ実装を行っています。アプリケーション側でも過度な同時并列呼び出しは避けてください。
- ニュース収集モジュールは SSRF 対策や XML パースの安全処理（defusedxml）を行っています。RSS ソースの追加は DEFAULT_RSS_SOURCES を使うか run_news_collection の引数で渡してください。
- 本レポジトリは strategy / execution 層を分離して設計しています。実際の発注（ブローカー接続）を実装する場合は execution パッケージを拡張し、audit テーブルにトレースを残すことを推奨します。

---

## 開発者向けメモ

- テストを行う際は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env の自動読込を無効化できます。
- DuckDB の in-memory 接続は `":memory:"` を init_schema に渡すことで利用できます（ユニットテストで便利）。
- jquants_client._request の挙動はネットワーク依存のため、ユニットテストでは _request や _urlopen をモックすることを推奨します。
- news_collector._urlopen や jquants_client._get_cached_token などモジュールレベルの関数はテスト時に差し替え可能な設計になっています。

---

もし README に追加したい「実行スクリプト例」「CI の設定」「サンプル .env.example」などがあれば提供できます。必要な内容を教えてください。