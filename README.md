# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、スキーマ管理などを含むモジュール群を提供します。

> 注意: 本リポジトリはライブラリ実装の一部（設計文書への参照あり）を含みます。実際の運用では各種シークレットや取引API周りの統合・十分なテスト・リスク管理が必要です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（例）
- 環境変数 / 設定
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームと自動売買戦略パイプラインを想定した Python ライブラリです。  
主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への蓄積（冪等保存）
- ETL（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量の正規化・合成と features テーブルへの保存
- シグナル（BUY/SELL）の生成ロジック（複合スコア）
- RSS からのニュース収集と記事 → 銘柄紐付け
- DuckDB スキーマ定義と初期化

設計上の注意点として、ルックアヘッドバイアス防止、冪等性（ON CONFLICT）やトランザクション制御、API レート制限・リトライ等に配慮しています。

---

## 機能一覧（モジュール概要）

- kabusys.config
  - 環境変数読み込み（.env/.env.local、自動ロード）と Settings オブジェクト
- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン更新）
  - schema: DuckDB スキーマ定義と init_schema()
  - pipeline: ETL ジョブ（run_daily_etl 等）
  - news_collector: RSS 取得・前処理・DB 保存、銘柄抽出
  - calendar_management: JPX カレンダー管理 / 営業日判定
  - stats: Zスコア正規化などの統計ユーティリティ
  - features: zscore_normalize の再エクスポート
  - audit: 監査ログ用スキーマ（signal / order / execution の追跡）
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value（prices_daily/raw_financials を参照）
  - feature_exploration: 将来リターン calc_forward_returns、IC（calc_ic）、サマリー等
- kabusys.strategy
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, ...)
- kabusys.execution
  - （発注・ブローカ連携は別実装を想定。パッケージ用の名前空間あり）
- kabusys.monitoring
  - （監視・Slack通知等の実装を想定した名前空間）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子等を使用）
- Git（.env 自動ロードでプロジェクトルート検出を行うため推奨）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt がある場合はそれに従ってください）

4. パッケージをインストール（開発モード）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 環境変数（主なキー）

Settings クラスで利用される主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注層で使用）
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知用チャンネルID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視用、デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)。デフォルト development
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

.env の例（実際のシークレットは安全に管理してください）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下は代表的なワークフロー例です。DuckDB を初期化し、日次 ETL → 特徴量作成 → シグナル生成 を行う流れです。

1) DuckDB スキーマ初期化
```
python - <<'PY'
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
print("schema initialized")
PY
```

2) 日次 ETL（J-Quants からデータを取得して保存）
```
python - <<'PY'
from datetime import date
import duckdb
from kabusys.data.schema import get_connection
from kabusys.data.pipeline import run_daily_etl

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
PY
```

3) 特徴量の構築（features テーブルへ書き込み）
```
python - <<'PY'
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print("features upserted:", count)
PY
```

4) シグナル生成（signals テーブルへ書き込み）
```
python - <<'PY'
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals written:", total)
PY
```

5) ニュース収集ジョブ（RSS から raw_news / news_symbols へ保存）
```
python - <<'PY'
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄リスト（文字列の4桁コードセット）を渡すと抽出・紐付けを試みる
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
PY
```

注意点:
- 各 ETL 関数は冪等に設計されています（ON CONFLICT や日付単位の置換を行う）。
- 実際の発注や証券会社連携を行う execution 層は実装が必要です（このリポジトリ内には主要ロジックとデータ層が含まれます）。

---

## 主要 API（参照用）

- init_schema(db_path) — DuckDB スキーマを作成して接続を返す
- get_connection(db_path) — 既存 DB への接続を返す
- run_daily_etl(conn, target_date=...) — 日次 ETL（calendar, prices, financials, quality checks）
- build_features(conn, target_date) — features を計算し保存
- generate_signals(conn, target_date, threshold, weights) — signals を生成して保存
- run_news_collection(conn, sources, known_codes) — RSS からニュース収集・保存

設定値は kabusys.config.settings 経由で取得できます:
```
from kabusys.config import settings
print(settings.duckdb_path, settings.env)
```

---

## ディレクトリ構成（抜粋）

以下はパッケージ内の主要ファイルと階層です（src 配下）:

- src/kabusys/
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
    - (その他: quality.py など想定)
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
    - (監視/通知用モジュール想定)

---

## 開発時の補足・注意

- SQL の暫定的な制約や DuckDB バージョン依存（ON DELETE CASCADE のサポート等）に注意してください。README や DataSchema.md 等（リポジトリにある場合）を参照して下さい。
- J-Quants API のレート制限（120 req/min）やリトライロジックは jquants_client.py 内で実装済みですが、実運用時はさらに安定化（キュー、バックオフ方針）の検討が必要です。
- ニュース収集では SSRF 対策や XML パースの安全対策（defusedxml）を取り入れていますが、外部フィードの多様性に応じて例外処理を拡充してください。
- 実際の板寄せ・約定・ブローカ接続の実装は別途必要です。特に本番環境（live）での動作は入念なテストとリスク管理が必須です。

---

問題や実装上の疑問点があれば、用途（研究 / ペーパートレード / 本番）や具体的なワークフローを教えてください。README の補足やサンプルスクリプトを追加します。