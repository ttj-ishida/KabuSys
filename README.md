# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。J-Quants API や RSS 等からデータを収集して DuckDB に蓄積し、ファクター計算・特徴量作成・シグナル生成・監査トレースまでを一貫して扱うことを目的としています。

主な設計方針:
- ルックアヘッドバイアス回避（target_date 時点のデータのみを使用）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全に）
- 最小限の外部依存（主要処理は標準ライブラリ + duckdb）
- テスト容易性（トークン注入や URL オープンのモックを想定）

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS ベースのニュース収集（Article 正規化、銘柄抽出、SSRF/サイズ保護）
  - DuckDB への冪等保存ユーティリティ（raw / processed / feature / execution 層）
- ETL パイプライン
  - 日次差分 ETL（価格・財務・カレンダー）、バックフィルオプション、品質チェック連携
  - カレンダー夜間更新ジョブ
- ファクター計算 / 研究ツール（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング（strategy）
  - 生ファクターの正規化・合成（Zスコア正規化、ユニバースフィルタ、クリップ）
- シグナル生成（strategy）
  - 正規化済み特徴量 + AI スコアの統合 → final_score 計算
  - Bear レジーム判定、BUY / SELL シグナルの生成（閾値・重みつけ対応）
  - エグジット（ストップロス・スコア低下）判定
- スキーマ＆監査
  - DuckDB 用スキーマ初期化ユーティリティ（raw / processed / feature / execution 層）
  - 監査テーブル（signal_events / order_requests / executions）によるトレーサビリティ

---

## 要件

- Python >= 3.10（型注釈で PEP 604 の `X | Y` を使用）
- 主要依存:
  - duckdb
  - defusedxml
- その他: 標準ライブラリ（urllib, datetime, logging 等）

（環境に応じて追加ライブラリが必要になる場合があります。pip インストール時にエラーが出たら該当パッケージを追加してください。）

---

## インストール

開発レポジトリとして扱う想定の手順例:

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール
   - pip install duckdb defusedxml

4. （任意）パッケージ化してインストール
   - pip install -e .

---

## 環境変数 / 設定

config.Settings で以下の環境変数を参照します（必須と省略可能を分けて掲示）。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD     : kabu API（kabuステーション）のパスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先チャネル ID

省略可能（デフォルト値あり）:
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 環境 (development / paper_trading / live)、デフォルト development
- LOG_LEVEL             : ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)、デフォルト INFO

自動ロード:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）にある `.env` と `.env.local` を起動時に自動読み込みします。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（DB 初期化）

DuckDB スキーマを初期化します。Python スクリプトから呼べます。

例:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可

この関数は必要なテーブル・インデックスをすべて作成します（冪等）。

---

## 使い方（主要ユースケース）

以下は代表的な操作例の簡単な流れ。

1) 日次 ETL（J-Quants から市場カレンダー・日足・財務を取得して保存）
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) 特徴量の作成（research の生ファクターを正規化・保存）
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")

3) シグナル生成（features と ai_scores から BUY/SELL を作成）
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals created: {count}")

4) ニュース収集（RSS を DB に保存し、銘柄紐付け）
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)

注意点:
- 全ての主要 API は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る設計です。
- J-Quants 認証は config.Settings.jquants_refresh_token を用います。get_id_token() を直接呼んでトークンを取得できます。
- generate_signals/build_features/run_daily_etl は日付単位で冪等に動作するよう設計されています。

---

## 主要モジュール一覧（簡易説明）

- kabusys.config
  - 環境変数の読み込み / Settings（アプリ設定アクセス）
- kabusys.data
  - schema.py : DuckDB スキーマ定義 & init_schema/get_connection
  - jquants_client.py : J-Quants API クライアント + 保存ユーティリティ
  - pipeline.py : ETL パイプライン（run_daily_etl など）
  - news_collector.py : RSS 取得・正規化・DB 保存
  - calendar_management.py : 営業日判定 / カレンダー更新ジョブ
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - features.py : zscore_normalize の再エクスポート
  - audit.py : 監査ログ用スキーマ定義
- kabusys.research
  - factor_research.py : calc_momentum / calc_value / calc_volatility
  - feature_exploration.py : calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - feature_engineering.py : build_features（生ファクター -> features テーブル）
  - signal_generator.py : generate_signals（features/ai_scores -> signals）
- kabusys.execution (プレースホルダ)
  - 発注・ブローカー連携等（将来的に実装想定）
- kabusys.__init__.py
  - パッケージメタデータ（__version__）

プロジェクトツリー（抜粋）
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ schema.py
   │  ├─ pipeline.py
   │  ├─ calendar_management.py
   │  ├─ stats.py
   │  └─ ...
   ├─ research/
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   ├─ strategy/
   │  ├─ feature_engineering.py
   │  └─ signal_generator.py
   └─ execution/

---

## 運用上の注意 / ヒント

- KABUSYS_ENV は動作モードを切り替えます（development / paper_trading / live）。
  - settings.is_live / is_paper / is_dev で判定可能。
- 自動 .env のロードはプロジェクトルートの検出に依存します（.git または pyproject.toml）。
  - テスト時などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のレート制限（デフォルト 120 req/min）に合わせて内部でスロットリング・リトライが実装されています。
- DuckDB ファイルはデフォルト data/kabusys.duckdb に作成されます。バックアップ・アーカイブ戦略を検討してください。
- news_collector は SSRF / XML Bomb / 大容量レスポンス対策を実装していますが、外部 RSS の信頼度や取得頻度は運用で管理してください。

---

## 貢献 / 開発

- 新しい機能追加や修正は PR を歓迎します。
- テストは各モジュール（特にネットワーク／IO を行う部分）でモックしやすいように設計されています（例: _urlopen の差し替え、id_token の注入）。
- ドキュメント・仕様（StrategyModel.md / DataPlatform.md / DataSchema.md）を参照して実装を合わせてください（リポジトリ内に仕様書がある想定です）。

---

詳細な API や拡張例は各モジュールの docstring を参照してください。必要であれば README に追加したい具体的な操作例（cron 設定、監視・アラートの設定、Slack 通知連携の例など）を教えてください。