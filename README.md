# KabuSys

日本株の自動売買／データプラットフォーム用ライブラリ群です。  
J-Quants から市場データを取得して DuckDB に蓄積し、研究用ファクター計算 → 特徴量合成 → シグナル生成までのワークフローを提供します。監査ログ、ニュース収集、マーケットカレンダー管理、ETL パイプラインなどの機能を備えています。

---

## 目次
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 簡単な使い方（サンプルコード）
- 環境変数一覧
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は以下の階層構造に基づくデータ＆戦略基盤を提供します。

- Raw Layer: J-Quants など外部ソースから取得した生データ（raw_prices / raw_financials / raw_news 等）
- Processed Layer: 整形済み市場データ（prices_daily / market_calendar / fundamentals 等）
- Feature Layer: 戦略・AI 用の特徴量（features / ai_scores 等）
- Execution Layer: シグナル・発注・約定・ポジション管理（signals / orders / trades / positions 等）
- Audit: シグナルから約定までのトレーサビリティ用テーブル群

主要コンポーネントは DuckDB をデータ格納先として想定しています。

---

## 主な機能
- J-Quants API クライアント（ページネーション・リトライ・トークン自動更新・レート制御）
- DuckDB スキーマ定義と初期化（冪等なテーブル作成）
- デイリー ETL パイプライン（市場カレンダー、株価、財務データの差分取得と保存）
- 特徴量計算（モメンタム / ボラティリティ / バリュー等のファクター算出）
- 特徴量合成（正規化・フィルタリング・features テーブルへの保存）
- シグナル生成（features と AI スコアを統合し BUY/SELL シグナルを生成）
- ニュース収集（RSS フィードからの収集、SSRF対策・トラッキングパラメータ除去・記事→銘柄紐付け）
- マーケットカレンダー管理（営業日判定、前後営業日取得、夜間更新ジョブ）
- 監査ログ（signal_events / order_requests / executions 等のテーブル群）
- 研究向けユーティリティ（forward returns、IC 計算、統計サマリー、Zスコア正規化）

---

## 必要条件
（実装で利用されているライブラリに基づく最小セット）
- Python 3.10+
- duckdb
- defusedxml
- （標準ライブラリ以外の HTTP や DB 周辺の依存があれば適宜追加）

※ 実際のプロジェクトでは requirements.txt / pyproject.toml に依存関係を明記してください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   （プロジェクトに requirements があればそれを利用。ここでは最低限の例）
   ```bash
   pip install duckdb defusedxml
   # あるいは
   # pip install -r requirements.txt
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（詳細は下記「環境変数一覧」参照）を設定してください。
   - 例: `.env`
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマの初期化
   Python コンソールまたはスクリプトで以下を実行：
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb
   ```

---

## 簡単な使い方（サンプル）

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 特徴量作成（features テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 15))
  print(f"{n} 銘柄の特徴量を作成しました")
  ```

- シグナル生成（signals テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today())
  print(f"{total} 件のシグナルを作成しました")
  ```

- ニュース収集ジョブ実行（RSS → raw_news、news_symbols への紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄コードの集合を渡すと記事中の4桁コード抽出で紐付けを行う
  res = run_news_collection(conn, known_codes={"7203", "6758"})
  print(res)  # {source_name: saved_count}
  ```

- マーケットカレンダー更新ジョブ（夜間バッチ想定）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"market_calendar に {saved} 件保存しました")
  ```

---

## 環境変数一覧（主要なもの）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 非空にすると .env 自動読み込みを無効化

注意: Settings クラス経由で安全に取得することを推奨します（kabusys.config.settings）。

---

## 開発・運用上のポイント（簡潔に）
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）から行われます。CI やテストで無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は冪等です。既存テーブルは上書きされません。
- J-Quants API 呼び出しはレート制御・リトライ・トークン自動更新を備えています。長時間のバッチではレートに注意してください。
- ニュース収集は SSRF 対策や Gzip/BOM サイズチェック等を実装済みです。
- 特徴量作成・シグナル生成はルックアヘッドバイアスを避けるよう設計されています（target_date 時点のデータのみ使用）。

---

## ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（取得 + 保存ユーティリティ）
  - news_collector.py             — RSS ニュース収集／保存
  - schema.py                     — DuckDB スキーマ定義・初期化
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - features.py                   — features 関連公開インターフェース
  - stats.py                      — Zスコア等の統計ユーティリティ
  - calendar_management.py        — カレンダー管理 / ジョブ
  - audit.py                      — 監査ログ（signal_events, order_requests, executions）
  - (他: quality 等の品質チェックモジュール想定)
- research/
  - __init__.py
  - factor_research.py            — モメンタム / ボラティリティ / バリューの計算
  - feature_exploration.py        — forward returns / IC / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py        — 生ファクターの正規化・合成 → features テーブル
  - signal_generator.py           — features/ai_scores を統合して signals を生成
- execution/
  - __init__.py                   — 発注／実行層のエントリ（今後の実装想定）
- monitoring/                      — 監視・アラート関連（存在が __all__ に含まれている想定）

（上記はコードベースから抽出した主要ファイルの一覧です。）

---

## 貢献・拡張のヒント
- quality（品質チェック）モジュールを実装して ETL の品質検査を強化してください。
- execution 層と証券会社ブリッジ（kabuステーション等）の実装を追加して実取引フローを完成させることができます。
- AI スコア生成ルーチン（外部モデル呼び出し）を ai_scores テーブルに投入する処理を追加すると、signal_generator が利用できます。
- ロギング、メトリクス（Prometheus など）、ジョブスケジューリング（Airflow / cron / Prefect）との統合を検討してください。

---

必要であれば、README に含める具体的な実行コマンド例、CI セットアップ、docker-compose や systemd ユニット例、さらに詳しいテーブル定義ドキュメント（DataSchema.md 相当）を追記します。どの部分を詳しく書き加えたいか教えてください。