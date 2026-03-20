# KabuSys

日本株向けの自動売買基盤ライブラリ（研究・データ基盤・戦略・実行・監査）です。  
主に DuckDB をデータ層に用いて、J-Quants API と RSS ニュースを取り込み、ファクター計算 → 特徴量生成 → シグナル生成 → 発注（実行レイヤ）までのワークフローを支援します。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API クライアント（レートリミット管理・リトライ・トークン自動更新）
  - 株価（OHLCV）、財務データ、マーケットカレンダーの差分取得
  - DuckDB への冪等（ON CONFLICT）保存
  - ETL パイプライン（run_daily_etl など）と品質チェックの統合

- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 除去、XML 安全パーサ）
  - 記事正規化・ID発行（URL 正規化 + SHA-256）
  - raw_news / news_symbols への冪等保存、記事→銘柄抽出

- 研究（research）ユーティリティ
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（スピアマン順位相関）、ファクター要約
  - クロスセクション Z スコア正規化

- 戦略（strategy）層
  - 特徴量エンジニアリング（build_features）
  - シグナル生成（generate_signals）：複合スコア計算、Bear 判定、BUY/SELL の生成、冪等的な signals テーブル更新

- スキーマ・監査
  - DuckDB 用の包括的スキーマ定義と初期化（init_schema）
  - 監査ログ（signal_events / order_requests / executions）によるトレーサビリティ設計

- 運用面の設計
  - 自動 .env 読み込み（プロジェクトルート基準）
  - 設定管理（kabusys.config.settings）
  - 安全性：SSRF、XML インジェクション、巨大レスポンス、プライベートIPブロックなどを考慮

---

## 必要条件 / 推奨環境

- Python >= 3.10（| 型注釈や一部構文を使用しているため）
- DuckDB（Python パッケージ）
- defusedxml（RSS XML の安全パース）
- インターネット接続（J-Quants API / RSS フェッチを行う場合）

必須パッケージ（最低限）:
- duckdb
- defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# （パッケージが PyPI に公開されていれば）pip install -e .
```

プロジェクトとして使う場合は setup/pyproject に応じて `pip install -e .` を想定しています。

---

## 環境変数（設定）

kabusys は環境変数（またはプロジェクトルートの `.env`, `.env.local`）から設定を読み込みます。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能です。

主な必須変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

その他（省略可 / デフォルトあり）:
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視用）（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）

.env の例（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定取得例（コード）:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
db_path = settings.duckdb_path
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンし仮想環境を作る
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # 必要に応じて他依存 (例: slack_sdk 等) を追加
   ```

2. 環境変数を用意
   - プロジェクトルートに `.env` を作成するか、シェルの環境変数に設定してください。
   - 自動読み込みは .git または pyproject.toml を基準に行われます。

3. DuckDB スキーマの初期化
   Python REPL やスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（主な API）

以下は主要なワークフローの例です。すべて冪等的（同日再実行で上書き）に動作するよう設計されています。

- DuckDB 接続の取得 / スキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection

# 初回: スキーマを作る
conn = init_schema("data/kabusys.duckdb")

# 既存 DB へ接続（初期化は行わない）
conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ファクター → 特徴量の作成（strategy.feature_engineering）
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, date.today())
print(f"features upserted: {n}")
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

total_signals = generate_signals(conn, date.today(), threshold=0.6)
print(f"signals generated: {total_signals}")
```

- RSS ニュース収集（news_collector）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は有効な銘柄コードの集合（例: DB から取得した銘柄一覧）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- J-Quants API を直接呼ぶ（必要な場面で）
```python
from kabusys.data.jquants_client import fetch_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 注意点 / 補足

- Python バージョン: 3.10 以上を推奨（型ヒントの | 演算子等を使用）
- DuckDB をデータ格納に使用するため、ファイルの永続化先（DUCKDB_PATH）を適切に設定してください。
- J-Quants API の利用には有効なトークン（JQUANTS_REFRESH_TOKEN）が必要です。401 発生時は自動でトークンを更新する実装を含みます。
- ニュース収集は外部 HTTP を行うため、社内ネットワークやプロキシ、ファイアウォールの影響を受けます。
- パッケージの一部機能（Slack 通知、kabu API 連携など）は外部ライブラリや接続設定が別途必要になる場合があります（このコードベースでは設定の読み取りまでは定義されていますが、Slack クライアント等は含まれていません）。

---

## ディレクトリ構成

（主要ファイル / モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
      - news_collector.py      — RSS ニュース収集・保存
      - schema.py              — DuckDB スキーマ定義・初期化
      - stats.py               — 統計ユーティリティ（zscore_normalize 等）
      - pipeline.py            — ETL パイプライン（run_daily_etl など）
      - features.py            — data 側の features 公開
      - calendar_management.py — 市場カレンダー管理・ジョブ
      - audit.py               — 監査ログテーブル DDL
    - research/
      - __init__.py
      - factor_research.py     — ファクター計算（momentum/volatility/value）
      - feature_exploration.py — 将来リターン / IC / サマリー計算
    - strategy/
      - __init__.py
      - feature_engineering.py — features 作成（build_features）
      - signal_generator.py    — シグナル生成（generate_signals）
    - execution/                — 発注 / 実行関連（空のパッケージプレースホルダ）
    - monitoring/               — 監視系（プレースホルダ）

---

この README はコードベースに基づく基本的な導入・利用手順をまとめたものです。必要であれば以下を追加できます：
- 実行例の詳細スクリプト（cron / Airflow 用タスク例）
- テスト実行方法
- より詳細な .env.example（全ての設定キー一覧）
- Slack/発注 API と統合するためのサンプルコード

追加希望があれば、どの項目を詳しく書くか教えてください。