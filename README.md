# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータプラットフォームと自動売買の基盤を提供する Python ライブラリです。J-Quants API からのデータ取得、DuckDB によるデータ格納・スキーマ管理、特徴量計算、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、ETL パイプラインなど、研究〜運用までの一連の処理をサポートします。

主な設計方針:
- ルックアヘッドバイアスを避けるため、常に target_date 時点までのデータのみを使用
- DuckDB をストレージとして採用し、冪等性（ON CONFLICT）とトランザクションで整合性を維持
- 外部 API 呼び出しは data 層（jquants_client 等）に限定し、戦略層は発注 API に依存しない

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足、四半期財務、マーケットカレンダー）
  - レート制限・リトライ・トークン自動更新対応
  - raw → processed への ETL（差分更新・バックフィル対応）
- データ管理
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
- ニュース収集
  - RSS フィード取得、前処理、記事保存、本文から銘柄コード抽出と紐付け
  - SSRF 対策、XML の安全パース、レスポンスサイズ上限など安全対策実装
- 研究・特徴量
  - ファクター計算モジュール（momentum / volatility / value）
  - 特徴量探索（将来リターン、IC、統計サマリー）
  - Zスコア正規化ユーティリティ
- 戦略
  - 特徴量の正規化〜features テーブルへの書き込み（build_features）
  - features と ai_scores を統合した final_score の計算、BUY/SELL シグナルの生成（generate_signals）
  - Bear レジームフィルタ、エグジット（ストップロス等）判定
- ETL パイプライン
  - run_daily_etl によりカレンダー/株価/財務の差分取得・保存・品質チェックを実行
- 監査・実行
  - 信頼性の高い監査ログ（signal_events / order_requests / executions 等）や実行層スキーマを提供

---

## 必要条件

- Python 3.10 以上（PEP 604 の union 型記法などを利用しているため）
- 主な外部依存:
  - duckdb
  - defusedxml

例（最低限の依存をインストールする場合）:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクトをパッケージとしてインストールできる構成（pyproject.toml 等）がある場合は:
```bash
pip install -e .
```

---

## 環境変数（主な設定）

このパッケージは .env または環境変数から設定を読み込みます（プロジェクトルートに `.git` または `pyproject.toml` がある場合、自動で `.env` → `.env.local` を読み込みます）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注層利用時）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

オプション（デフォルト値あり）:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルト: INFO
- KABUS_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

例 .env（サンプル）:
```
JQUANTS_REFRESH_TOKEN=xxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 必要最低限:
     ```bash
     pip install duckdb defusedxml
     ```
   - もし pyproject.toml / requirements.txt があれば:
     ```bash
     pip install -e .
     # または
     pip install -r requirements.txt
     ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートします（上記必須項目をセット）。

5. DuckDB スキーマを初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb
   ```

   init_schema は親ディレクトリがなければ自動作成し、すべてのテーブルとインデックスを作成します。

---

## 使い方（簡易ガイド）

以下は代表的なユースケースのコード例です。

- 日次 ETL を実行してデータを更新する:
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）を作成する:
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"built features for {n} symbols")
```

- シグナルを生成して signals テーブルへ保存する:
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"generated {count} signals")
```

- RSS ニュースの収集と保存:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- マーケットカレンダーの夜間更新:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved {saved} calendar rows")
```

ログレベルは環境変数 LOG_LEVEL で制御してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py  (パッケージ定義、__version__ = "0.1.0")
  - config.py    (環境変数 / 設定管理)
  - data/
    - __init__.py
    - jquants_client.py      (J-Quants API クライアント)
    - schema.py              (DuckDB スキーマと初期化)
    - pipeline.py            (ETL パイプライン)
    - news_collector.py      (RSS ニュース収集)
    - calendar_management.py (マーケットカレンダー管理)
    - audit.py               (監査ログスキーマ)
    - stats.py               (統計ユーティリティ: zscore_normalize)
    - features.py            (features インターフェース)
    - execution/             (発注・実行関連のプレースホルダ)
  - research/
    - __init__.py
    - factor_research.py     (momentum/volatility/value の計算)
    - feature_exploration.py (IC, 将来リターン, サマリー)
  - strategy/
    - __init__.py
    - feature_engineering.py (features テーブル作成ロジック)
    - signal_generator.py    (final_score & シグナル生成)
  - monitoring/              (監視関連: 未展開の可能性あり)

（上記は現行コードベースの主なモジュールと役割の一覧です）

---

## 注意事項 / 運用メモ

- DuckDB のファイルパス（DUCKDB_PATH）はデフォルトで data/kabusys.duckdb。init_schema は親ディレクトリを自動作成します。
- .env 自動ロードはプロジェクトルート検出による（.git または pyproject.toml）。テストや特殊実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- J-Quants API のレート制限（120 req/min）遵守のためモジュール側で制御しています。大量取得時はバックオフや分散スケジュールを検討してください。
- news_collector は外部 URL の取り扱いに関して SSRF 対策やレスポンスサイズ制限など安全対策を組み込んでいますが、運用時は取得元の信頼性と頻度に注意してください。
- 戦略の重みや閾値は generate_signals の引数で上書き可能ですが、合計重みは自動で正規化されます。

---

## 開発・貢献

- コーディング規約、テスト、CI の詳細はリポジトリの CONTRIBUTING.md / pyproject.toml / .github/workflows を参照してください（存在する場合）。
- ユニットテストの追加、品質チェックルールの拡張（data.quality モジュール）や execution 層のブリッジ実装などが想定されます。

---

README に含めてほしい追加情報（例えば利用例スクリプト、CI 手順、より詳細な環境構成など）があれば教えてください。必要に応じてサンプル .env.example や start-up スクリプトも作成します。