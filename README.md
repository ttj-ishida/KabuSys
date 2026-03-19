# KabuSys

日本株向けの自動売買システム用ライブラリ。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・スキーマ管理など、戦略開発から実運用に必要な主要機能を含んだモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス防止（常に target_date 時点のデータのみを使用）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで安全に）
- 外部発注層（execution）への依存を直接持たない（signals 等は DB へ書き込む）
- 最小限の外部ライブラリ（duckdb, defusedxml 等）

バージョン: 0.1.0

---

## 機能一覧

- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルートを探索）
  - 必須設定の取得と検証

- データ取得 / 保存
  - J-Quants API クライアント（認証リフレッシュ、ページネーション、レート制御、リトライ）
  - raw_prices / raw_financials / market_calendar の取得および DuckDB への冪等保存

- ETL / パイプライン
  - 差分更新（最終取得日からの差分算出、backfill 対応）
  - 市場カレンダー、株価、財務データの統合的な日次 ETL（品質チェック呼び出しを含む）

- スキーマ管理
  - DuckDB 用スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - 初期化関数でディレクトリ自動作成

- 研究・ファクター計算
  - momentum / volatility / value などのファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマンのランク相関）計算、統計サマリー

- 特徴量エンジニアリング
  - 生ファクターを統合、ユニバースフィルタ適用、Zスコア正規化、クリップ、features テーブルへの UPSERT

- シグナル生成
  - features と ai_scores を統合して final_score を計算
  - Bear レジームによる BUY 抑制、エグジット（STOP LOSS 等）判定、signals テーブルへ保存

- ニュース収集
  - RSS 収集（SSRF 対策、XMLパース安全化、URL 正規化）、raw_news と news_symbols への保存
  - 記事IDは正規化URLのSHA-256先頭32文字で冪等性保証

- その他
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day、期間内営業日取得）
  - 監査ログ（signal_events / order_requests / executions 等の初期DDLあり）

---

## セットアップ手順

1. 必要な Python バージョン
   - Python 3.10 以上（型ヒントに | 演算子を使用）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに setup.cfg / pyproject.toml があれば pip install -e . を使用）

4. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます（読み込み順: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数（少なくとも実運用で必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API （発注連携がある場合）
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意/デフォルト:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development / paper_trading / live) デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...) デフォルト: INFO

5. DuckDB スキーマ初期化
   - サンプル:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - :memory: を渡すとインメモリ DB を使用できます。

---

## 使い方（主要ワークフロー例）

以下は一例です。実際はアプリケーションの CLI / ワーカーなどから呼び出します。

- データベース初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場データ取得・保存・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  count = build_features(conn, target_date=date(2024, 1, 4))
  print(f"Built features for {count} symbols")
  ```

- シグナル生成（signals テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date(2024, 1, 4), threshold=0.6)
  print(f"Generated {total} signals")
  ```

- ニュース収集ジョブ（RSS から raw_news と news_symbols へ）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  known_codes = {"7203", "6758", ...}  # 有効な銘柄コードのセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J-Quants API から日足を直接取得して保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,4))
  saved = save_daily_quotes(conn, records)
  ```

注意点:
- API 呼び出しはレート制御・リトライ・トークン自動リフレッシュを備えています。
- ETL は個々のステップで例外を吸収しログ化するため、結果オブジェクト（ETLResult）で問題の有無を確認してください。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内部の主要ファイル一覧（src/kabusys）です。省略箇所は多数のユーティリティ・DDL・実装を含みます。

- src/
  - kabusys/
    - __init__.py
    - config.py — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py — J-Quants API クライアント（取得・保存）
      - news_collector.py — RSS ニュース収集と保存
      - schema.py — DuckDB スキーマ定義と init_schema()
      - stats.py — zscore_normalize 等の統計ユーティリティ
      - pipeline.py — ETL パイプライン（日次 ETL 等）
      - calendar_management.py — market_calendar 管理・営業日ロジック
      - audit.py — 監査ログ用スキーマ定義
      - features.py — data.stats の再エクスポート
    - research/
      - __init__.py
      - factor_research.py — momentum / volatility / value 計算
      - feature_exploration.py — 将来リターン / IC / summary
    - strategy/
      - __init__.py
      - feature_engineering.py — features 構築（正規化・フィルタ）
      - signal_generator.py — final_score 計算と signals 生成
    - execution/ — 発注関連（インターフェース層、空 __init__ が存在）
    - monitoring/ — 監視・モニタリング周り（ディレクトリあり）

（詳細なファイルはソースツリーを参照してください）

---

## 設定 / 実運用での注意点

- シークレット（API トークンなど）は .env ファイルまたは OS 環境変数で管理してください。`.env.example` を参考に設定することを想定しています。
- DB ファイル（DUCKDB_PATH）はバックアップや整合性を考慮して適切な場所に配置してください。大規模環境では S3 等へのエクスポート運用を検討してください。
- KABUSYS_ENV を `live` にすると実運用モード（発注等と連携）を想定した挙動にするため、必ず十分にテストしてから切り替えてください。
- ニュース収集は外部 RSS を取得するため、ネットワーク制約や公開元の利用規約に注意してください。
- 発注周り（kabu API 等）を連携する場合は、安全なテスト口座（paper_trading）での検証を推奨します。

---

以上がプロジェクトの README です。必要であれば、以下を追加で作成できます：
- 簡易 CLI / systemd タスクの実行例
- 詳細な環境変数一覧（.env.example）
- 開発者向けのユニットテスト実行手順
- リファレンス（各関数の入出力例）