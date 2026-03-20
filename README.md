# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
DuckDB をデータ層に用い、J-Quants API や RSS からのニュース収集、ファクター計算、特徴量生成、シグナル生成、ETL パイプライン、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 主要機能（概要）

- データ取得 / 保存
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）
  - RSS からのニュース収集（前処理、記事ID正規化、銘柄抽出）
  - DuckDB への冪等保存（ON CONFLICT / INSERT ... DO UPDATE/DO NOTHING）
- ETL パイプライン
  - 差分取得（バックフィル対応）、品質チェック、日次 ETL エントリ
- データスキーマ
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
- リサーチ / 戦略
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
  - シグナル生成（final_score の算出、BUY/SELL の判定、エグジット判定）
- マーケットカレンダー管理（営業日判定、次/前営業日取得）
- 監査ログ（signal → order → execution のトレーサビリティ）
- 汎用統計ユーティリティ（Z スコア正規化等）

---

## 必要条件

- Python 3.10+ 推奨（typing 機能を多用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- （プロジェクトに requirements.txt があればそれを使用してください）

例（依存パッケージが明記されていない場合のインストール例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはパッケージ化されていれば:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／配置する
2. 仮想環境を作成して依存をインストール
3. 環境変数を設定（.env をプロジェクトルートに置くと自動的に読み込まれます）
4. DuckDB スキーマを初期化

例:
```bash
git clone <repo_url>
cd <repo_dir>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # または必要パッケージを個別にインストール
```

DuckDB スキーマ初期化（Python REPL / スクリプト例）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# これで data/kabusys.duckdb が作成され、全テーブルが作成されます
```

---

## 環境変数（主なもの）

自動読み込み順: OS 環境変数 > .env.local > .env  
自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（Settings にて _require されるもの）:
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD：kabuステーション API のパスワード
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID：Slack チャネル ID

オプション / デフォルトあり:
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（主要ワークフロー）

以下は代表的な利用例（Python スクリプト／REPL）。

1) データベース初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（株価・財務・市場カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）構築
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 有効な銘柄コードセット（例: prices_daily から取得）
known_codes = set([row[0] for row in conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()])

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar records saved: {saved}")
```

---

## 仕組みと注意点（実装上の重要ポイント）

- ETL・取得処理は差分・バックフィルを行い、冪等に保存します（ON CONFLICT / bulk insert）。
- J-Quants クライアントはレートリミット（120 req/min）、リトライ（指数バックオフ）、401 のトークン自動リフレッシュに対応しています。
- NewsCollector は SSRF 対策、XML インジェクション対策（defusedxml）、レスポンスサイズ制限 等の安全策を備えています。
- 特徴量生成およびシグナル生成はルックアヘッドバイアスを防ぐため、target_date 時点のデータのみを使用する設計です。
- システム設定（KABUSYS_ENV）により live / paper_trading / development を切り替え可能です。live 環境では実際の発注等を行うレイヤと組み合わせる想定です（本 repo は発注層との疎結合設計）。

---

## ディレクトリ構成

主なファイル／モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、fetch_* / save_* 関数
    - news_collector.py
      - RSS 取得・正規化・DB 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize など統計ユーティリティ
    - pipeline.py
      - run_daily_etl、個別 ETL ジョブ（prices/financials/calendar）
    - calendar_management.py
      - 営業日判定・calendar_update_job 等
    - audit.py
      - 監査ログ用 DDL（signal_events / order_requests / executions 等）
    - features.py
      - data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリューの計算
    - feature_exploration.py
      - forward returns / IC / factor summary 等の分析ユーティリティ
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル構築（normalize / universe filter）
    - signal_generator.py
      - final_score 計算と signals テーブル挿入
  - execution/
    - (発注・execution 層のエントリやラッパーを想定)
  - monitoring/
    - (監視・アラート連携等を想定)

---

## 開発・貢献

- コードベースはユニットテストを想定した設計（外部依存を引数で注入できる等）です。テストを書く際は J-Quants への実 HTTP を行わないようにモックを使用してください（例: jquants_client._request、news_collector._urlopen など）。
- .env や .env.local を使用して開発用の設定を管理してください。
- 自動ロードをテスト時に抑制するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ライセンス

（プロジェクトのライセンス情報をここに記載してください）

---

README の内容は実装コード（各モジュールの docstring）を元にまとめています。追加で CLI、サンプルスクリプト、requirements.txt、.env.example、テスト手順などを用意すると導入がさらに容易になります。必要であればそれらのテンプレートを作成します。