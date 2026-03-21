# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログ・スキーマなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、J-Quants 等からの市場データを DuckDB に蓄積し、研究で作成した生ファクターを正規化して特徴量を構築、戦略に基づく売買シグナルを生成する一連の処理を提供する Python パッケージです。  
設計上の特徴：

- DuckDB を用いたオンディスク/インメモリ DB（スキーマ定義・初期化済み）
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- ETL（差分更新・バックフィル・品質チェック）パイプライン
- ニュース収集（RSS）・記事→銘柄紐付け機能（SSRF 対策・トラッキング除去）
- 研究（research）モジュールにおけるファクター計算・評価ユーティリティ
- 戦略層（feature_engineering / signal_generator）での特徴量生成および BUY/SELL シグナル生成
- 監査ログ（オーダー／約定トレース）用スキーマ

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出：.git / pyproject.toml）
  - 必須環境変数のラップ（settings）

- データ取得 / 保存
  - J-Quants クライアント（fetch/save：日足、財務、カレンダー）
  - レート制御・リトライ・トークン自動リフレッシュ
  - raw → processed の DuckDB スキーマ（冪等性あり）

- ETL / パイプライン
  - run_daily_etl：カレンダー・株価・財務の差分取得＋品質チェック
  - 差分更新とバックフィル対応

- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman ρ）、統計サマリー、ランク変換

- 特徴量・戦略
  - build_features：Z スコア正規化・ユニバースフィルタ・features テーブルへの保存
  - generate_signals：ai_scores 統合、重み付け、Bear フィルタ、BUY/SELL の生成・保存

- ニュース収集
  - RSS フィードの取得、正規化、raw_news 保存、銘柄抽出と紐付け
  - SSRF 対策、受信サイズ制限、XML パースの安全化

- スキーマ / 監査
  - DuckDB のスキーマ初期化（raw / processed / feature / execution / audit）
  - 監査ログ（signal_events / order_requests / executions）によるトレース可能性

---

## 必要な環境変数

主要な環境変数（Settings により取得）：

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション等の API パスワード
- KABU_API_BASE_URL（任意）: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN（必須）: Slack 通知用トークン
- SLACK_CHANNEL_ID（必須）: Slack チャネル ID
- DUCKDB_PATH（任意）: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（任意）: 監視 DB 等（デフォルト: data/monitoring.db）
- KABUSYS_ENV（任意）: development / paper_trading / live（デフォルト development）
- LOG_LEVEL（任意）: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

備考:
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（テスト時など自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット）。

---

## セットアップ手順

1. Python（3.10+ を推奨）をインストールします。

2. リポジトリをクローンしてセットアップ（開発環境向け）:
   - pip を使う例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install duckdb defusedxml
     # 任意でパッケージを editable install（setup.py/pyproject.toml がある場合）
     # pip install -e .
     ```

   - 必要な主な外部依存（コード参照）:
     - duckdb
     - defusedxml
     - （標準ライブラリ以外の依存は将来的に requirements.txt にまとめてください）

3. 環境変数を設定:
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートしてください。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマを初期化:
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
     conn.close()
     ```

---

## 使い方（サンプル）

以下は主要な処理を呼び出す簡易例です。

- 日次 ETL（市場カレンダー・株価・財務の差分取得 + 品質チェック）:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())
  conn.close()
  ```

- 特徴量の構築（build_features）:
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  print("features upserted:", n)
  conn.close()
  ```

- シグナル生成（generate_signals）:
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print("signals written:", total)
  conn.close()
  ```

- ニュース収集（RSS）:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は抽出に使う銘柄コード集合（例: {"7203", "6758", ...}）
  results = run_news_collection(conn, known_codes=None)  # known_codes を渡すと紐付けまで実施
  print(results)
  conn.close()
  ```

- J-Quants API へ直接アクセス（取得 / 保存）:
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved", saved)
  conn.close()
  ```

---

## 開発者向けメモ

- 自動 .env 読み込みはパッケージ import 時に実行されます。テストなどで抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境に設定してください。
- J-Quants クライアントは内部で固定間隔の RateLimiter と指数バックオフ retry を実装しています。401 はトークン更新を試みます。
- ニュース収集は SSRF 対策、gzip サイズチェック、XML パーサの防御を実装しています。
- DuckDB のスキーマは冪等（CREATE TABLE IF NOT EXISTS）かつ INDEX を作成します。初回は `init_schema()` を必ず呼んでください。
- strategy 層は発注実装（execution との接続）には依存しない設計です。signals テーブルへ出力後、別レイヤで発注を処理する想定です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - schema.py              — DuckDB スキーマ定義＆初期化
    - pipeline.py            — ETL（run_daily_etl 等）
    - news_collector.py      — RSS ニュース収集 / 保存 / 銘柄抽出
    - calendar_management.py — 市場カレンダー操作（営業日判定等）
    - audit.py               — 監査ログ用 DDL と初期化
    - features.py            — データ層の feature ユーティリティ（zscore 再エクスポート）
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py     — momentum/volatility/value の計算
    - feature_exploration.py — 将来リターン・IC・要約統計
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成（正規化・フィルタ）
    - signal_generator.py    — final_score 計算・BUY/SELL 生成
  - execution/
    - __init__.py            — 発注・執行層（将来的な拡張ポイント）
  - monitoring/              — 監視・通知関連（Slack 等を想定：パッケージ内で参照あり）

---

## 注意事項 / 制限

- 本パッケージは資金運用を直接行うものではありません。実際の発注・本番運用を開始する前に十分な検証を行ってください。
- J-Quants や外部 API 利用にあたっては各サービスの利用規約・レート制限に従ってください（本クライアントは一部制御を実装していますが、最終責任は利用者にあります）。
- DuckDB スキーマや SQL は将来的に変更される可能性があります。運用時はマイグレーションを検討してください。

---

必要であれば、README に含めるより具体的なセットアップコマンド（requirements.txt の提案）、CI / テスト実行手順、サンプルデータでのハンズオン手順なども作成できます。どの情報を追加希望か教えてください。