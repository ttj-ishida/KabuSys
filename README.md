# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）の README。

このリポジトリは、J-Quants などの外部データソースから市場データを取得して DuckDB に格納し、研究用ファクターの計算、特徴量正規化、シグナル生成、ニュース収集、監査ログなどを行うためのモジュール群を提供します。発注実行（broker 連携）部分は抽象化されており、戦略ロジックと実行ロジックの分離を意識した設計になっています。

主な用途
- データ ETL（株価・財務・市場カレンダー）
- 特徴量（features）生成
- 戦略シグナル生成（signals）
- ニュース収集と銘柄紐付け
- DuckDB ベースのスキーマ管理と監査ログ

---

## 特徴（機能一覧）

- データ収集（J-Quants API クライアント）
  - 日足（OHLCV）、財務データ、JPX カレンダーのページネーション対応取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ
- ETL パイプライン
  - 差分更新（バックフィル対応）、品質チェックとの連携
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル定義（冪等）
- 研究（research）/ ファクター計算
  - momentum / volatility / value などのファクター算出
  - 将来リターン・IC 計算・統計サマリ（研究用途）
- 特徴量エンジニアリング
  - ファクターのユニバースフィルタ、Z スコア正規化、クリッピング、features テーブルへの UPSERT
- シグナル生成
  - features と ai_scores を統合して final_score を計算
  - Buy / Sell シグナル生成（Bear レジーム抑制、ストップロス等）
  - signals テーブルへの日次置換（冪等）
- ニュース収集
  - RSS フィード取得（SSRF 対策、サイズ制限、XML 安全パース）
  - raw_news / news_symbols への冪等保存
  - 記事から銘柄コード抽出（4桁コード）
- 監査ログ（audit）
  - signal → order_request → execution の追跡用テーブル群（UUID ベース）
- 設定読み込み
  - .env / .env.local / OS 環境変数からの設定自動読み込み（必要に応じて無効化可）

---

## 動作環境・依存

- Python 3.10 以上（PEP 604 の Union 演算子などの構文を使用）
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml
- 標準ライブラリで十分な部分も多いですが、実行環境に合わせて追加でインストールしてください。

例：
pip install duckdb defusedxml

（プロジェクトで requirements.txt / pyproject.toml があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存をインストールします。
   - pip install duckdb defusedxml

3. 環境変数を準備します。
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local は .env を上書き）
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必要な環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD      — kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL      — kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN        — Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID       — Slack チャンネル ID（必須）
     - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH            — SQLite（監視用 DB 等）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV            — 実行環境: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL              — ログレベル: DEBUG/INFO/...（デフォルト: INFO）

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python REPL かスクリプトで init_schema を呼び出します。
   - 例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を渡すとインメモリ DB になります。

---

## 使い方（簡単な例）

以下はライブラリの代表的な呼び出し例です。ご自身の運用スクリプトやバッチからこれらを呼んでください。

- DuckDB 初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL（J-Quants からデータ取得 → 保存 → 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())

- 特徴量構築（features）
  from kabusys.strategy import build_features
  build_features(conn, target_date=date.today())

- シグナル生成
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date=date.today(), threshold=0.6)

- ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出に利用する有効コードの set（None で紐付けスキップ）
  run_news_collection(conn, sources=None, known_codes={"7203","6758"})

- J-Quants API 呼び出し（低レベル）
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))

- 設定値の参照
  from kabusys.config import settings
  token = settings.jquants_refresh_token

ログレベルや環境は環境変数（KABUSYS_ENV, LOG_LEVEL）で制御します。

---

## 実行上の注意・セキュリティ

- 秘密情報（トークン・パスワード）は .env に置くか、OS 環境変数で渡してください。リポジトリに plaintext を置かないでください。
- J-Quants API にはレート制限があるため、fetch 系関数は内部でレート制御・リトライを行います。大量取得や短時間ループは避けてください。
- RSS フィード取得には SSRF / XML Bomb 対策が組み込まれていますが、外部コンテンツの扱いには常に注意してください。
- DuckDB ファイル（デフォルト data/kabusys.duckdb）は定期的にバックアップしてください。
- 本システムは研究・自動売買支援用のライブラリであり、ライブマネー運用時は十分な検証・監査を行ってください。KabuSys 自体は発注実行の最終責任を負いません（実際の証券会社連携部分は別実装が必要です）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理（.env 自動読み込み）
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py           — RSS ニュース収集・前処理・保存
  - schema.py                   — DuckDB スキーマ定義・初期化
  - stats.py                    — 統計ユーティリティ（zscore_normalize）
  - pipeline.py                 — ETL パイプライン（run_daily_etl など）
  - features.py                 — data 層の features 再エクスポート
  - calendar_management.py      — 市場カレンダー更新・営業日判定ユーティリティ
  - audit.py                    — 監査ログ用テーブル定義
- research/
  - __init__.py
  - factor_research.py          — momentum/volatility/value 計算
  - feature_exploration.py      — IC / forward returns / summary 等の研究ユーティリティ
- strategy/
  - __init__.py
  - feature_engineering.py      — features を構築して features テーブルへ保存
  - signal_generator.py         — final_score 計算と signals への書き込み
- execution/                     — 発注実行関連（空パッケージ、実装は運用側で拡張）
- monitoring/                    — 監視用コード置き場（将来的に）

（各ファイルには詳細な docstring / 実装コメントがあるため参照してください）

---

## 参考・拡張ポイント

- broker 連携（kabuステーションや証券会社 API）を実装して signal_queue → orders → executions のフローを完成させる
- AI スコア（ai_scores）生成パイプラインの追加（ニュース + NLP モデル）
- 運用用 CLI / ジョブスケジューラ（Airflow / cron 等）との統合
- テストコード・CI（自動化）を追加して品質保証を強化

---

もし README に追記したい「実行スクリプト例」や「CI 設定」「Docker 化」などの要望があれば、目的にあわせたサンプルを作成します。