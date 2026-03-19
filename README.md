# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（リサーチ / データ基盤 / 戦略 / 発注監査用モジュール群）。

このリポジトリは主に以下を提供します：
- J-Quants API からのデータ取得・保存（株価・財務・市場カレンダー）
- DuckDB ベースのデータスキーマと初期化ユーティリティ
- ETL パイプライン（差分取得、保存、品質チェック）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量作成（正規化・ユニバースフィルタ）とシグナル生成（BUY/SELL）
- ニュース収集・記事保存・銘柄抽出（RSS）
- 発注〜約定〜ポジションまでの監査用スキーマ（トレーサビリティ確保）

---

## 主な機能一覧

- data/jquants_client：J-Quants API クライアント（リトライ、レート制御、トークン自動更新、ページネーション対応）
- data/schema：DuckDB のスキーマ定義と init_schema() による初期化
- data/pipeline：日次 ETL 実行（run_daily_etl）／個別 ETL ジョブ（prices/financials/calendar）
- data/news_collector：RSS 取得→前処理→raw_news への冪等保存、銘柄抽出
- data/calendar_management：営業日判定・next/prev_trading_day 等のユーティリティ
- research/factor_research：モメンタム・ボラティリティ・バリュー等のファクター計算
- research/feature_exploration：将来リターン計算、IC（スピアマン）計算、統計サマリー
- strategy/feature_engineering：生ファクターを正規化・フィルタして features テーブルへ永続化
- strategy/signal_generator：features と ai_scores を統合して final_score を算出し signals テーブルへ書き込み
- data/stats：Zスコア正規化ユーティリティ
- audit（監査スキーマ）：signal_events / order_requests / executions など監査用テーブル群

---

## 要件

- Python 3.10 以上（PEP 604 の型記法（`X | None`）などを使用）
- 必須パッケージ（最小）:
  - duckdb
  - defusedxml
- 標準ライブラリで多く実装されているが、プロダクション用途では追加パッケージ（ログ集約、Slack 通知等）を導入することが想定されます。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（実際の要件はプロジェクトの requirements.txt に合わせてください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化する
2. 必要パッケージをインストール（上記参照）
3. 環境変数を準備する（.env ファイルをプロジェクトルートに置くと自動でロードされます。自動ロードを無効にするには env var `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）
4. DuckDB スキーマを初期化する

例：.env（最低限必要なキー）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

DuckDB スキーマ初期化（Python 実行例）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn を以降の処理で再利用
```

---

## 使い方（よく使う操作の例）

- DuckDB スキーマ作成
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（市場カレンダー・株価・財務データの差分取得／保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ファクター計算と特徴量の構築（features テーブルへ保存）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, date(2025, 1, 31))
print(f"upserted features: {n}")
```

- シグナル生成（signals テーブルへ保存）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, date(2025, 1, 31), threshold=0.60)
print(f"signals written: {count}")
```

- ニュース収集ジョブ（RSS から収集して raw_news に保存、既知銘柄で紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- J-Quants のデータ取得（クライアント関数を直接利用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token, save_daily_quotes
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
token = get_id_token()  # settings からリフレッシュトークンを使って取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,12,31))
saved = save_daily_quotes(conn, records)
```

---

## 環境変数（主な設定項目）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン（通知等で使用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化（テスト用）

設定はプロジェクトルートの `.env` / `.env.local` → OS 環境変数 の順で読み込まれます（自動ロードをオフにすることも可能）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（version など）
- config.py — 環境変数・設定管理（Settings クラス）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント + 保存ユーティリティ
  - news_collector.py — RSS 取得 / 前処理 / raw_news 保存 / 銘柄抽出
  - schema.py — DuckDB スキーマ定義 / init_schema / get_connection
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - calendar_management.py — 営業日ユーティリティ & calendar_update_job
  - features.py — data.stats の公開インターフェース
  - audit.py — 発注〜約定の監査ログスキーマ
- research/
  - __init__.py
  - factor_research.py — 各種ファクター計算（mom/vol/value）
  - feature_exploration.py — 将来リターン, IC, 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — 生ファクターの正規化・ユニバースフィルタ→features へ保存
  - signal_generator.py — final_score 計算、BUY/SELL シグナル生成→signals へ保存
- execution/ — 発注／実行レイヤ（雛形／将来拡張）
- monitoring/ — 監視・メトリクス用（設計想定）

（README では主要なモジュール・用途を抜粋して記載しています）

---

## 運用上の注意 / ヒント

- DuckDB のファイルパスは Settings.duckdb_path（デフォルト data/kabusys.duckdb）。複数プロセスで同一ファイルを使う場合はロックや接続設計に注意してください。
- J-Quants API のレート制限（120 req/min）は jquants_client によって守られる設計です。大量取得やバックフィル時は API 制限を確認してください。
- ETL は差分更新（最終取得日ベース）かつ backfill（デフォルト 3 日）を行い、API の後出し修正を吸収するよう設計されています。
- news_collector は外部 RSS を解析するため、SSRF/XML Bomb/大容量対策を組み込んでいますが、運用環境では信頼できる RSS ソースを使ってください。
- production（live）環境では KABUSYS_ENV を `live` に設定し、発注・実行周りの挙動は厳密にテストしてください（ペーパートレードでの十分な検証を推奨）。

---

必要であれば README に「開発フロー」「テスト方法」「CI 設定」「デプロイ手順」なども追記します。どの情報を優先して追加しますか？