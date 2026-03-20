# KabuSys

日本株向け自動売買基盤ライブラリ KabuSys の README。  
本リポジトリはデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログといった自動売買の主要機能をモジュール化して提供します。

## プロジェクト概要

KabuSys は日本株（JPX）向けの研究・本番パイプラインを念頭に設計されたライブラリです。主な目的は以下です。

- J-Quants API からのデータ取得（OHLCV・財務・カレンダー）と DuckDB への冪等保存
- データ品質チェック・差分 ETL の自動化
- 研究向けファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量正規化・合成（features テーブル作成）
- シグナル生成（final_score 計算・BUY/SELL 判定）
- RSS ベースのニュース収集・記事と銘柄の紐付け
- 市場カレンダー管理（営業日判定等）
- 発注／監査層のスキーマ（注文・約定・監査ログ等）

設計上の特徴：
- DuckDB を利用した軽量かつ高速なローカルデータベース
- 冪等（idempotent）な保存処理（ON CONFLICT / upsert）
- ルックアヘッドバイアスを避けるため、target_date 時点のデータのみ使用
- 外部依存を最小化しつつ、セキュリティ（SSRF 対策、XML 安全パーサ）や耐障害性（リトライ/バックオフ）にも配慮

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env / 環境変数の自動読み込み、設定オブジェクト（settings）
- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション・トークンリフレッシュ・レートリミット）
  - schema: DuckDB スキーマ定義 / init_schema
  - pipeline: ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・DB 保存（SSRF 対策、gzip 上限）
  - calendar_management: 営業日判定、next/prev/get_trading_days、calendar_update_job
  - stats: zscore_normalize（クロスセクション Z スコア正規化）
  - features: zscore_normalize の公開インターフェース
  - audit: 監査ログ用テーブル定義
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - feature_engineering.build_features: raw factor を正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して signals を生成
- kabusys.execution / monitoring
  - 発注や監視に関する層（スケルトン／実装ポイント）

---

## セットアップ手順

※ 以下は一般的なセットアップ手順の例です。プロジェクトで使用する Python バージョンや依存パッケージは適宜調整してください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール  
   主要な依存（明示されているものの例）:
   - duckdb
   - defusedxml
   - （必要に応じて）requests 等

   例:
   ```
   pip install duckdb defusedxml
   ```

   プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数の設定  
   プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   必須環境変数（config.Settings を参照）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意/デフォルトあり:
   - KABUSYS_ENV (development | paper_trading | live) - デフォルト: development
   - KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で無効化)
   - KABUSYS_API_BASE_URL などは config により既定値あり
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な例）

以下はライブラリの代表的な使い方例です。各関数はドキュメント文字列にも解説があります。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL を走らせる（J-Quants トークンは settings から自動取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を省略すると今日
   print(result.to_dict())
   ```

3. 特徴量構築（features テーブルの作成）
   ```python
   from kabusys.strategy import build_features
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2025, 1, 31))
   print(f"features updated: {n}")
   ```

4. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import init_schema
   from datetime import date

   conn = init_schema("data/kabusys.duckdb")
   count = generate_signals(conn, target_date=date(2025, 1, 31))
   print(f"signals generated: {count}")
   ```

5. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   # known_codes: 抽出に利用する有効銘柄コードの集合（例: prices テーブルから取得）
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
   print(results)
   ```

6. カレンダー更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py           — RSS 取得・前処理・DB 保存
  - schema.py                   — DuckDB スキーマ定義・init_schema
  - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
  - stats.py                    — zscore_normalize 等統計ユーティリティ
  - features.py                 — features インターフェース再エクスポート
  - calendar_management.py      — カレンダー管理・営業日判定
  - audit.py                    — 監査ログ用スキーマ
- research/
  - __init__.py
  - factor_research.py          — calc_momentum / calc_volatility / calc_value
  - feature_exploration.py      — calc_forward_returns / calc_ic / factor_summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py      — build_features
  - signal_generator.py         — generate_signals
- execution/                     — 発注層（スケルトン）
- monitoring/                    — 監視・通知用（スケルトン）

主要公開名（パッケージ __all__ 例）:
- kabusys.research: calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy: build_features, generate_signals

---

## 知っておくべき実装上のポイント

- 環境変数自動ロード:
  - プロジェクトルート（.git か pyproject.toml のある親ディレクトリ）に `.env` / `.env.local` がある場合、自動で読み込みます。
  - テストや特殊用途で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants クライアント:
  - レート制限（120 req/min）を尊重する固定間隔スロットリングを実装。
  - 401 を受け取るとリフレッシュトークンで id_token を自動更新して再試行。
  - 再試行（指数バックオフ）およびページネーション対応。
- News Collector:
  - RSS の XML は defusedxml で安全にパース。SSRF 対策・レスポンスサイズ上限を実装。
  - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
- ETL:
  - 差分取得（最終取得日から backfill を含めて再取得）を行い、API 側の後出し修正に対応。
  - 品質チェックは別モジュール（quality）にまとめられており、ETL 実行後に実行可能。
- Strategy:
  - build_features と generate_signals は target_date 固定で過去データへのルックアヘッドを排除するように設計。
  - generate_signals は欠損コンポーネントを中立（0.5）で補完し、不当な降格を避ける実装。

---

## ライセンス・貢献

この README ではライセンス情報ファイルやコントリビュートガイドは含まれていません。リポジトリルートに LICENSE / CONTRIBUTING.md 等を置いてください。

---

README はここまでです。追加で以下が必要でしたら教えてください：
- requirements.txt や pyproject.toml のサンプル
- CI / デプロイ手順（systemd / cron / Airflow 等）
- .env.example の詳細テンプレート
- quality モジュールや execution 層の詳細ドキュメント化