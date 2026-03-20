# KabuSys

日本株向けの自動売買・データ基盤ライブラリ集です。  
J-Quants API からのデータ収集 → DuckDB による保存・整形 → 研究用ファクター計算 → 特徴量正規化 → シグナル生成、さらにニュース収集やマーケットカレンダー管理までを含む ETL / 戦略レイヤーを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤を構成するためのライブラリ群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等データの差分取得と DuckDB への冗長性のある保存（冪等）
- DuckDB 上のスキーマ定義と初期化
- 研究（research）モジュールによるファクター計算
- 戦略（strategy）モジュールによる特徴量生成・正規化・シグナル生成
- ニュース収集（RSS）と銘柄紐付け
- マーケットカレンダー管理と営業日判定
- 発注／実行（execution）レイヤーのスキーマ（発注監査用DDL等）

設計のキーワードは「冪等性」「ルックアヘッドバイアス防止」「外部依存を最小化（DuckDB + 標準ライブラリ優先）」です。

---

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（`kabusys.data.jquants_client`）
    - 日足（OHLCV）、財務諸表、マーケットカレンダーの取得（ページネーション対応）
    - レートリミット、リトライ、トークン自動リフレッシュなどの堅牢な実装
  - ETL パイプライン（`kabusys.data.pipeline`）
    - 差分取得 / バックフィル / 品質チェックのワンストップ実行（`run_daily_etl`）
  - DuckDB スキーマ定義・初期化（`kabusys.data.schema`）
    - Raw / Processed / Feature / Execution 層のテーブル群を定義、`init_schema` で初期化

- 研究・特徴量
  - ファクター計算（`kabusys.research.factor_research`）
    - Momentum / Value / Volatility / Liquidity 等の計算（prices_daily / raw_financials を参照）
  - 特徴量探索・評価（`kabusys.research.feature_exploration`）
    - 将来リターン計算、IC（Spearman）計算、統計サマリー等
  - 正規化ユーティリティ（`kabusys.data.stats.zscore_normalize`）

- 戦略
  - 特徴量生成（`kabusys.strategy.feature_engineering.build_features`）
    - research 結果をマージ、ユニバースフィルタ、Z スコア正規化、features テーブルへ UPSERT
  - シグナル生成（`kabusys.strategy.signal_generator.generate_signals`）
    - features + ai_scores を統合し最終スコア算出、BUY/SELL シグナルを signals テーブルへ書き込み
    - Bear レジーム抑制、売り（エグジット）判定ロジック搭載

- ニュース収集
  - RSS 収集・前処理・DB 保存（`kabusys.data.news_collector`）
    - URL 正規化、記事 ID（SHA-256 先頭32文字）生成、SSRF 対策、gzip サイズ制限、銘柄抽出と紐付け

- カレンダー管理
  - JPX カレンダー更新、営業日判定、next/prev/trading_days 等（`kabusys.data.calendar_management`）

- 監査（Audit）
  - 発注・シグナル・実行の監査用スキーマ（`kabusys.data.audit`）

---

## セットアップ手順

前提:
- Python 3.9+（typing 機能を多用しているため推奨）
- DuckDB（Python パッケージ `duckdb`）
- defusedxml（RSS パースの堅牢化のため）
- ネットワーク接続（J-Quants API 等）

1. リポジトリをチェックアウトしてパッケージをインストール
   ```bash
   git clone <repo-url>
   cd <repo>
   pip install -e .  # setup があれば。無ければ必要な依存を個別インストール
   pip install duckdb defusedxml
   ```

2. 環境変数 / .env ファイルを準備  
   主要な環境変数（必須は _require としてチェックされるもの）:

   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用（必要に応じて）
   - SLACK_CHANNEL_ID (必須) — Slack チャネル ID
   - KABUSYS_ENV (任意) — "development" / "paper_trading" / "live"（デフォルト: development）
   - LOG_LEVEL (任意) — "DEBUG"/"INFO"/...（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD (任意) — 自動 .env ロードを無効化（1 で無効）
   - DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH (任意) — 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による無効化可）。

3. DuckDB スキーマ初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" でも OK
   conn.close()
   ```

---

## 使い方（主要ワークフロー）

以下は典型的な日次ワークフロー例です。DuckDB 接続を使って順に ETL → 特徴量生成 → シグナル生成 を行います。

1. DuckDB 接続 / スキーマ初期化（初回のみ）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL を実行（市場カレンダー・株価・財務を差分更新）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # 引数で target_date, id_token などを指定可能
   print(result.to_dict())
   ```

