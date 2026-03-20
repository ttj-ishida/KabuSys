# KabuSys

KabuSys は日本株のデータ収集・特徴量生成・シグナル生成・ETL・ニュース収集・監査などを含む自動売買プラットフォームのコアライブラリ群です。DuckDB をデータストアとして利用し、J-Quants API や RSS フィードを通じて市場データ・財務データ・ニュースを収集・処理します。戦略層（feature_engineering / signal_generator）はルックアヘッドバイアスを回避する設計になっており、本番発注ロジックとは分離されています。

主な設計方針：
- 冪等性（ON CONFLICT / トランザクション）を重視
- ルックアヘッドバイアス防止（target_date 時点のデータのみ利用）
- API レート制御・リトライ・トークン自動更新対応（J-Quants クライアント）
- SSRF・XML Bomb 等の対策（ニュース収集）

---

## 機能一覧

- データ取得・保存（J-Quants API 経由）
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック
  - 日次 ETL 実行エントリポイント
- DuckDB スキーマ定義 / 初期化（init_schema）
- 研究用ファクター計算（momentum / volatility / value）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ・features テーブル保存）
- シグナル生成（final_score の計算、BUY / SELL シグナルの生成、signals テーブル保存）
- ニュース収集（RSS → raw_news、銘柄抽出・news_symbols 保存）
- 市場カレンダー管理（営業日判定／次・前営業日取得／カレンダー更新バッチ）
- 監査ログ（signal_events / order_requests / executions 等のスキーマ）

---

## 必要条件 / 依存ライブラリ（例）

必須:
- Python 3.10 以上（コードは typing の近代的表記を使用）
- duckdb
- defusedxml

その他（標準ライブラリ中心で多くの処理は外部依存を避けていますが、HTTP/JSON 等に標準モジュールを使用しています）.

インストール例（プロジェクト直下で）:
```bash
python -m pip install -U pip setuptools
python -m pip install duckdb defusedxml
# 開発インストール（パッケージ化されている場合）
python -m pip install -e .
```

※ requirements.txt はこのリポジトリに含まれていないため、環境に応じて必要なライブラリを追加してください。

---

## 環境変数

このライブラリは環境変数（またはプロジェクトルートの `.env` / `.env.local`）から設定を自動読み込みします。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須・推奨）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注等）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）

例: `.env`（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン／配置
2. Python 環境を用意（venv 等推奨）
3. 依存ライブラリをインストール（duckdb, defusedxml 等）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. DuckDB スキーマを初期化

サンプル:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install duckdb defusedxml
# (オプション) pip install -e .
# .env を作成

# Python REPL で初期化
python - <<'PY'
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ディレクトリ自動作成されます
print("initialized:", conn)
conn.close()
PY
```

---

## 使い方（主要 API の例）

以下は最小限の利用フロー例です。実運用ではログ・エラーハンドリング・スケジューリングを併用してください。

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量作成（features テーブルへ保存）:
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection, init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 10))
print("built features:", n)
```

- シグナル生成（signals テーブルへ保存）:
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 10))
print("signals written:", count)
```

- ニュース収集ジョブ:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes を与えると記事に出現する銘柄コードの紐付けを実行
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)
```

- カレンダー更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意点:
- 本パッケージの戦略層（build_features / generate_signals）は発注 API へ直接依存しません。発注は execution 層（将来的な実装）を通じて行ってください。
- J-Quants API 呼び出しはレート制限・リトライ・トークン更新を内包します。テスト時は id_token を注入してモックすることが可能です（jquants_client の関数は id_token 引数を受け入れます）。

---

## ディレクトリ構成

下記は主要ファイル・モジュールの概観（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/設定管理（.env 自動ロード等）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS → raw_news の収集処理
    - schema.py                    — DuckDB スキーマ定義・初期化
    - stats.py                     — Z スコア等の統計ユーティリティ
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       — market_calendar 管理
    - features.py                  — features API（再エクスポート）
    - audit.py                     — 監査ログスキーマ
    - (他: quality モジュール等想定)
  - research/
    - __init__.py
    - factor_research.py           — momentum / value / volatility 等の計算
    - feature_exploration.py       — forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py       — ファクター正規化・features 作成
    - signal_generator.py          — final_score 計算・BUY/SELL 生成
  - execution/                      — 発注/約定/ポジション管理（今後実装想定）
  - monitoring/                     — 監視・通知（Slack 等）用モジュール（想定）

各モジュールは docstring や関数レベルで使用方法・設計意図を詳細に記載しています。まずは schema.init_schema → pipeline.run_daily_etl → strategy.build_features → strategy.generate_signals の流れを試してみてください。

---

## テスト／開発メモ

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索して行われます。テスト中に自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のインメモリ使用は `db_path=":memory:"` を指定することで可能です（テストで便利）。
- jquants_client のネットワーク呼び出しは内部で rate limiter を用いているため、テストではこれら関数をモックして呼び出しを抑制してください。
- news_collector は defusedxml を使用して XML の安全パースを行っています。外部ネットワーク呼び出しは _urlopen をモックして制御可能です。

---

もし README に追加して欲しい項目（例：詳しい API 使用例、サンプルワークフロー、CI 設定、テストコマンド、ライセンス情報など）があれば教えてください。必要に応じてサンプルスクリプトや .env.example を追記します。