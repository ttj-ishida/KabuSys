# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB を内部データベースとして用い、J-Quants API や RSS を取り込み、特徴量生成 → シグナル生成 → 発注（実装層あり）までのワークフローをサポートします。

主な設計方針：
- データ取得 → 前処理 → 特徴量 → シグナル を明確なレイヤーで分離
- 冪等性（DB の ON CONFLICT / トランザクション）を重視
- ルックアヘッドバイアス防止（target_date 時点のデータのみを参照）
- 外部 API 呼び出しは RateLimiter / リトライ / token リフレッシュ等で堅牢化
- research モジュールは本番口座にアクセスしない（分析専用）

バージョン: 0.1.0

---

## 主要機能一覧

- データ収集
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - RSS ニュース収集（トラッキングパラメータ除去、SSRF対策、gzip対応）
- データ格納・スキーマ管理
  - DuckDB スキーマ定義 / 初期化（raw / processed / feature / execution レイヤ）
- ETL パイプライン
  - 差分取得・バックフィル・品質チェックを考慮した日次 ETL
- 研究（research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Spearman）・統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクターの正規化（Z スコア）・ユニバースフィルタ・features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - 正規化ファクターと AI スコアを統合して final_score を算出し BUY/SELL シグナル生成
  - Bear レジーム判定、エグジット（ストップロス等）判定、signals テーブルへの書き込み
- ユーティリティ
  - 統計ユーティリティ（zscore_normalize 等）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュースの銘柄抽出（4桁コード抽出）と紐付け

---

## 要件

- Python 3.10 以上（型アノテーションに `X | None` を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）を行う場合は適切な環境変数（認証トークン等）を設定

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / ダウンロードして作業ディレクトリへ移動。

2. 仮想環境を作成・有効化（推奨）:
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 必要パッケージをインストール（例）:
   - pip install "duckdb" "defusedxml"
   - またはプロジェクトの依存定義に従ってインストール

4. 本パッケージを開発モードでインストール（任意）:
   - pip install -e .

5. 環境変数設定:
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込みます（詳細は下記）。
   - 必須環境変数（実行に必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注を行う場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知を受け取るチャンネル ID
   - その他（省略時はデフォルトが利用されます）:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/... （デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — （モニタリング用）デフォルト: data/monitoring.db
   - 自動 .env 読み込みを無効にする:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

6. DuckDB スキーマ初期化（例）:
   - Python で:
     ```py
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")  # ファイルに保存
     # またはメモリDB:
     # conn = init_schema(":memory:")
     ```
   - これにより、全テーブルとインデックスが作成されます。

---

## 使い方（主要ワークフロー）

以下は簡単なコード例です。実運用ではログ設定・例外処理・スケジューラ等を組み合わせてください。

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）:
  ```py
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量ビルド（features テーブル作成）:
  ```py
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")  # 事前に init_schema を実行
  count = build_features(conn, target_date=date.today())
  print(f"features upserted: {count}")
  ```

- シグナル生成（signals テーブル書き込み）:
  ```py
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total_signals}")
  ```

- ニュース収集ジョブ:
  ```py
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を渡すと記事->銘柄紐付けを行う
  known_codes = {"7203", "6758", "9432"}  # 実運用では全銘柄コードを用意
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- J-Quants からデータ取得（低レベル）:
  ```py
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  # fetch_daily_quotes() は id_token を自動取得するため通常は引数省略可
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## .env / 環境変数の自動読み込みについて

- パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env` → `.env.local` の順に読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- テスト等で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須環境変数が足りない場合、Settings のプロパティアクセス時に ValueError が発生します。例: `from kabusys.config import settings; settings.jquants_refresh_token`

---

## ディレクトリ構成

主要なソース配置（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py        — RSS ニュース収集 / 保存
    - schema.py                — DuckDB スキーマ定義・初期化
    - stats.py                 — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — 市場カレンダー管理
    - audit.py                 — 監査ログテーブル定義
    - features.py              — features の公開インターフェース
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/volatility/value）
    - feature_exploration.py   — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py   — ファクター統合・正規化 → features テーブルへ
    - signal_generator.py      — final_score 計算・BUY/SELL シグナル生成
  - execution/                  — 発注・ブローカー連携（空の __init__ がある）
  - monitoring/                 — モニタリング用 DB/仕組み（未記載詳細）

ドキュメント参照ファイル（コード内コメント）:
- DataPlatform.md, StrategyModel.md, Research/… など設計ドキュメント（コードコメントで参照されていますが、実ファイルは別途管理される想定）

---

## ログ／環境モード

- KABUSYS_ENV: development / paper_trading / live のいずれか。ライブ運用時は `live` に設定してください（Settings.is_live 等が参照）。
- LOG_LEVEL: デフォルト INFO。DEBUG にすると内部処理ログが詳細に出ます。

---

## 注意事項 / 運用上のヒント

- DuckDB の初期化は一度行えばよく、init_schema() は既存テーブルがあればスキップするため安全に呼べます。
- ETL は差分取得ロジックを持ち、バックフィル（デフォルト 3 日）を使って API の後出し修正を吸収します。
- J-Quants API のレート制限（120 req/min）や 401 の自動リフレッシュ、リトライロジックは jquants_client に実装されています。
- RSS 取得時は SSRF 対策やサイズチェックを行っていますが、信頼できるフィードソースを用いることが重要です。
- シグナル生成は features と ai_scores を参照します。AI スコアが無い場合は中立補完（0.5）で処理されます。
- 発注 / ブローカー連携を行う場合は、必ず sandbox/paper_trading 環境で充分なテストを行ってください。

---

## 貢献 / 拡張

- 新しいファクターやフィードの追加は各モジュール（research.factor_research / data/news_collector）を拡張してください。
- schema.py でテーブルやインデックスを追加することでデータレイヤを拡張できます（DDL は冪等）。
- テスト追加・CI の導入を推奨します（KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境依存を外せます）。

---

README は以上です。必要であれば以下について追記できます：
- 具体的な .env.example のテンプレート
- よくあるトラブルシューティング項目（接続エラー、権限、レート制限）
- 具体的なスケジュール例（cron / Airflow / systemd timer）と運用フロー

どの追加情報を望みますか？