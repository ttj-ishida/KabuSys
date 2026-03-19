# KabuSys — 日本株自動売買システム

KabuSys は日本株のデータ取得・ETL・特徴量生成・シグナル作成・ニュース収集を行うライブラリ群です。研究（research）で算出した生ファクターを加工して戦略用の特徴量を作成し、AI スコアやルールに基づいて売買シグナルを生成します。DuckDB を主な永続化層として利用します。

## 特徴（主な機能一覧）

- 環境変数／.env 管理
  - プロジェクトルートの `.env` / `.env.local` を自動的に読み込み（無効化可）。
- データ取得（J-Quants API）
  - 日足（OHLCV）、財務データ、マーケットカレンダーをページネーション対応で取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（冪等）
- ETL パイプライン
  - 差分更新（最終取得日からの取得）・バックフィル対応・品質チェック（フラグ検出）
  - 日次 ETL の統合エントリポイント
- ニュース収集
  - RSS 取得、XML パース（defusedxml 使用）、URL 正規化、銘柄コード抽出、冪等保存
  - SSRF／gzip／受信サイズ制限などセキュリティ対策あり
- 研究（research）モジュール
  - モメンタム / ボラティリティ / バリューのファクター計算、将来リターン計算、IC 計算等
- 特徴量エンジニアリング
  - 生ファクターのマージ・ユニバースフィルタ・Z スコア正規化・クリッピング・features テーブルへの UPSERT
- シグナル生成
  - ファクターと AI スコアを統合して最終スコアを計算、BUY/SELL シグナルを signals テーブルへ日付単位で置換（冪等）
- 発注／監査用スキーマ（Execution / Audit）
  - signal_queue / orders / executions / audit テーブル等を定義

---

## セットアップ手順

以下はローカル開発／実行の最低限の手順例です。

1. Python 環境を用意（推奨: 3.9+）
   - 仮想環境の作成例:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - このリポジトリで必要とされる主な依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。）

3. 環境変数（.env）を準備
   - プロジェクトルートの `.env` または `.env.local` に必要な設定を記載します。
   - 必須環境変数（config.Settings が要求するもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（execution 層で使用）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
   - 任意（デフォルトあり）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベーススキーマの初期化
   - DuckDB を初期化してテーブルを作成します（親ディレクトリは自動作成されます）。
   - 例（Python コンソール）:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```

---

## 使い方（基本的なサンプル）

以下は代表的な操作のコードスニペット例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL の実行（J-Quants から差分取得して保存）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
  print(result.to_dict())
  ```

- 研究モジュールでファクターを計算（例: calc_momentum）
  ```python
  from kabusys.research import calc_momentum
  from datetime import date
  factors = calc_momentum(conn, date(2024, 1, 31))
  ```

- 特徴量のビルド（features テーブルへ）
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, date(2024, 1, 31))
  print(f"built features for {n} symbols")
  ```

- シグナル生成（features と ai_scores を基に signals テーブルへ）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2024, 1, 31), threshold=0.6)
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ（RSS から raw_news と news_symbols へ保存）
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes: 抽出対象の有効な銘柄コード集合
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)
  ```

- J-Quants の低レベル操作（必要に応じて）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

---

## 環境変数（主要一覧）

- JQUANTS_REFRESH_TOKEN — 必須: J-Quants リフレッシュトークン（Settings.jquants_refresh_token）
- KABU_API_PASSWORD — 必須: kabuAPI パスワード
- KABU_API_BASE_URL — 任意: kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — 必須: Slack Bot トークン
- SLACK_CHANNEL_ID — 必須: Slack チャンネル ID
- DUCKDB_PATH — 任意: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 任意: SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 任意: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — 任意: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 任意: 自動 .env 読み込みを無効化する場合は "1" を設定

注意: config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` / `.env.local` を読み込みます。パッケージ配布後も動作するように __file__ を起点に探索します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイルと役割の一覧です（抜粋）。

- kabusys/
  - __init__.py
  - config.py — 環境変数管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - schema.py — DuckDB スキーマ定義・初期化
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - news_collector.py — RSS ニュース収集・保存
    - calendar_management.py — 市場カレンダー判定・更新ジョブ
    - features.py — zscore_normalize の再エクスポート
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログ（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value の計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成ロジック
    - signal_generator.py — final_score 計算と signals 作成
  - execution/ — 発注／約定連携（空ディレクトリまたは将来的な実装）
  - monitoring/ — 監視／メトリクス関連（将来的な実装）

各モジュールはコメントに設計方針・参照すべきドキュメント（StrategyModel.md, DataPlatform.md 等）を記載しています。

---

## 運用上の注意

- DuckDB のデータファイルはバックアップを取り、適切なファイルパーミッション管理を行ってください。
- J-Quants API のレート制限（120 req/min）を尊重してください。jquants_client は内部で固定間隔スロットリングを行いますが、運用ジョブの同時実行には注意が必要です。
- ニュース収集では外部 URL を開くため SSRF 等の対策を実装していますが、運用環境に応じたホワイトリスト運用を検討してください。
- 本システムは研究・バックテスト用コードと本番発注ロジックを分離する設計になっています。実際に資金を投入する前に十分なテスト・監査を行ってください。
- env の取り扱い: `.env.example` を参考に `.env` を作成してください（.env ファイルは機密情報を含むためバージョン管理から除外すること）。

---

## 参考・拡張ポイント

- 実マーケットでの運用時は `KABUSYS_ENV=live` を設定し、paper_trading フラグや発注確認ワークフローを強化してください。
- AI スコアを格納する `ai_scores` テーブルを用いることでニュースや外部モデル出力を統合できます。
- execution 層の証券会社 API（kabuステーション等）との連携は切り離して実装することを推奨します（発注の冪等性・監査ログを優先）。

---

この README はコードベースの主要な使い方・構成を簡潔にまとめたものです。より詳細な実装方針や仕様（StrategyModel.md、DataPlatform.md、Research ドキュメント等）がプロジェクトに含まれている想定です。必要であればサンプルのジョブスクリプトや運用チェックリストのテンプレートも作成します。