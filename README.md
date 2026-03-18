# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータ層に用い、J-Quants API や RSS からデータを取得して ETL → 特徴量算出 → 戦略評価 → 発注監査までの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は下記の責務を持つモジュール群で構成されています。

- データ取得/保存（J-Quants API 経由の株価・財務・マーケットカレンダー、RSS ニュース）
- DuckDB を用いたスキーマ定義・初期化・接続管理
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集と銘柄抽出
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z-score 正規化）
- 監査ログ（シグナル → 発注 → 約定 のトレース用テーブル群）
- 環境設定管理（.env 読み込み、必須設定の検証）

設計上のポイント:
- DuckDB を中心に「Raw / Processed / Feature / Execution / Audit」レイヤでテーブル設計
- ETL は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）で実装
- J-Quants クライアントはレート制御・リトライ・トークン自動リフレッシュ対応
- RSS 収集は SSRF 防止・受信サイズ制限・XML の安全パース等の対策あり
- 研究モジュールは外部ライブラリに依存せず標準ライブラリのみで実装

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API の取得・保存ユーティリティ（fetch / save）
  - news_collector: RSS 収集、正規化、DB 保存、銘柄抽出
  - schema: DuckDB のスキーマ定義と init_schema / get_connection
  - pipeline: 日次 ETL（prices / financials / calendar）および品質チェック実行
  - quality: 欠損・スパイク・重複・日付不整合チェック
  - calendar_management: market_calendar の更新・営業日判定ユーティリティ
  - audit: 監査ログ用テーブルの初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- research
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、factor_summary 等
  - factor_research: momentum / volatility / value など主要ファクター算出
- config: .env / 環境変数読み込み、Settings オブジェクト（必須キーチェック）
- monitoring / execution / strategy: 各層のプレースホルダ（将来的な拡張）

---

## 前提

- Python 3.10 以上（型アノテーションで `X | None` 構文を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml

（実行環境に合わせて requirements.txt を整備してください）

---

## セットアップ手順

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - pip install duckdb defusedxml
   - （プロジェクトとして開発する場合）pip install -e .

3. 環境変数（.env）準備  
   プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   最低限必要な環境変数（Settings で必須とされるもの）:
   - JQUANTS_REFRESH_TOKEN=（J-Quants のリフレッシュトークン）
   - KABU_API_PASSWORD=（kabu API パスワード）
   - SLACK_BOT_TOKEN=（Slack ボットトークン）
   - SLACK_CHANNEL_ID=（通知先 Slack チャンネルID）

   追加オプション:
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL  （デフォルト: INFO）
   - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
   - SQLITE_PATH=data/monitoring.db  （デフォルト）

   .env の例（.env.example）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な例）

以下はいくつかの主要な操作例です。実運用ではエラーハンドリングやログ設定を追加してください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 監査ログ用スキーマ追加（既存接続へ）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- 日次 ETL の実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # デフォルトは today を対象に ETL 実行
  print(result.to_dict())
  ```

- RSS ニュース収集ジョブ実行（銘柄抽出に known_codes を使う例）
  ```python
  from kabusys.data.news_collector import run_news_collection
  # conn: DuckDB 接続
  known_codes = {"7203", "6758", "6502"}
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: 新規保存数}
  ```

- 研究系関数（ファクター計算）の利用例
  ```python
  from kabusys.data.schema import get_connection
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target)
  # 例: mom の 'ma200_dev' と fwd の 'fwd_1d' で IC を計算
  ic = calc_ic(mom, fwd, "ma200_dev", "fwd_1d")
  ```

- Settings の利用
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## 主要モジュールの説明（ディレクトリ構成）

プロジェクトは `src/kabusys` 以下に実装されています。主要ファイル / モジュール:

- kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込みロジック
    - Settings クラス（J-Quants トークン、kabu API パスワード、Slack、DB パス等）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レートリミット、リトライ、トークンリフレッシュ、保存関数）
    - news_collector.py
      - RSS 取得・前処理・ID 生成・DuckDB への保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ（Raw / Processed / Feature / Execution）定義と init_schema/get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl（ETL ロジック）
    - features.py
      - データ側の特徴量ユーティリティ再エクスポート
    - calendar_management.py
      - market_calendar の更新・営業日判定ユーティリティ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）の DDL と初期化
    - etl.py
      - ETLResult 再エクスポート
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - research/
    - __init__.py
      - 研究系ユーティリティのエクスポート
    - factor_research.py
      - momentum / volatility / value のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC 計算、factor_summary、rank
  - strategy/
    - __init__.py
    - （戦略実装は拡張ポイント）
  - execution/
    - __init__.py
    - （発注ロジックは拡張ポイント）
  - monitoring/
    - __init__.py
    - （監視・メトリクス関連は拡張ポイント）

---

## 注意事項 / 運用メモ

- 環境変数は .env / .env.local の順で読み込まれ、OS 環境変数が最優先です。テスト時など自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants のレート制限（120 req/min）に合わせた実装が組み込まれていますが、大量のページネーションを伴う処理や同時実行では注意してください。
- DuckDB のバージョン差異によりサポート状況が変わる機能（外部キーの ON DELETE 挙動など）があります。README の実装は DuckDB の制限を考慮した設計になっています。
- 本リポジトリには実際の発注処理（ブローカー API 呼び出し）や Slack 通知等の完全実装は含まれていない部分があります。運用前に適切なリスク管理、テスト（paper_trading 環境）を行ってください。
- Secrets（トークンやパスワード）は .env に平文で置く場合の取り扱いに注意し、必要に応じてシークレット管理サービスを利用してください。

---

必要であれば、README に含めるサンプル .env.example、docker-compose / systemd ジョブ例、CI 用テスト手順、より詳細な API リファレンス（各関数の使用例）なども追加できます。どの情報を優先的に追加しますか？