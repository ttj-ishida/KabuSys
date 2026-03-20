# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
DuckDB をデータ層に用い、J-Quants API や RSS ニュースを取り込み、研究（factor/research）→ 特徴量生成 → シグナル生成 → 発注監査に至る一連の処理をサポートします。

---

## 主な特徴

- データ取得（J-Quants）／差分 ETL（株価・財務・市場カレンダー）
  - レートリミット・リトライ・ID トークン自動リフレッシュ対応
- DuckDB ベースのスキーマ定義と冪等保存（ON CONFLICT/UPsert）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー）
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ）
- シグナル生成（ファクター＋AIスコアの統合、Buy/Sell 判定、エグジットロジック）
- RSS → raw_news の収集・正規化・銘柄抽出（SSRF 対策、サイズ制限、トラッキング除去）
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）
- 監査ログ（signal_events / order_requests / executions 等）を想定したスキーマ設計

---

## 必要条件（推奨）

- Python 3.10+
- 依存パッケージ（例）
  - duckdb
  - defusedxml
- （実行環境により）J-Quants API アクセス用のネットワーク接続と有効なリフレッシュトークン

---

## セットアップ

1. リポジトリをクローン（またはプロジェクトルートへ移動）:

   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（推奨）:

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール:

   pip install duckdb defusedxml
   # 開発中にパッケージとして編集を反映したい場合:
   pip install -e .

4. 環境変数 / .env を設定（後述）

---

## 環境変数（主なキー）

config.py により .env / .env.local を自動読み込みします（プロジェクトルートに .git または pyproject.toml がある場合）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（実行する機能により必要なものが変わります）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 層を使用する場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知を使う場合）
- SLACK_CHANNEL_ID: Slack 通知の投稿先チャンネル ID

オプション / デフォルト:

- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 初期化（DB スキーマ）

DuckDB に必要なテーブルを作成するには `init_schema` を使います。

例:

```python
from kabusys.data.schema import init_schema

# ローカルファイルに初期化
conn = init_schema("data/kabusys.duckdb")

# メモリ DB（テスト用）
# conn = init_schema(":memory:")
```

`init_schema` は親ディレクトリを自動作成し、すべてのDDLを冪等的に実行します。

---

## デイリー ETL 実行（株価・財務・カレンダー）

日次ETL を一括で実行するユーティリティ:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ETL は以下を順に実行します:
  1. 市場カレンダー更新
  2. 株価（差分取得 + backfill）
  3. 財務データ（差分取得 + backfill）
  4. 品質チェック（デフォルトで有効）
- J-Quants のレートリミット / リトライ処理、IDトークン自動リフレッシュに対応しています。

必要に応じて `id_token` を外部から注入してテスト可能です（jquants_client.get_id_token）。

---

## 特徴量生成（Feature Engineering）

DuckDB に保存された生ファクターを正規化・合成して `features` テーブルへ書き込みます。

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, date.today())
print(f"features upserted: {n}")
```

処理のポイント:

- research 層の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得
- ユニバースフィルタ（最低株価・平均売買代金）を適用
- 指定カラムを Z スコア正規化、±3 でクリップ
- 日付単位の置換（トランザクションで DELETE→INSERT）で冪等性を保証

---

## シグナル生成

`features` と `ai_scores` を統合して最終スコアを算出し `signals` テーブルへ書き込みます。

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, date.today())
print(f"signals generated: {count}")
```

- デフォルト閾値: final_score >= 0.60 で BUY（weights はデフォルト値で合計を 1 に正規化）
- Bear レジーム（AI の regime_score 平均 < 0）では BUY を抑制
- エグジット判定（STOP LOSS、スコア低下など）を行い SELL シグナルを生成
- BUY/SELL の書き込みは日付単位の置換で冪等

weights をオーバーライドすることも可能（無効値や未知キーは無視され、合計は自動スケールされます）。

---

## ニュース収集（RSS）

RSS フィードを取得して raw_news / news_symbols へ保存します。SSRF/サイズ/トラッキング除去を考慮した実装です。

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

主な注意点:

- URL スキームは http/https のみ許可
- レスポンスサイズは上限（10MB）で保護
- 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等性を確保
- 銘柄抽出は 4 桁数字（known_codes によるフィルタ）を採用

---

## カレンダー管理ジョブ

JPX の市場カレンダーを差分更新する夜間バッチ:

```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- 既存データの最終日から差分取得、直近バックフィルを行う設計
- market_calendar が空の場合は曜日フォールバック（土日は休場）を利用

---

## 主要モジュール（要約）

- kabusys.config
  - 環境変数読み込み・検証、Settings オブジェクト
- kabusys.data
  - jquants_client.py: J-Quants API クライアント（取得 + 保存ユーティリティ）
  - schema.py: DuckDB スキーマ初期化 / get_connection
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - news_collector.py: RSS 取得・保存・銘柄抽出
  - calendar_management.py: 営業日判定 / calendar_update_job
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - features.py: zscore_normalize の公開ラッパ
- kabusys.research
  - factor_research.py: calc_momentum / calc_volatility / calc_value
  - feature_exploration.py: calc_forward_returns / calc_ic / factor_summary
- kabusys.strategy
  - feature_engineering.py: build_features
  - signal_generator.py: generate_signals
- kabusys.execution / monitoring
  - （骨組み・プレースホルダ／実装の拡張点）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - stats.py
  - calendar_management.py
  - features.py
  - audit.py
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
- monitoring/
  - (監視関連モジュール)

（README のファイル一覧は開発中のため一部省略されることがあります）

---

## 使い方のベストプラクティス

- 本番/ペーパートレード/開発は `KABUSYS_ENV` で切り替え（is_live/is_paper/is_dev の判定が可能）
- 機密情報は .env.local などで管理し、`.gitignore` に追加する
- ETL は cron / Airflow / 任意バッチで日次実行。Calendar を先に取得して trading_day を調整すると安定
- DuckDB ファイルは定期的にバックアップして監査ログや約定データを保全
- ニュース収集や外部アクセス部分はネットワークに対する例外処理を必ず監視ログに残す

---

## 貢献・ライセンス

- 本リポジトリへの貢献は Pull Request を歓迎します。Issue で議論してから実装を進めてください。
- ライセンス情報はリポジトリの LICENSE ファイルに従ってください。（この README にライセンスは含めていません）

---

不明点や README に追記してほしい使い方（例: 実際の運用スクリプト、CI 設定、より詳細な .env.example）などがあれば教えてください。