# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）のリポジトリ向け README。  
本ドキュメントはプロジェクトの概要、機能、セットアップ手順、使い方（主要 API の利用例）、およびディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するためのモジュール群です。  
主に以下のレイヤーを持つ設計になっています。

- Data Platform（データ取得 / ETL / スキーマ管理）
- Research（ファクター計算 / リサーチ用ユーティリティ）
- Strategy（特徴量生成 / シグナル生成）
- Execution（発注・約定・ポジション監視用テーブル等のインターフェース）
- Monitoring（監視・ログ・Slack 通知等 ※実装はプロジェクト側で補完）

設計上のポイント
- DuckDB をローカル DB として使い、Raw → Processed → Feature → Execution の多段構造を採用
- J-Quants API からのデータ取得はレート制御・リトライ・トークン自動リフレッシュ等を実装
- ETL と品質チェックは冪等に設計（ON CONFLICT / トランザクション）
- 研究用コードは本番システムに直接依存しない（ルックアヘッドバイアス対策）

---

## 主な機能一覧

- データ取得（J-Quants API クライアント）
  - 日次株価、財務データ、JPX カレンダーを取得・保存
  - レートリミット/リトライ/トークン自動更新対応
- DuckDB スキーマ定義と初期化
  - raw_prices / prices_daily / features / ai_scores / signals / orders / executions / positions など
- ETL パイプライン
  - 差分取得（最終取得日に基づく差分）、バックフィル、品質チェック
- ニュース収集
  - RSS フィード収集、URL 正規化、記事ID生成、銘柄抽出、冪等保存
- 研究用ユーティリティ
  - momentum/volatility/value 等のファクター計算、将来リターン（forward returns）、IC 計算、統計サマリー
- 戦略（特徴量エンジニアリング／シグナル生成）
  - features テーブル生成（Zスコア正規化・ユニバースフィルタ）
  - final_score 計算、BUY / SELL シグナルの生成（売り条件・Bear レジーム対応）
- 監査ログ／トレーサビリティ（order_requests / executions / signal_events 等）

---

## セットアップ手順

前提
- Python 3.9+（type annotation に | を使っているため 3.10 推奨）
- DuckDB を用いるためローカル環境にインストール可能であること

1. リポジトリをクローンし、開発用インストール（任意）
   - pip install -e . が可能な構成ならそれでインストールします（pyproject.toml 等がある前提）。
   - 直接モジュールを使う場合は PYTHONPATH に `src` を追加するか、パッケージをインストールしてください。

2. 必要な Python パッケージをインストール
   - 最低依存（例）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

3. 環境変数 / .env の設定
   - プロジェクトルート（.git か pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（`src/kabusys/config.py` の自動ロード）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必要な主要環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
     - KABU_API_BASE_URL — kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN — Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
     - DUCKDB_PATH — DuckDB ファイルパス（省略時 data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（省略時 data/monitoring.db）
     - KABUSYS_ENV — development / paper_trading / live（省略時 development）
     - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（省略時 INFO）

4. DuckDB スキーマ初期化
   - アプリ起動前にスキーマを作成します（1 回実行すれば OK）。
   - 例:
     - from kabusys.data.schema import init_schema
     - conn = init_schema(settings.duckdb_path)

---

## 使い方（代表的な API と実行例）

以下は Python REPL やスクリプト内での例です。必要に応じて import 文を実行してください。

1. 初期化（DB 作成）
   - from kabusys.config import settings
   - from kabusys.data.schema import init_schema
   - conn = init_schema(settings.duckdb_path)

2. 日次 ETL 実行（株価 / 財務 / カレンダー）
   - from kabusys.data.pipeline import run_daily_etl
   - result = run_daily_etl(conn)  # target_date を渡さなければ本日で実行
   - print(result.to_dict())

3. 市場カレンダー更新ジョブ（夜間バッチ向け）
   - from kabusys.data.calendar_management import calendar_update_job
   - saved = calendar_update_job(conn)
   - print("calendar saved:", saved)

4. ニュース収集ジョブ
   - from kabusys.data.news_collector import run_news_collection
   - known_codes = {"7203","6758", ...}  # 既知の銘柄コードセット（抽出用）
   - results = run_news_collection(conn, known_codes=known_codes)
   - print(results)

5. ファクター → features テーブル構築
   - from kabusys.strategy import build_features
   - from datetime import date
   - n = build_features(conn, date(2024, 1, 12))
   - print("features upserted:", n)

6. シグナル生成
   - from kabusys.strategy import generate_signals
   - total = generate_signals(conn, date(2024, 1, 12))
   - print("signals generated:", total)
   - 追加オプション: generate_signals(conn, target_date, threshold=0.65, weights={"momentum":0.5, "value":0.2, ...})

7. DuckDB へのデータ保存（J-Quants 取得→保存）
   - from kabusys.data import jquants_client as jq
   - records = jq.fetch_daily_quotes(date_from=..., date_to=...)
   - saved = jq.save_daily_quotes(conn, records)

主な戻り値や挙動
- run_daily_etl は ETLResult オブジェクトを返します（品質チェックやエラー情報を含む）。
- features / signals の書き込みは「日付単位で置換（DELETE→INSERT）」による冪等処理です。
- J-Quants クライアントは内部でレート制御・リトライ・トークンリフレッシュを行います。

---

## 環境変数と .env の自動読み込み

- 自動読み込みの優先順位:
  1. OS 環境変数
  2. .env.local（存在する場合、既存の OS 環境変数は保護される）
  3. .env
- 自動ロードを無効化する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env のパースは shell ライク（export KEY=val、コメント、クォートのエスケープ等）をサポートします。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルのツリー（src 以下）です。実際のリポジトリではさらにファイルが存在する場合があります。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - schema.py
      - jquants_client.py
      - pipeline.py
      - news_collector.py
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
      - pipeline.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/  (モニタリング関連の実装を想定)

（上記は本リポジトリの主要モジュールを整理したものです）

---

## 開発上の注意点 / 補足

- DuckDB のスキーマ初期化は init_schema() を用いて行ってください。初回のみ親フォルダの作成を自動で行います。
- J-Quants の API トークン（refresh token）は必須です。get_id_token() は settings.jquants_refresh_token を参照します。
- ニュース収集では SSRF 対策、XML の安全パース、レスポンスサイズ上限、トラッキングパラメータ除去等を実装していますが、運用時はニュースソースの数や接続タイムアウト等を調整してください。
- シグナル生成は戦略仕様（StrategyModel.md）に準拠したロジックを含みます。運用前にシミュレーション・バックテストを十分に行ってください。
- 本パッケージは外部通信（J-Quants / RSS / 証券会社 API）を行うため、テスト時は環境変数の注入や外部呼び出しのモックを推奨します。config では自動 .env ロードを無効化できます。

---

## 問い合わせ / 貢献

バグ報告や改善提案、プルリクエストはリポジトリの Issue / PR を用いてお願いします。README に記載されていない実装意図や仕様書（DataPlatform.md、StrategyModel.md 等）が別途ある場合はそちらも参照してください。

---

以上。必要であれば README にサンプル .env.example や docker-compose / systemd 用の起動例、さらに詳細な CLI スクリプト例（ETL の定期実行、監視ジョブ）を追加します。どの情報を追加したいか教えてください。