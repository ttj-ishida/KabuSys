# KabuSys

日本株向けの自動売買・データプラットフォーム基盤ライブラリです。  
J-Quants API からのデータ取得、DuckDB を用いたデータスキーマ、特徴量生成・戦略シグナル生成、ニュース収集・紐付け、マーケットカレンダー管理、ETL パイプライン等の主要機能を提供します。

---

## 主な特徴（Feature list）

- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - トークン自動リフレッシュ、レート制限、再試行（指数バックオフ）を実装
- DuckDB ベースのデータスキーマ定義と初期化
  - Raw / Processed / Feature / Execution 層を想定したテーブル群を定義
  - 冪等性を考慮した保存（ON CONFLICT / DO UPDATE）を実装
- ETL パイプライン
  - 差分取得（最終取得日を元に差分）＋バックフィル
  - 品質チェック（スパイク、欠損など）とエラーハンドリング
  - 日次 ETL エントリポイント（run_daily_etl）
- 研究（research）ツール
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- 戦略（strategy）
  - 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
  - シグナル生成（複数コンポーネントスコアの重みづけ、BUY/SELL 生成、エグジット判定）
- ニュース収集
  - RSS フィードの安全な取得（SSRF 対策、受信サイズ制限、XML 攻撃対策）
  - 記事の正規化、ID 生成（URL 正規化 + SHA256）、raw_news 保存、銘柄コード抽出と紐付け
- マーケットカレンダー管理
  - JPX カレンダー取得・管理、営業日判定、next/prev_trading_day 等のユーティリティ
- 監査（audit）スキーマ（発注・約定のトレーサビリティ）設計

---

## 要件（Requirements）

- Python 3.10 以上（型ヒントに `|` を使っています）
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml
- OS 環境（Linux / macOS / Windows）上で動作します（ただし DB パス等のパス変換は環境による）

※ 実際の requirements はプロジェクトの packaging/setup に依存します。上記はコードから推定される最小限の依存です。

---

## セットアップ手順（Setup）

1. Python 仮想環境を作成（任意）
   - python -m venv venv
   - source venv/bin/activate  （Windows: venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （開発時）pip install -e . などでパッケージをインストールできるようにする

3. 環境変数の設定
   - .env ファイルをプロジェクトルートに置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu API パスワード（発注連携を行う場合）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（通知機能を使う場合）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV — 環境: `development` / `paper_trading` / `live`（デフォルト `development`）
     - LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト `INFO`）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
     - SQLITE_PATH — SQLite 監視 DB（デフォルト: `data/monitoring.db`）

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 初期化（DB スキーマ作成）

DuckDB のスキーマを初期化するには `kabusys.data.schema.init_schema` を呼び出します。例:

```python
from pathlib import Path
from kabusys.data.schema import init_schema

db_path = Path("data/kabusys.duckdb")
conn = init_schema(db_path)
# conn は duckdb.DuckDBPyConnection オブジェクト
```

- `db_path` に指定したパスの親ディレクトリが存在しない場合は自動で作成されます。
- ":memory:" を指定するとインメモリ DB を使用できます（テスト用途など）。

---

## 使い方（Usage examples）

以下は代表的な処理のサンプルコード例です。

1) 日次 ETL（データ取得・保存・品質チェック）

```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量（features）構築（strategy の feature_engineering）

```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 10))
print(f"features upserted: {count}")
```

3) シグナル生成

```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
n_signals = generate_signals(conn, target_date=date(2024, 1, 10))
print(f"signals generated: {n_signals}")
```

- `generate_signals` は features / ai_scores / positions を参照して BUY/SELL を作成し、signals テーブルへ日付単位で置換（冪等）します。
- 重みや閾値を引数で上書き可能です（weights, threshold）。

4) ニュース収集（RSS）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 銘柄コードセット（実運用では全コードを用意）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) カレンダー更新ジョブ（夜間バッチ）

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"market_calendar updated: {saved}")
```

---

## 環境設定の自動読み込みについて

- パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動的に読み込みます（OS 環境変数 > .env.local > .env の優先度）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに便利です）。

---

## 実行モード（KABUSYS_ENV）

- KABUSYS_ENV は以下のいずれかを設定します:
  - development
  - paper_trading
  - live
- `Settings.is_live` / `is_paper` / `is_dev` で判定できます。実運用でライブ注文を行う際は `live` を使用し、十分な安全対策を行ってください。

---

## ディレクトリ構成（抜粋）

以下はソースツリーの主要部分（src/kabusys 内）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 / 保存）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義と初期化
    - stats.py               — 統計ユーティリティ（Z スコア正規化）
    - pipeline.py            — ETL パイプライン（run_daily_etl など）
    - calendar_management.py — マーケットカレンダー管理
    - features.py            — data.stats の公開インターフェース
    - audit.py               — 監査ログ（発注・約定トレース）スキーマ
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン・IC・統計サマリ等
  - strategy/
    - __init__.py
    - feature_engineering.py — features の構築（正規化・ユニバースフィルタ）
    - signal_generator.py    — シグナル生成（final_score、BUY/SELL）
  - execution/
    - __init__.py            — 発注/実行層（実装は別途）
  - monitoring/              — 監視・アラート（存在が示唆されるが実装ファイルは抜粋外）

（上記は主要モジュールの抜粋です。詳細はソースを参照してください）

---

## 開発上の注意・設計方針（抜粋）

- ルックアヘッドバイアス回避のため、特徴量計算やシグナル生成は target_date 時点で利用可能なデータのみを使う設計になっています。
- データ保存は冪等（ON CONFLICT）を意識しているため、差分更新や再実行が安全に可能です。
- ニュース収集は SSRF 対策、XML 脆弱性対策、受信サイズ上限などを考慮して実装されています。
- API リクエストはレート制限・リトライを組み込んでいます。J-Quants の制限（120 req/min）に対応する実装があります。

---

## よくある操作（FAQ 形式）

- Q: DuckDB スキーマの初期化はどのように行いますか？  
  A: data.schema.init_schema(db_path) を呼んでください。初回はこれで全テーブルが生成されます。

- Q: .env が読み込まれない／テスト時に読み込みを止めたい  
  A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます。

- Q: 実際に発注（ブローカー連携）する部分は含まれていますか？  
  A: execution 層はインターフェース/スキーマ設計を含みますが、具体的なブローカー統合は別実装（設定や証券会社 API に依存）になる想定です。production（live）での運用は十分な検証・安全策が必須です。

---

## 貢献／拡張

- 新しいデータソース、戦略の追加、execution 層のブローカー連携、監視/アラート統合などは歓迎します。
- 大きな設計変更や外部依存追加は README とドキュメントに明記してください。

---

以上が本リポジトリの README 相当の概要です。  
具体的なユースケースやサンプルスクリプト（cron / Airflow / CI に組み込む方法）などが必要であれば、用途に合わせた追加の README や運用ガイドを作成します。