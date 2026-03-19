# KabuSys

日本株向けの自動売買・データプラットフォーム。  
J-Quants API と連携して市場データ・財務データ・ニュースを収集し、DuckDB に格納、特徴量作成→シグナル生成→（発注層へ引き渡し）というワークフローを想定したモジュール群を提供します。

設計上のポイント:
- ルックアヘッドバイアス防止：各処理は target_date 時点のデータのみを使う
- 冪等性：DB への保存は ON CONFLICT（UPDATE）や日付単位の置換で安全に再実行可能
- テストしやすさ：トークン注入や自動 .env ロードを抑止可能
- 外部依存を最小化：主要処理は標準ライブラリ＋必須ライブラリのみ

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルートを探索）
  - 必須環境変数取得ヘルパ
- データ収集 / ETL（kabusys.data）
  - J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - RSS ベースのニュース収集（SSRF対策・サイズ制限・トラッキング除去）
  - DuckDB スキーマの定義と初期化
  - ETL パイプライン（差分取得、バックフィル、品質チェックの呼び出し）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 統計ユーティリティ（Zスコア正規化など）
- 研究用（kabusys.research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC（Information Coefficient）・統計サマリー
- 戦略（kabusys.strategy）
  - 特徴量作成（research の生ファクターを正規化して features テーブルへ保存）
  - シグナル生成（features と ai_scores を統合して BUY/SELL を生成）
- 発注 / 実行（kabusys.execution）
  - 発注・約定・ポジション関連のスキーマは定義（発注ロジックは別実装想定）
- 監査（audit）・ログ（audit テーブル群） — トレーサビリティを確保する設計
- その他：ニュースと銘柄の紐付け、データ品質チェック（quality モジュール呼び出し想定）

---

## セットアップ手順

1. 必要環境
   - Python 3.10 以上（型ヒントや | ユニオン表記を利用）
   - DuckDB（Python パッケージ）
   - defusedxml（RSS/XML の安全パース）
   - （任意）他のユーティリティや linters

2. パッケージのインストール（例）
   ```
   python -m pip install duckdb defusedxml
   ```
   - プロジェクト配布形態に応じて `pip install -e .` などでインストールしてください。

3. 環境変数（.env）
   - プロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（コード内で _require() によりチェックされます）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携で利用）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — 通知先チャネル ID
   - 任意:
     - KABUSYS_ENV (development|paper_trading|live) — 実行環境
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 SQLite: data/monitoring.db）
   - 例 .env（参考）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
     ```
   - メモリ DB を試す場合:
     ```python
     conn = init_schema(":memory:")
     ```

---

## 使い方（主要ワークフロー例）

以下は代表的な呼び出し例です。各関数は DuckDB 接続を受け取る設計です。

- 日次 ETL（市場カレンダー→株価→財務→品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルを更新）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2026, 1, 31))
  print(f"upserted features: {n}")
  ```

- シグナル生成（features と ai_scores から signals 更新）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2026, 1, 31), threshold=0.6)
  print(f"generated signals: {total}")
  ```

- ニュース収集（RSS を取得して raw_news に保存、銘柄紐付け）
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に取得しておく銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.data.calendar_management import calendar_update_job

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

注意点:
- 各 ETL / 保存処理は冪等設計です。再実行しても重複登録を避けるよう設計されています。
- J-Quants API のリクエストは内部でレートリミッタとリトライを実施します。
- ai_scores 等が未登録でもシグナル生成は中立値で補完して処理します。

---

## 設定と挙動のポイント

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を順に読み込みます。
  - OS 環境変数が優先され、`.env.local` は上書き（override=True）されます。
  - 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- 環境種別
  - KABUSYS_ENV は development / paper_trading / live のいずれか。`settings.is_live` 等のプロパティで判定可能。
- ログレベル
  - LOG_LEVEL を設定し、"DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかを使用します。

---

## ディレクトリ構成（抜粋）

以下はソース内の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + 保存ユーティリティ）
    - news_collector.py — RSS 収集・前処理・DB 保存
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — market_calendar 管理・営業日ロジック
    - features.py — zscore_normalize の再エクスポート
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 発注から約定までの監査ログ定義
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value ファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — 特徴量作成（features テーブルへUPSERT）
    - signal_generator.py — final_score 計算・BUY/SELL 生成・signals テーブル書込み
  - execution/
    - __init__.py — 発注層（実装は別途）
  - monitoring/ (パッケージとして公開される想定だが個別ファイルは省略)

各モジュールは DuckDB 接続を引数に取ることが多く、モジュール間の副作用を抑えた設計です。

---

## 開発・運用上の注意

- DuckDB の SQL 構文やバージョンに依存する部分があるため、DuckDB のバージョン互換性に注意してください（DDL の一部は古いバージョンで未サポートの機能を避ける工夫あり）。
- 実運用（live）では KABUSYS_ENV を `live` に設定し、発注層の安全（冪等キー、ステータス管理、監査ログ）を必ず確認してください。
- ニュース収集は外部ネットワークを使うため SSRF・XML の安全対策（defusedxml、ホスト検査、レスポンスサイズ制限）を実装していますが、追加のネットワーク制限・プロキシの設定などは運用環境で行ってください。

---

必要であれば、README に含める具体的な .env.example、CI 用のコマンド、デプロイ手順（systemd / cron / Kubernetes CronJob でのスケジューリング例）なども作成します。どの情報が欲しいか教えてください。