3. 特徴量（features）作成（strategy.feature_engineering）
   ```python
   from kabusys.strategy import build_features
   from datetime import date
   cnt = build_features(conn, date.today())  # 指定日分を計算して features テーブルへ UPSERT
   print(f"features upserted: {cnt}")
   ```

4. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date
   n_signals = generate_signals(conn, date.today(), threshold=0.6)
   print(f"signals written: {n_signals}")
   ```

5. ニュース収集（RSS）と銘柄紐付け
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes: 銘柄コードのセット（抽出対象）
   res = run_news_collection(conn, known_codes={"7203", "6758"})
   print(res)
   ```

6. カレンダー夜間更新（バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

注意点:
- generate_signals / build_features は DuckDB 上のテーブル（prices_daily, raw_financials, features, ai_scores, positions 等）に依存します。ETL の実行・スキーマ初期化を行ってから使用してください。
- シグナル生成は発注・execution 層への直接送信を行いません。signals テーブルに結果を保存するのみです。実行（発注）は別のレイヤーで実装することを想定しています。

---

## ディレクトリ構成

主要ファイルを抜粋した構成（src/kabusys/...）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（J-Quants, kabu, Slack, DB パス等）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - 差分 ETL ロジックと run_daily_etl
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存・銘柄抽出
    - calendar_management.py
      - カレンダー更新、営業日判定、next/prev/get_trading_days
    - audit.py
      - 監査ログ用 DDL（signal_events, order_requests, executions 等）
    - features.py
      - zscore_normalize の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - momentum / value / volatility の計算
    - feature_exploration.py
      - forward returns / IC / factor summary / rank 等
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features
    - signal_generator.py
      - generate_signals
  - execution/
    - __init__.py
    - （発注処理実装はここに配置予定）
  - monitoring/
    - （監視用 DB / ロギング等のコードを配置する想定）

各モジュール内に詳細な docstring があり、設計方針や処理フロー、重要な定数・チェックポイントが記載されています。まずは schema.init_schema → data.pipeline.run_daily_etl → strategy.build_features → strategy.generate_signals の順に動かすと、基本的な ETL→シグナル生成の流れを確認できます。

---

## 環境変数と設定について

- 自動 .env ロード
  - パッケージ起点（このファイルの親ディレクトリで .git または pyproject.toml を探索）で `.env` と `.env.local` を自動読み込みします。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Settings（主なプロパティ）
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url
  - settings.slack_bot_token
  - settings.slack_channel_id
  - settings.duckdb_path
  - settings.sqlite_path
  - settings.env (development / paper_trading / live)
  - settings.log_level

未設定の必須変数を参照すると ValueError が送出されます。`.env.example` を参照して `.env` を整備してください（リポジトリに存在する場合）。

---

## 開発・運用上の注意

- ルックアヘッドバイアス対策:
  - すべての計算は target_date 時点で利用可能なデータに限定して行う設計です（fetched_at の記録など）。
- 冪等性:
  - DB 書き込みは可能な限り ON CONFLICT / INSERT ... DO UPDATE / INSERT ... DO NOTHING を用いて冪等化しています。
- レートリミットとリトライ:
  - J-Quants クライアントは 120 req/min の制限を守る実装が含まれます。429/408/5xx などに対しては指数バックオフでリトライします。
- セキュリティ:
  - RSS 収集で SSRF 対策、gzip 解凍上限、defusedxml 利用等の安全対策を導入しています。
- 本番運用:
  - settings.is_live / is_paper フラグを利用して実行時の挙動を切り替え、発注実装では必ず二重発注防止（監査・冪等キー）を行ってください。

---

## 追加情報 / 拡張点

- execution 層の具象（証券会社 API 連携）は現状シグナル保存までで、実際の発注エンジンは別途実装することを想定しています。audit モジュールはそのための監査スキーマを提供します。
- AI スコア連携: ai_scores テーブルを参照する形で signal_generator は AI スコアを利用します。AI スコアの生成・投入は別プロセスで行ってください。
- 品質チェック: pipeline.run_daily_etl は quality モジュールを利用します（quality モジュールが実装されていることが前提です）。

---

README に書かれている手順で動作させる際に不明点やエラーが出た場合は、該当するモジュール名とエラー・環境情報を教えてください。具体的なコマンド例やトラブルシュートを提示します。