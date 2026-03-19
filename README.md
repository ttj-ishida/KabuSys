# KabuSys

日本株向けの自動売買システム用ライブラリセットです。データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ／監査ログなど、戦略開発〜実行の各層をモジュール化しています。

主に研究環境（feature / research）と運用環境（ETL / execution）を想定しており、発注ロジック（ブローカー連携）とは分離して設計されています。

バージョン: 0.1.0

---

## 主要機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、財務データ、JPX カレンダー取得（ページネーション・リトライ・トークン自動リフレッシュ・レートリミット対応）
- DuckDB ベースのスキーマ定義 & 初期化（raw / processed / feature / execution / audit 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 特徴量計算（モメンタム / ボラティリティ / バリュー など）、Z スコア正規化
- シグナル生成（複数コンポーネントの重み付き合成、Bear レジーム抑制、BUY/SELL 生成）
- ニュース収集（RSS：URL 正規化、トラッキングパラメータ除去、SSRF 対策、記事→銘柄紐付け）
- マーケットカレンダー管理（営業日判定・次/前営業日検索・夜間更新ジョブ）
- 監査ログ（signal → order → execution のトレーサビリティを保持するテーブル群）
- 環境変数による設定管理（.env 自動読み込み機能有り。パッケージ配布後も動作するようプロジェクトルート探索）

---

## 必要条件（例）

- Python 3.10+
- duckdb
- defusedxml
- （ネットワークアクセス先）J-Quants API の利用資格

必要パッケージはプロジェクトの requirements に依存します。最低限、duckdb と defusedxml が必要です。

インストール例（仮）:
```
python -m pip install "duckdb" "defusedxml"
python -m pip install -e .
```

（実プロジェクトでは pyproject.toml / requirements.txt を参照してください）

---

## 環境変数（主な項目）

設定は .env または OS 環境変数から読み込まれます。自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（ライブラリ内で ID トークンに変換されます）
- KABU_API_PASSWORD
  - kabuステーション等の API パスワード（execution 層で利用想定）
- SLACK_BOT_TOKEN
  - Slack 通知に使用するボットトークン
- SLACK_CHANNEL_ID
  - Slack 通知先チャンネル ID

任意（デフォルトあり）
- KABUSYS_ENV: 開発環境フラグ。`development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL: ログレベル。`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）
- KABUS_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）

設定は `from kabusys.config import settings` で参照できます（例: `settings.jquants_refresh_token`）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
```
git clone <repository-url>
cd <repository>
```

2. Python 仮想環境を作成して有効化
```
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
```

3. 必要パッケージをインストール
```
pip install -e .           # パッケージを開発モードでインストール (もし setup/pyproject がある場合)
pip install duckdb defusedxml
```

4. 環境変数ファイルを作成
```
cp .env.example .env
# 必要なトークン等を .env に設定
```

5. DuckDB スキーマを初期化
Python REPL やスクリプトで:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# これで DuckDB ファイルに全テーブルが作成されます
conn.close()
```

---

## 使い方（主要 API と例）

以下は典型的なワークフローの例です。日次 ETL → 特徴量計算 → シグナル生成、という流れを想定しています。

- 日次 ETL 実行（市場カレンダー取得・株価・財務データ・品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 特徴量ビルド（features テーブルへ保存）
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
from datetime import date

conn = get_connection("data/kabusys.duckdb")
num = build_features(conn, target_date=date(2026, 1, 31))
print(f"features upserted: {num}")
conn.close()
```

- シグナル生成
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total_signals = generate_signals(conn, target_date=date(2026, 1, 31))
print(f"signals written: {total_signals}")
conn.close()
```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット (例)
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

- マーケットカレンダー更新（夜間バッチ）
```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
conn.close()
```

- 設定参照例
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live, settings.log_level)
```

---

## ディレクトリ構成（抜粋）

（リポジトリの `src/kabusys` を中心に記載）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント / 保存ユーティリティ
      - news_collector.py        # RSS ニュース収集・保存・銘柄抽出
      - schema.py                # DuckDB スキーマ定義・初期化
      - stats.py                 # 統計ユーティリティ（zscore_normalize 等）
      - pipeline.py              # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py   # カレンダー管理・判定・更新ジョブ
      - features.py              # data 層の特徴量ユーティリティ再公開
      - audit.py                 # 監査ログ関連 DDL
    - research/
      - __init__.py
      - factor_research.py       # モメンタム/ボラティリティ/バリュー等の計算
      - feature_exploration.py   # 将来リターン計算・IC・統計サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py   # features 作成パイプライン
      - signal_generator.py      # final_score 計算 → signals 生成
    - execution/                 # 発注／実行層（空/__init__ 用意）
    - monitoring/                # 監視・モニタリング（実装想定）

コードはモジュール単位で分割されており、ETL と戦略ロジックは明確に分離されています。

---

## 動作上の注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス対策: 各処理は target_date 時点のデータのみを参照するよう設計されています。
- 冪等性: DuckDB への保存は ON CONFLICT 句やトランザクションにより冪等を保つようにしています。
- エラーハンドリング: ETL やニュース収集はソース毎に独立して例外処理し、可能な限り処理継続を行います（Fail-Fast ではない）。
- セキュリティ対策:
  - RSS は URL 正規化・トラッキング除去、SSRF 対策（リダイレクト先のホスト検査）を施しています。
  - J-Quants API 呼び出しはレート制限、リトライ、トークン自動更新を実装しています。
- テスト容易性: id_token を注入できる等、外部依存を差し替え可能にしてあります。

---

## 貢献・拡張

- 戦略の重みや閾値は signal_generator の引数（weights / threshold）で変更可能です。
- 発注実装（execution 層）は現状スケルトンになっているので、ブローカー API を接続する際は execution モジュールを実装してください。
- 監査ログやスキーマは将来的な要件に合わせて拡張可能ですが、FK の取り扱い（DuckDB のバージョン差分）に注意してください。

---

以上が README の概要です。必要であれば、具体的なコマンドや CI／デプロイ手順、より詳細な環境変数の例（.env.example の内容）などを追記します。どの項目を優先して詳述しますか？