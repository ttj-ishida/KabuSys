# KabuSys

バージョン: 0.1.0

KabuSys は日本株を対象としたデータプラットフォーム兼自動売買システムのライブラリです。J‑Quants API からのデータ取得（OHLCV・財務・マーケットカレンダー）・DuckDB による ETL／スキーマ管理・特徴量（features）計算・シグナル生成・ニュース収集など、研究→運用のワークフローを意識したモジュール群を提供します。

主な目的：
- データの差分取得と冪等保存（DuckDB）
- 研究環境でのファクター計算・探索（ルックアヘッドバイアスを回避）
- 戦略用特徴量の構築とシグナル生成（BUY/SELL）
- ニュース収集と銘柄紐付け（RSS）
- 発注／監査用のスキーマ基盤（設計上の階層化）

---

## 機能一覧

- 環境設定管理
  - .env ファイルおよび環境変数から設定を読み込む（自動ロード有効/無効化可）
- データ取得（J‑Quants クライアント）
  - daily quotes（OHLCV）取得・保存（ページネーション対応、トークン自動リフレッシュ、リトライ・レート制御）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
- ETL パイプライン
  - 差分取得（最終取得日ベース）／バックフィル／品質チェックを包含する日次 ETL（run_daily_etl）
  - 市場カレンダーの夜間更新ジョブ
- データスキーマ（DuckDB）
  - raw → processed → feature → execution 層のテーブル定義と初期化（init_schema）
  - 各種インデックスを含む冪等な DDL 実行
- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
  - Z スコア正規化ユーティリティ
- 特徴量生成（strategy.feature_engineering）
  - research で算出した raw factor を統合・正規化して features テーブルへ UPSERT（日付単位の置換、冪等）
  - ユニバースフィルタ（最低株価・流動性）を適用
- シグナル生成（strategy.signal_generator）
  - features / ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals テーブルへ保存（冪等）
  - Bear レジーム抑制、売り条件（ストップロス等）を含む
- ニュース収集（data.news_collector）
  - RSS 取得（SSRF/リダイレクト検査、gzip 対応、XML 安全パース）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等保存
  - 記事 -> 銘柄の紐付け機能（抽出パターンと既知銘柄セットでフィルタ）
- 監査／オーディット（data.audit）
  - signal → order → execution の追跡用テーブル設計（監査トレース）

---

## セットアップ手順

前提
- Python 3.8+（ソースによっては 3.10+ を想定）
- OS による一般的なビルド環境（pip, venv 等）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -e .   # 開発インストール。requirements.txt または pyproject に依存が定義されている想定
   - 必要な主なライブラリ（例）
     - duckdb
     - defusedxml
   - （プロジェクトに依存ファイルがない場合は requirements を確認してください）
4. 環境変数の設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（既定）
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード（execution 層を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意（デフォルトあり）
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live) (default: development)
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)
   - 自動 .env 読み込みを無効化する:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. DuckDB スキーマ初期化
   - Python REPL かスクリプトで実行:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を渡すとインメモリ DB を利用できます。

---

## 使い方（簡易例）

以下は代表的な利用例です。実運用ではログ設定・例外ハンドリング・スケジュール実行等を追加してください。

1) スキーマ初期化
   - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

2) 日次 ETL（市場カレンダー、株価、財務の差分取得 + 品質チェック）
   - サンプルスクリプト:
     - from datetime import date
       from kabusys.data.schema import init_schema
       from kabusys.data.pipeline import run_daily_etl
       conn = init_schema('data/kabusys.duckdb')
       res = run_daily_etl(conn, target_date=date.today())
       print(res.to_dict())
   - 戻り値は ETLResult オブジェクト（取得件数・保存件数・品質問題・エラー等を含む）

3) 特徴量構築（features テーブルの生成）
   - from datetime import date
     from kabusys.data.schema import get_connection, init_schema
     from kabusys.strategy import build_features
     conn = init_schema('data/kabusys.duckdb')
     n = build_features(conn, target_date=date.today())
     print(f"built {n} features")

4) シグナル生成
   - from datetime import date
     from kabusys.data.schema import init_schema
     from kabusys.strategy import generate_signals
     conn = init_schema('data/kabusys.duckdb')
     total = generate_signals(conn, target_date=date.today(), threshold=0.60)
     print(f"signals generated: {total}")

5) ニュース収集ジョブ（RSS）
   - from kabusys.data.news_collector import run_news_collection
     from kabusys.data.schema import init_schema
     conn = init_schema('data/kabusys.duckdb')
     results = run_news_collection(conn, sources=None, known_codes={'7203','6758'})
     print(results)

6) カレンダー更新ジョブ（夜間バッチ）
   - from kabusys.data.calendar_management import calendar_update_job
     conn = init_schema('data/kabusys.duckdb')
     saved = calendar_update_job(conn)
     print(f"saved calendar records: {saved}")

ヒント:
- すべての「日付単位の置換」は冪等に設計されています（既存データは削除して再挿入）。
- J‑Quants API 呼び出しはレート制御 / リトライ / トークン自動リフレッシュを含みます。
- research モジュールは外部依存を少なく設計されており、単体で統計解析が可能です。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須 for execution): kabu ステーション API パスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須 for slack): Slack 通知で使用
- SLACK_CHANNEL_ID (必須 for slack): Slack チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意): development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意): DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 (任意): 自動 .env 読み込みを無効にする（テスト向け）

注意: Settings クラスは必須変数が未設定のままアクセスされると ValueError を発生させます。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの例: src/kabusys/ 以下）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J‑Quants API クライアント（取得・保存）
    - news_collector.py             — RSS ニュース収集・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義 / init_schema
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - features.py                   — features 公開インターフェース
    - calendar_management.py        — マーケットカレンダー関連ユーティリティ
    - audit.py                      — 監査ログ用テーブル定義
    - audit... (その他データ関連)
  - research/
    - __init__.py
    - factor_research.py            — momentum / volatility / value の計算
    - feature_exploration.py        — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py        — features を構築して features テーブルへ保存
    - signal_generator.py           — final_score 計算、BUY/SELL 生成
  - execution/                      — 発注 / execution 層（スケルトン）
  - monitoring/                     — 監視 / メトリクス（スケルトン）

※ 上記は主要モジュールの抜粋です。細かい実装や追加モジュールはソースツリーを参照してください。

---

## 運用・開発上の注意点

- ルックアヘッドバイアス防止: strategy / research モジュールは target_date 時点で利用可能なデータのみを参照する設計になっています。
- 冪等性: 多くの DB 保存処理は ON CONFLICT や INSERT RETURNING を用い、再実行に耐えるようになっています。
- テスト: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを抑制できます。ID トークン等はテスト時に注入してください。
- セキュリティ: news_collector は SSRF 対策（リダイレクト先検査・プライベート IP 拒否）や defusedxml による XML 安全化を実装しています。
- 運用ジョブ: ETL・calendar_update_job・news_collection 等は cron / Airflow / Prefect などで定期実行してください。

---

必要であれば、README に以下を追加できます：
- 具体的な requirements.txt / pyproject.toml の依存一覧
- CI/CD（テスト・ビルド）の手順
- サンプル .env.example
- API の詳細な呼び出し例（パラメータ説明）

追記や調整したい箇所があれば指示してください。