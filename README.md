# KabuSys

日本株自動売買システム（KabuSys）用ライブラリ / フレームワーク

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム向けに設計された Python モジュール群です。  
主に以下の機能を提供します。

- J-Quants API からの市場データ・財務データ取得と DuckDB への永続化（ETL）
- RSS ベースのニュース収集と記事 → 銘柄紐付け
- 研究（research）用のファクター計算・解析ユーティリティ
- 戦略層（strategy）での特徴量構築（feature engineering）および売買シグナル生成
- DB スキーマの定義・初期化、マーケットカレンダー管理、監査ログ設計
- 発注・実行（execution）層のためのテーブル群（監査／トレーサビリティ設計）

設計の特徴として、DuckDB を中心としたデータレイヤー、ルックアヘッドバイアス対策、冪等性（ON CONFLICT）・リトライ・レート制御・セキュリティ（SSRF対策等）に配慮しています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（レートリミット、リトライ、トークン自動リフレッシュ）
  - raw / processed / feature / execution 層の DuckDB スキーマ（init_schema）
  - 日次 ETL（差分取得・バックフィル・品質チェック）
  - JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
- ニュース収集
  - RSS フィード取得、コンテンツ整形、記事 ID 正規化（SHA-256）、raw_news 保存
  - 記事中の 4 桁銘柄コード抽出と news_symbols への紐付け
  - SSRF・XML攻撃・レスポンスサイズ等の防御処理
- 研究 / 戦略
  - ファクター計算（Momentum / Volatility / Value 等）
  - cross-section Z スコア正規化ユーティリティ
  - 特徴量構築（ユニバースフィルタ、Z スコアクリップ、features テーブルへの UPSERT）
  - シグナル生成（コンポーネントスコア、重み付け合算、Bear レジーム抑制、BUY/SELL の入出力を signals テーブルへ）
- 監査 / 発注
  - signal_events / order_requests / executions 等の監査テーブル設計（トレーサビリティ）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに | を利用）
- system に duckdb をインストールできること

1. リポジトリをクローンしてインストール（開発モード）
   - pip を使う例:
     - pip install -e .

2. 依存パッケージ（例）
   - duckdb
   - defusedxml
   - （標準ライブラリのみで動く箇所も多いですが、上記は必須または推奨です）
   - 例: pip install duckdb defusedxml

3. 環境変数（.env）を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます
     (自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能)。
   - 最低限設定が必要な変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot Token（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
   - 任意 / デフォルト付き:
     - KABUSYS_ENV — development / paper_trading / live （デフォルト development）
     - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト INFO）
     - KABU_API_BASE_URL — kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

   例（.env の最小テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # :memory: も可
     ```
   - 上記で必要なテーブル・インデックスが全て作成されます（冪等）。

---

## 使い方（代表的な API）

以下は主要ワークフローのサンプルです。適宜ロギングや例外処理を追加してください。

1. 設定（Settings）の参照
   ```python
   from kabusys.config import settings
   print(settings.duckdb_path)
   print(settings.is_dev)
   ```

2. DB 初期化（1回）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema(settings.duckdb_path)
   ```

3. 日次 ETL を実行（J-Quants から差分取得して保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

4. 特徴量構築（features テーブルへの書き込み）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   count = build_features(conn, date(2024, 1, 5))
   print(f"features upserted: {count}")
   ```

5. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   gen_count = generate_signals(conn, date(2024, 1, 5), threshold=0.6)
   print(f"signals generated: {gen_count}")
   ```

6. ニュース収集（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   # known_codes は銘柄抽出に使う有効な銘柄コード集合（例: {"7203","6758",...}）
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set())
   print(res)
   ```

7. J-Quants API 直接利用（テストや手動取得）
   ```python
   from kabusys.data import jquants_client as jq
   # get_id_token() は settings.jquants_refresh_token を利用して自動で取得します
   rows = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,5))
   saved = jq.save_daily_quotes(conn, rows)
   ```

8. カレンダー更新ジョブ（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   calendar_update_job(conn)
   ```

---

## 注意事項 / 設計上のポイント

- 環境変数は .env/.env.local を自動ロードしますが、CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用して無効化できます。
- DuckDB 上の INSERT は冪等（ON CONFLICT）を利用しているため、再実行での重複登録を防ぎます。
- J-Quants クライアントは API レート制限（120 req/min）を想定した RateLimiter と、特定ステータスでのリトライ・トークン自動再取得を備えています。
- RSS ニュース収集は SSRF 対策（リダイレクトチェック、プライベートIP検査）、XML の安全パース（defusedxml）や最大レスポンスサイズチェックを行っています。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかで、システム挙動（例: 発注抑制）に利用されます。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理（.env 自動読み込み、必須キーチェック）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 / 保存ユーティリティ）
  - news_collector.py — RSS 取得・保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義と init_schema
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — マーケットカレンダー管理
  - features.py — data.stats の再エクスポート
  - audit.py — 監査ログテーブル定義
- research/
  - __init__.py
  - factor_research.py — モメンタム/ボラティリティ/バリュー等の算出
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — features テーブル構築
  - signal_generator.py — final_score 計算と signals 生成
- execution/ — 発注/実行関連（モジュールプレースホルダ）
- monitoring/ — 監視系（DB監視等：ディレクトリあり）
- その他：utils や補助モジュール（コードベースに応じて追加）

（上記はプロジェクト内の主要モジュールを抜粋しています）

---

## 貢献・開発

- 新機能・バグ修正は Pull Request をお願いします。
- 環境変数・キー名を変更する場合は config.py を更新し README も合わせて修正してください。
- テスト & CI を追加することで安全性を高められます（特に ETL・ネットワーク周り）。

---

もし README に載せてほしい追加情報（例: CI 実行方法、具体的な .env.example、スケジューラ設定例、運用手順など）があれば教えてください。必要に応じてサンプル .env.example や systemd / cron ジョブの例も作成します。