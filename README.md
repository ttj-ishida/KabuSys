# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けのデータパイプライン、特徴量作成、シグナル生成、ニュース収集、監査・実行用スキーマを備えた自動売買基盤のコアライブラリ群です。研究（research）で得た生ファクターを正規化・合成して戦略用の特徴量を作成し、AIスコアやルールを統合して売買シグナルを生成します。データ取得は J-Quants API を利用し、保存先は DuckDB を想定しています。

主な設計方針（抜粋）
- ルックアヘッドバイアス防止：target_date 時点のデータのみで計算
- 冪等性：DB への保存は ON CONFLICT / トランザクションで安全に
- テスト性：id_token 等を注入できる API 設計
- セキュリティ配慮：RSS の SSRF 対策、XML パースに defusedxml を使用

---

## 機能一覧

- 環境設定管理
  - .env 自動ロード（プロジェクトルート検出）／必須キー取得（kabusys.config）
- データ取得・保存（J-Quants）
  - 株価日足、財務データ、JPX カレンダーの取得と DuckDB への冪等保存（kabusys.data.jquants_client）
  - API レート制御・リトライ・トークン自動リフレッシュ
- ETL パイプライン
  - 日次差分 ETL（カレンダー・株価・財務）と品質チェック（kabusys.data.pipeline）
  - カレンダー更新ジョブ（kabusys.data.calendar_management）
- ニュース収集
  - RSS 収集・前処理・重複排除・銘柄抽出・DB 保存（kabusys.data.news_collector）
- ファクター計算 / 研究支援
  - Momentum / Volatility / Value 等のファクター計算（kabusys.research.factor_research）
  - 将来リターン計算、IC（Spearman）や統計サマリー（kabusys.research.feature_exploration）
  - Zスコア正規化ユーティリティ（kabusys.data.stats）
- 特徴量作成・シグナル生成（戦略層）
  - features テーブル作成（標準化・クリップ）: build_features
  - final_score 計算・BUY/SELL シグナル生成: generate_signals（kabusys.strategy）
- スキーマ / 監査
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）(kabusys.data.schema)
  - 監査ログ（signal_events / order_requests / executions）設計（kabusys.data.audit）

---

## セットアップ手順

前提
- Python 3.10 以上（| 型ヒントを使用しているため）
- pip が使える環境

1. リポジトリを取得
   - git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合は pip install -e .）

   ※ 上記は主要依存です。プロジェクトで別途 requirements.txt があればそちらを使用してください。

4. 環境変数 (.env)
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須環境変数（kabusys.config.Settings 参照）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API 用パスワード（発注連携を行う場合）
   - SLACK_BOT_TOKEN: Slack 通知を行うなら必須
   - SLACK_CHANNEL_ID: Slack チャネル ID
   推奨／任意
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: モニタリング用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 (.env)
   - JQUANTS_REFRESH_TOKEN=your_refresh_token
   - KABU_API_PASSWORD=your_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C12345678
   - DUCKDB_PATH=data/kabusys.duckdb
   - KABUSYS_ENV=development
   - LOG_LEVEL=DEBUG

5. DB スキーマ初期化
   - Python から DuckDB のスキーマを作成します（データディレクトリがなければ自動作成されます）。

   例:
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---

## 使い方（主要 API の例）

以下は Python スクリプト／REPL 上での簡単な操作例です。conn は duckdb の接続オブジェクトです。

1) スキーマ初期化
- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL を実行（カレンダー取得、株価・財務取得、品質チェック）
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn)  # target_date を指定可能
- print(result.to_dict())

3) 特徴量作成（features テーブルへ UPSERT）
- from datetime import date
- from kabusys.strategy import build_features
- build_features(conn, date(2024, 1, 31))

4) シグナル生成（features / ai_scores / positions を参照して signals を作成）
- from kabusys.strategy import generate_signals
- generate_signals(conn, date(2024, 1, 31), threshold=0.6)

5) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
- from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
- res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
- print(res)

6) カレンダー更新ジョブ（夜間バッチ）
- from kabusys.data.calendar_management import calendar_update_job
- calendar_update_job(conn)

注意点（運用上の重要情報）
- J-Quants API はレート制限（120 req/min）があるため jquants_client が内部でスロットリングします。
- jquants_client は 401 を受けるとリフレッシュトークンで ID トークンを自動更新して再試行します。
- 多くの DB 操作はトランザクションで行われ、冪等性を担保しています。
- RSS フェッチは SSRF 対策や XML Bomb 対策（defusedxml）を行っています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                 — 環境設定 / .env 自動ロード
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（取得 + 保存）
  - news_collector.py       — RSS 取得・前処理・保存・銘柄抽出
  - schema.py               — DuckDB スキーマ定義 & init_schema()
  - stats.py                — zscore_normalize 等ユーティリティ
  - pipeline.py             — ETL（run_daily_etl 等）
  - features.py             — data.stats の再エクスポート
  - calendar_management.py  — market_calendar の管理 / カレンダー更新ジョブ
  - audit.py                — 監査ログ DDL（signal_events / order_requests / executions 等）
  - audit.py                — （監査用テーブル定義、トレーサビリティ）
- research/
  - __init__.py
  - factor_research.py      — momentum / volatility / value の計算
  - feature_exploration.py  — 将来リターン、IC、統計サマリー等
- strategy/
  - __init__.py             — build_features / generate_signals を公開
  - feature_engineering.py  — features テーブル作成処理
  - signal_generator.py     — final_score 計算と signals 作成
- execution/
  - __init__.py             — 実行層モジュール用（未実装箇所を含む）
- monitoring/                — モニタリング用モジュール（__all__ に含まれるが実装が無い場合あり）
- その他（logging 設定や CLI があれば追加）

（上記は提供されたコードからの抜粋です。実際のリポジトリにはドキュメント・スクリプト等が追加されている可能性があります。）

---

## 運用・開発時のヒント

- テスト時に .env 自動読み込みを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のパスを変更すると複数環境で簡単に切り替えられます（development / paper_trading / live を使い分け）。
- feature / signal 生成は target_date 単位で冪等に実行できるため、再実行やバッチ再処理が容易です。
- ニュースの銘柄抽出は単純な 4 桁数字検出に基づくため、必要に応じて辞書や NER を組み合わせると精度向上します。

---

README に記載した以外の詳細（SQL スキーマやアルゴリズム仕様、設計文書）は該当するソースコードの docstring とモジュールコメントに記載されています。必要があれば個別の機能についての使い方・例や API リファレンスを追加しますので、どの部分を詳しく知りたいか教えてください。