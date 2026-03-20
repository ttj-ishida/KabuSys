# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査（発注/約定）までの主要コンポーネントを含みます。学術的なファクター研究と運用実装の橋渡しを意図した設計です。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ使用）
- 冪等性（DB 保存は ON CONFLICT / トランザクション）
- 外部依存を限定（DuckDB を主な永続化層として使用）
- セキュリティ対策（RSS の SSRF 対策・XML パース保護等）

---

## 機能一覧

- データ取得
  - J-Quants API から日足（OHLCV）、財務データ、市場カレンダーを取得（ページネーション対応、トークン自動リフレッシュ、レート制限）
- データ永続化
  - DuckDB スキーマの定義・初期化（raw / processed / feature / execution 層）
  - raw_prices / raw_financials / market_calendar / raw_news 等の冪等保存
- ETL パイプライン
  - 差分取得（最終取得日からの差分）・バックフィル対応・品質チェックフレームワークと統合
- 研究（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 特徴量エンジニアリング
  - 生ファクターの Z スコア正規化、ユニバースフィルタ（最低株価・流動性）適用、features テーブルへの UPSERT
- シグナル生成
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成、エグジット（ストップロス等）判定
- ニュース収集
  - RSS から記事収集、テキスト前処理、raw_news 保存、銘柄コード抽出と紐付け（SSRF/サイズ/XML 保護あり）
- マーケットカレンダー管理
  - JPX カレンダー取得、営業日判定（DB 優先、未登録日は曜日フォールバック）
- 監査ログ（audit）
  - シグナル→発注→約定までのトレーサビリティ用テーブル定義

---

## 要件

- Python 3.10+
- 主要依存（例）
  - duckdb
  - defusedxml
- （ネットワーク経由機能を利用する場合）J-Quants API へのアクセスが必要

依存はプロジェクト側に pyproject.toml / requirements.txt があればそちらに従ってください。最小例：
pip install duckdb defusedxml

---

## 環境変数（設定項目）

KabuSys は環境変数（または .env / .env.local）から設定を読み込みます。自動ロードはプロジェクトルート（.git か pyproject.toml）を起点に行われ、優先順位は OS 環境変数 > .env.local > .env です。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数：
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | ...)

settings オブジェクトは kabusys.config.settings でアクセスできます。

---

## セットアップ手順

1. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存インストール
   pip install duckdb defusedxml

   （プロジェクトの依存ファイルがあればそれを使ってインストールしてください）

3. 環境変数設定
   プロジェクトルートに .env または .env.local を作成し、必要な鍵を設定します。例（.env.example を参考に）:
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb

4. DuckDB スキーマ初期化
   以下の Python 例を参照して DB を初期化してください（:memory: でも可）。

---

## 初期化と基本的な使い方（Python サンプル）

以下は最小の利用例です。適宜 logging を設定してください。

- スキーマ初期化（DuckDB ファイルを作成しテーブルを作る）

from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")
# 以降 conn を使って ETL / 特徴量 / シグナルを実行できる

- 日次 ETL 実行（J-Quants から差分取得して保存）

from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())

- 特徴量構築（features テーブルの作成）

from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2025, 1, 31))
print(f"upserted features: {count}")

- シグナル生成（features と ai_scores から signals に書き込む）

from kabusys.strategy import generate_signals
from datetime import date
num_signals = generate_signals(conn, date(2025, 1, 31))
print(f"signals written: {num_signals}")

- ニュース収集ジョブ（RSS を取り DB に保存、known_codes を与えると紐付けも実行）

from kabusys.data.news_collector import run_news_collection
rss_results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(rss_results)

- カレンダー更新ジョブ（夜間バッチ等で実行）

from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")

注意点：
- いずれの操作もトランザクション・冪等性を考慮して設計されていますが、本番利用前に小さな範囲で動作確認を行ってください。
- J-Quants API を使う関数は id_token を引数注入可能（テスト容易性）。

---

## よく使うモジュール API（要点）

- kabusys.config.settings
  - settings.jquants_refresh_token などプロジェクト設定参照

- kabusys.data.schema
  - init_schema(db_path) → DuckDB 接続（初期化）
  - get_connection(db_path) → 接続のみ

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...) → ETLResult

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)

- kabusys.data.news_collector
  - fetch_rss(url, source) / save_raw_news / run_news_collection

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
  - パッケージ定義と公開モジュールの列挙

- config.py
  - 環境変数読み込み・settings オブジェクト定義（.env 自動読み込みロジック含む）

- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
  - pipeline.py — ETL パイプライン（差分取得・バックフィル・品質チェック統合）
  - stats.py — Z スコア正規化など統計ユーティリティ
  - news_collector.py — RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management.py — market_calendar 管理・営業日判定・更新ジョブ
  - audit.py — 監査ログ（signal_events / order_requests / executions 等）
  - features.py — data.stats の公開再エクスポート

- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、ファクター統計サマリ

- strategy/
  - __init__.py
  - feature_engineering.py — 生ファクターの正規化・ユニバースフィルタ・features 保存
  - signal_generator.py — final_score 計算・BUY/SELL 生成・signals 保存

- execution/
  - 発注/約定/ポジション関連の実装用名前空間（現時点ではモジュール空）

上記ファイル群は、Raw → Processed → Feature → Execution の各レイヤーを意識した設計になっています。

---

## 運用上の注意 / ベストプラクティス

- 本ライブラリはトークン・API キーを必要とします。機密情報は .env.local や CI のシークレット機能を利用してください。
- 本番運用時は KABUSYS_ENV=live を設定し、ログレベル・通知設定を適切に行ってください。
- DuckDB ファイルは定期的にバックアップしてください。
- ニュース RSS 等、外部ソースの取得は失敗や応答サイズ超過に対応するよう実行スケジューラでリトライや監視を行ってください。
- 本パッケージは発注 (execution) 層と切り離して設計されています。実際のブローカー接続を行う場合は、監査 / 冪等キーの取り扱いに十分配慮してください。

---

## ライセンス・貢献

README にはライセンス情報や貢献手順が含まれていません。公開リポジトリに追加する場合は LICENSE を配置し、コントリビュート方法（Issue / PR の方針）を追記してください。

---

必要であれば、README に含める具体的な .env.example、docker-compose / systemd の起動例、CI ワークフロー例、より詳細な API リファレンスを追加できます。どの情報を優先して追加しますか？