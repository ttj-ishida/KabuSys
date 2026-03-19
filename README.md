# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（部分実装）。  
データ取得、ETL、特徴量エンジニアリング、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ用のスキーマなどを提供します。

> 注: このリポジトリはライブラリ/モジュール群の抜粋実装を含みます。実運用には追加のラッパー、ジョブスケジューラ、発注ブリッジ等が別途必要です。

## 主な特徴
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- DuckDB を使った冪等なスキーマ定義・初期化（init_schema）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェックフック）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ）
- 特徴量正規化（Zスコア）および features テーブルへの保存処理
- シグナル生成（重み付け合成／Bear レジーム抑制／エグジット判定）
- RSS ベースのニュース収集と銘柄抽出（SSRF対策・XML安全パース・トラッキング除去）
- マーケットカレンダー管理（JPX カレンダー取得・営業日判定）
- 監査ログ用テーブル群（signal → order → execution のトレース）

## 要件
- Python 3.10 以上（型ヒントの union 演算子 `|` を使用）
- 主要依存:
  - duckdb
  - defusedxml
- ネットワークアクセス: J-Quants API、RSS フィードへの HTTP(s)

必要パッケージはプロジェクトに requirements ファイルがある場合はそちらを参照してください。簡易インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクトがパッケージ化されている場合
pip install -e .
```

## 環境変数（必須 / 任意）
設定は OS 環境変数、`.env`、`.env.local` から読み込まれます（優先度: OS > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注部分を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を利用する場合に必要
- SLACK_CHANNEL_ID — Slack チャネルID

任意（デフォルト値あり）:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: `development`）
- LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: `INFO`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（任意）
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: `data/monitoring.db`）
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: `http://localhost:18080/kabusapi`）

.env の書き方は一般的な KEY=VALUE 形式とクォート付きをサポートします。`.env.local` は `.env` を上書きします（OS 環境変数は常に優先）。

## セットアップ手順（簡易）
1. リポジトリをクローンして仮想環境を作成・有効化
2. 依存パッケージをインストール（duckdb, defusedxml 等）
3. 環境変数を設定（`.env` / `.env.local` を作成）
4. DuckDB スキーマを初期化

例:
```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml

# .env を作成（例）
cat > .env <<EOF
JQUANTS_REFRESH_TOKEN=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
KABU_API_PASSWORD=secret
EOF

# Python で初期化
python - <<'PY'
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings
conn = init_schema(settings.duckdb_path)
print("DuckDB initialized:", settings.duckdb_path)
conn.close()
PY
```

## 使い方（主要ワークフロー例）

### 1) スキーマ初期化
Python REPL またはスクリプトで:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成・テーブル生成
```

### 2) 日次 ETL（市場カレンダー・株価・財務の差分取得）
run_daily_etl を用いると、カレンダー → 株価 → 財務 → 品質チェックを順に実行します。
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

引数で `id_token` を注入可能（テスト用）や `backfill_days` の変更も可能です。

### 3) 特徴量構築（features テーブル）
research レイヤーのファクターを使って features を作成します:
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print("features upserted:", n)
```

### 4) シグナル生成（signals テーブル）
features と ai_scores（あれば）を組み合わせてシグナルを生成:
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.60)
print("signals written:", count)
```

重みをカスタムで渡すことも可能です（無効なキーや負値は無視し、合計で再スケールします）。

### 5) ニュース収集ジョブ（RSS）
RSS ソースから記事を取得し `raw_news` に保存、必要に応じて `news_symbols` に紐付けします:
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count, ...}
```

既定の RSS ソースは `DEFAULT_RSS_SOURCES` に定義されています。URL のスキーム検査、SSRF 対策、コンテンツサイズ制限など安全対策を備えています。

### 6) カレンダー更新ジョブ（夜間バッチ）
JPX カレンダーを差分取得して `market_calendar` を更新:
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print("calendar entries saved:", saved)
```

## 主要モジュール（ディレクトリ構成）
以下は src/kabusys 以下の主要ファイルと役割の概観です。

- kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — 環境変数 / 設定の読み込みと検証（.env 自動ロード、settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save関数群、レート制御、リトライ）
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py — ETL パイプライン（run_daily_etl、個別 ETL 関数）
    - news_collector.py — RSS 取得・前処理・DB 保存（raw_news、news_symbols）
    - calendar_management.py — カレンダー更新・営業日判定ユーティリティ
    - audit.py — 発注〜実行の監査ログ用テーブル定義
    - features.py — features の公開インターフェース（zscore の再エクスポート）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL 実装（上記）
  - research/
    - __init__.py — 研究用API再公開
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py — build_features / generate_signals の公開
    - feature_engineering.py — ファクターの正規化・ユニバースフィルタ・features への UPSERT
    - signal_generator.py — final_score 計算・BUY/SELL 生成・signals への保存
  - execution/ — （発注レイヤー用の空パッケージ、実装追加想定）
  - monitoring/ — （監視・メトリクス関連の想定フォルダ）

（実際のファイルはリポジトリ参照ください）

## 実装上の設計方針（抜粋）
- ルックアヘッドバイアス防止: 特徴量・シグナル生成は target_date 時点で入手可能なデータのみ使用
- 冪等性: DB への挿入は ON CONFLICT / UPSERT を用い、トランザクションで日付単位の置換を実現
- セキュリティ: RSS の XML パースは defusedxml を利用、SSRF 判定、レスポンスサイズ上限を実装
- フォールバック: market_calendar が未取得の環境でも曜日ベースで営業日判定が可能

## よくある操作例・ヒント
- テストや CI では環境変数による自動 .env 読み込みを無効化する:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- DuckDB をインメモリで使う場合:
  ```python
  conn = init_schema(":memory:")
  ```
- `generate_signals` の重みをカスタマイズする際は辞書で指定。無効な値はスキップされ、合計は 1.0 に再スケールされます。

## 貢献
バグ修正・機能追加は歓迎します。Pull Request を作成する前に issue を立てて概要をご連絡ください。

---

この README はコードベースの要点をまとめた参照資料です。実際に運用する際はログ設定、エラーハンドリング、セキュリティ（API トークンの保護）、監視・アラートの整備を行ってください。