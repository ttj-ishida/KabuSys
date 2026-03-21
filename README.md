# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリです。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・実行レイヤのスキーマとユーティリティを含み、研究（research）用途と運用（production）用途の両方を想定して設計されています。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群から構成されます：

- データ取得 / 保存（J-Quants API、RSSニュース）と DuckDB への永続化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（正規化、ユニバースフィルタ）
- シグナル生成（ファクター＋AIスコアの統合、BUY/SELL 判定）
- マーケットカレンダー管理（JPX カレンダー）
- ニュース収集と銘柄紐付け（RSS→raw_news / news_symbols）
- DuckDB スキーマ定義・初期化、監査ログスキーマ

設計の要点：
- ルックアヘッドバイアス回避のため「target_date 時点の情報のみ」を利用
- DuckDB を用いたローカル DB（:memory: も利用可）
- 冪等性（ON CONFLICT / INSERT … DO UPDATE）を意識した保存設計
- 外部依存を最小化（標準ライブラリ＋必須パッケージで動作する実装）

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証・ページネーション・レート制御・リトライ）
  - pipeline: 日次 ETL（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - schema: DuckDB スキーマ定義と init_schema()
  - calendar_management: 営業日判定・次/前営業日取得・カレンダー更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログテーブル定義
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering.build_features: research で計算した生ファクターを正規化し features テーブルへ保存
  - signal_generator.generate_signals: features + ai_scores を統合して BUY / SELL シグナルを生成し signals テーブルへ保存
- config: 環境変数管理（.env の自動読み込み、必須チェック）
- execution / monitoring: 発注・監視用のプレースホルダ（パッケージ API の公開面は __all__ に記載）

---

## 必要要件（例）

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - defusedxml

production 環境では他に Slack 連携等を使う場合の依存が必要になることがあります。実際の配布パッケージ（pyproject.toml / requirements.txt）がある場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリへ移動

   git clone <repo_url>
   cd <repo>

2. 仮想環境の作成（任意）

   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール（例）

   pip install duckdb defusedxml

   ※ 実際はプロジェクトの requirements / pyproject を利用してください。

4. 環境変数の設定

   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードは無効化可能）。

   最低限設定が必須の環境変数：
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（発注を使う場合）
   - SLACK_BOT_TOKEN       : Slack Bot トークン（通知を行う場合）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（通知を行う場合）

   オプション：
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite（監視用 DB）パス（デフォルト data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env ロードを無効化

   .env の簡単な例（実運用ではシークレット管理を推奨）:
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

5. DuckDB スキーマ初期化

   Python から init_schema を呼び出して DB を作成します：

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   またはスクリプトや CLI を用意して実行してください。

---

## 使い方（代表的なワークフロー）

以下は主要な操作例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

1. DB 初期化

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

2. 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）

   from datetime import date
   from kabusys.data.pipeline import run_daily_etl, ETLResult
   result = run_daily_etl(conn, target_date=date.today())
   if result.has_errors:
       print("ETL 中にエラーが発生しました:", result.errors)

3. 特徴量構築（features テーブルへ保存）

   from datetime import date
   from kabusys.strategy import build_features
   count = build_features(conn, target_date=date.today())
   print(f"{count} 銘柄の特徴量を作成しました。")

4. シグナル生成（signals テーブルへ保存）

   from datetime import date
   from kabusys.strategy import generate_signals
   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"{total} 件のシグナルを作成しました。")

   - weights 引数でファクター重みを上書き可能。辞書で {"momentum":0.5, "value":0.2, ...} のように指定すると、実装側で既知キーのみ受け付け正規化されます。

5. ニュース収集ジョブ（RSS -> raw_news, news_symbols）

   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
   print(results)

6. マーケットカレンダー更新（夜間ジョブ）

   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"保存件数: {saved}")

7. 研究用ユーティリティ

   - 将来リターン計算: calc_forward_returns(conn, target_date)
   - IC 計算: calc_ic(factor_records, forward_records, factor_col, return_col)
   - ファクター計算: calc_momentum / calc_volatility / calc_value（research.factor_research）

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル配置（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理（.env 自動読み込み等）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - news_collector.py        — RSS 取得・前処理・DB 保存
    - schema.py                — DuckDB スキーマ定義・init_schema
    - stats.py                 — zscore_normalize 等の統計ユーティリティ
    - calendar_management.py   — 市場カレンダー管理・ジョブ
    - audit.py                 — 監査ログテーブル定義
    - features.py              — data.stats の再エクスポート
    - pipeline.py              — ETL のエントリポイント（重複記載を除く）
  - research/
    - __init__.py
    - factor_research.py       — Momentum/Value/Volatility の計算
    - feature_exploration.py   — 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py   — build_features（正規化＋ユニバースフィルタ）
    - signal_generator.py      — generate_signals（final_score 計算、BUY/SELL 判定）
  - execution/                  — 実行・発注関連（エンドポイント等）
  - monitoring/                 — 監視・アラート関連

（実際のリポジトリでは README やドキュメントファイル、pyproject.toml / requirements.txt 等も含まれているはずです。）

---

## 注意事項 / 運用上のポイント

- 機密情報（API トークン等）は .env に保存せず、Secrets Manager やランタイム環境変数で管理することを推奨します。
- DuckDB ファイルはバックアップや適切な権限設定を行ってください。
- J-Quants の API レート制限（120 req/min）に従う実装になっています（jquants_client の RateLimiter）。
- 本ライブラリは「発注 API との通信」や「実際の資金運用」をラップするための土台を提供します。実運用での発注ルール、リスク管理、監査手順は別途厳密に設計・検証してください。
- テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して .env の自動読み込みを無効化すると便利です。

---

## 追加情報 / 拡張

- strategy や research のパラメータ（閾値・重み・フィルタ等）は設定ファイルや外部管理に移すと運用が楽になります。
- AI スコア統合（ai_scores）はプラグイン可能なスコア生成器を想定しており、外部モデルの出力を ai_scores テーブルに書き込めば統合されます。
- NewsCollector は URL 正規化・SSRF 対策・受信サイズ制限を備えています。RSS ソース追加や言語解析は拡張可能です。

---

必要であれば、README に含める具体的なコマンド例（systemd / cron ジョブ化、Dockerfile、CI/CD 設定 など）や、より詳細な API 参照（関数ごとの引数説明・戻り値サンプル）を追記します。どの情報を深掘りしますか？