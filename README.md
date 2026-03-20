# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどをモジュール化して提供します。内部的には DuckDB をデータストアとして使用し、戦略ロジックはルックアヘッドバイアスを防ぐ設計になっています。

---

## 主な特徴

- J-Quants API クライアント（ページネーション / レート制限 / トークン自動リフレッシュ / リトライ）
- DuckDB ベースのスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- ファクター計算（Momentum / Volatility / Value など）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ、日付単位での冪等保存）
- シグナル生成（複数コンポーネントスコアの統合、BUY/SELL 判定、Bear レジーム判定、エグジット判定）
- ニュース収集（RSS フィード、SSRF 対策、トラッキング除去、銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev 営業日算出、夜間更新ジョブ）
- 監査ログモデル（シグナル → 発注 → 約定のトレースを可能にするスキーマ）

---

## 要件

- Python 3.10 以上（型ヒントで PEP 604 の `|` を使用）
- 必要な主要パッケージ（例）:
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）

---

## 環境変数

以下の環境変数を利用します（いずれも .env に記載してプロジェクトルートに置くと自動読み込みされます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)、デフォルト development
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)、デフォルト INFO

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   (例: venv)
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   （実際はプロジェクトの pyproject.toml / requirements.txt を使用してください。最低限の例:）
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数を .env に設定（上記参照）。プロジェクトルートに `.env` / `.env.local` があると自動で読み込まれます。

---

## データベース初期化

DuckDB スキーマを初期化して接続を取得する例:

```python
from pathlib import Path
from kabusys.data import schema

db_path = Path("data/kabusys.duckdb")
conn = schema.init_schema(db_path)
# conn は duckdb.DuckDBPyConnection
```

:init_schema は冪等で、必要なディレクトリを自動作成します。メモリ DB を使う場合は `":memory:"` を渡します。

---

## 基本的な使い方（コード例）

- 日次 ETL を実行（市場カレンダー、株価、財務データ、品質チェック）:

```python
from datetime import date
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）を構築:

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成:

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals generated: {total}")
```

- ニュース収集ジョブ実行:

```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出で利用する銘柄コードのセット（例: {"7203","6758",...}）
results = news_collector.run_news_collection(conn, sources=None, known_codes=None)
print(results)
```

- カレンダー夜間更新ジョブ:

```python
from kabusys.data import calendar_management
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"calendar rows saved: {saved}")
```

---

## モジュール概要（主なファイルと役割）

- kabusys/config.py
  - 環境変数の読み込み・管理（.env 自動読み込み、必須チェック）
- kabusys/data/
  - jquants_client.py : J-Quants API クライアント（取得・保存ユーティリティ）
  - schema.py        : DuckDB スキーマ定義と初期化
  - pipeline.py      : ETL パイプライン（run_daily_etl 等）
  - news_collector.py: RSS ベースのニュース収集と DB 保存
  - calendar_management.py: 市場カレンダー管理・営業日判定
  - stats.py         : Z スコア正規化など統計ユーティリティ
  - features.py      : data.stats の再エクスポート
- kabusys/research/
  - factor_research.py : ファクター計算（momentum, volatility, value）
  - feature_exploration.py : 将来リターン・IC・統計サマリー
- kabusys/strategy/
  - feature_engineering.py : ファクター正規化・features 保存
  - signal_generator.py    : final_score 計算、BUY/SELL シグナル生成
- kabusys/execution/、kabusys/monitoring/ : 発注・監視関連（実装ファイルがこのコードベースに部分的に含まれます）
- kabusys/__init__.py : パッケージバージョン等

---

## ディレクトリ構成

（抜粋。実際のリポジトリには pyproject.toml 等がある想定）

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ data/
│     │  ├─ __init__.py
│     │  ├─ jquants_client.py
│     │  ├─ schema.py
│     │  ├─ pipeline.py
│     │  ├─ news_collector.py
│     │  ├─ calendar_management.py
│     │  ├─ stats.py
│     │  ├─ features.py
│     │  └─ audit.py
│     ├─ research/
│     │  ├─ __init__.py
│     │  ├─ factor_research.py
│     │  └─ feature_exploration.py
│     ├─ strategy/
│     │  ├─ __init__.py
│     │  ├─ feature_engineering.py
│     │  └─ signal_generator.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ (監視関連モジュール)
└─ (その他: pyproject.toml / README.md / .env.example / tests / ...)
```

---

## 注意点・運用上のヒント

- 環境変数は自動で .env / .env.local から読み込まれます（ただしプロジェクトルートが .git または pyproject.toml で判定されます）。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットして無効化できます。
- J-Quants API のレート制限に注意（モジュールは 120 req/min を前提に固定間隔でスロットリングします）。
- ETL は冪等デザイン（差分取得・ON CONFLICT を多用）で作られているため、定期実行（cron / Airflow / similar）に適します。
- DuckDB ファイルのバックアップや運用ポリシーは各運用環境に合わせて設計してください（特に本番用口座を扱う場合は権限・バックアップ・監査に注意）。

---

必要であれば以下も提供できます:
- requirements.txt / pyproject.toml の例
- デプロイ手順（systemd / Docker / コンテナ化）
- CI / テスト実行例（ユニットテスト・モック戦略）