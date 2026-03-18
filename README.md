# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）を提供し、J-Quants API からのデータ収集、ETL パイプライン、品質チェック、ニュース収集、ファクター計算（リサーチ用）などを備えています。

---

## 概要（Project Overview）

KabuSys は以下の目的で設計されています。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する（冪等）
- 日次 ETL パイプラインで差分更新・バックフィル・品質チェックを行う
- RSS ベースのニュース収集と記事→銘柄紐付けの自動化（SSRF 対策、gzip/サイズ制限、トラッキング除去）
- リサーチ向けファクター計算（モメンタム・ボラティリティ・バリュー）と特徴量探索（将来リターン・IC 計算等）
- 発注 / 監査用スキーマを備え、シグナル→オーダー→約定までのトレーサビリティを確保

設計方針として、本番発注 API への直接呼び出しを行わないモジュール（Data / Research）は分離されており、外部依存を最小限（標準ライブラリ + 必要最小限のライブラリ）に抑えています。

---

## 主な機能一覧（Features）

- データ取得 / 保存
  - J-Quants API クライアント（レートリミット管理・リトライ・トークン自動リフレッシュ）
  - fetch / save: 日次株価、財務（四半期）、JPX カレンダー
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
  - 市場カレンダーの夜間更新ジョブ（calendar_update_job）
- データ品質チェック（quality）
  - 欠損、スパイク、重複、日付不整合の検出
- ニュース収集（news_collector）
  - RSS 取得・前処理・ID 生成（URL 正規化 + SHA256）、DB への冪等保存、銘柄抽出
  - SSRF 対策、gzip / サイズ上限、XML 安全パーサ（defusedxml）
- リサーチ（research）
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（将来リターン calc_forward_returns、IC calc_ic、統計サマリー factor_summary）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）
- スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution / Audit 用の DuckDB テーブル定義と初期化関数（init_schema / init_audit_db）
- 監査ログ（audit）
  - signal_events / order_requests / executions 等、監査用テーブルの初期化とインデックス

---

## 前提・依存（Requirements）

- Python 3.10 以上（typing の | 演算子などを使用しているため）
- 必要なパッケージ（最低限）:
  - duckdb
  - defusedxml
- 標準ライブラリの urllib, datetime, logging など

インストール例（仮に仮想環境を利用する場合）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージ開発インストール（pyproject.toml/セットアップがあれば）
pip install -e .
```

---

## セットアップ手順（Setup）

1. リポジトリをクローン / 配布パッケージを用意

2. Python 環境の準備 & 依存インストール（上記参照）

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須環境変数（Settings で必須になっているもの）:
     - JQUANTS_REFRESH_TOKEN ・・・J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD       ・・・（kabuステーション API）パスワード
     - SLACK_BOT_TOKEN         ・・・Slack 通知用（必要に応じて）
     - SLACK_CHANNEL_ID        ・・・Slack 通知先チャンネル ID
   - 任意 / デフォルトを持つ環境変数:
     - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | …) デフォルト: INFO
     - KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で自動ロード無効)
     - KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

   例: .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
   KABU_API_PASSWORD=あなたのkabuパスワード
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```

4. DuckDB スキーマ初期化
   - Python REPL / スクリプトで init_schema を実行して DB を初期化します（ファイルパスは settings.duckdb_path を使うか明示的に指定）。

---

## 初期化・実行例（使い方 / Usage）

以下は簡単な Python スクリプト例です。プロジェクトルートで実行してください。

- DB スキーマ初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# 設定されたパスに DuckDB ファイルを作成し、全テーブルを初期化
conn = init_schema(settings.duckdb_path)
print("DB initialized:", settings.duckdb_path)
conn.close()
```

- 日次 ETL の実行（run_daily_etl）

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # 既に初期化済みなら接続を取得
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- ニュース収集ジョブの実行（RSS 取得 → DB 保存 → 銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes は銘柄コードのセット（extract_stock_codes に利用）
# 例: {"7203", "6758", ...}
known_codes = {"7203", "6758"}

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

- J-Quants から日次株価を直接取得（テストやデバッグ）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from datetime import date

token = get_id_token()  # settings.jquants_refresh_token から取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
print(f"fetched {len(records)} records")
```

- リサーチ：モメンタム計算例

```python
from kabusys.research.factor_research import calc_momentum
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
momentum = calc_momentum(conn, target_date=date(2024,1,31))
print(momentum[:5])
conn.close()
```

---

## よく使う API の一覧（主な公開関数）

- data.schema.init_schema(db_path) → DuckDB 接続（スキーマ初期化）
- data.jquants_client.get_id_token() / fetch_daily_quotes(...) / save_* 関数
- data.pipeline.run_daily_etl(conn, target_date, ...)
- data.news_collector.run_news_collection(conn, sources, known_codes)
- data.calendar_management.calendar_update_job(conn)
- data.quality.run_all_checks(conn, target_date, reference_date)
- research.factor_research.calc_momentum / calc_volatility / calc_value
- research.feature_exploration.calc_forward_returns / calc_ic / factor_summary
- data.stats.zscore_normalize(records, columns)

---

## 開発・テストのヒント

- 自動環境変数読み込みは .env / .env.local をプロジェクトルートから探して行います。CI やテストで自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化関数は冪等（既存テーブルがあればスキップ）です。監査スキーマは別関数 init_audit_schema / init_audit_db で初期化します。
- news_collector はネットワークアクセスおよび XML パースを行うため、ユニットテストでは _urlopen / fetch_rss をモックすると安定的にテストできます。
- J-Quants API 呼び出しはレート制限・リトライ・401 リフレッシュ等に対応しています。大量取得やループでの利用時は注意してください。

---

## ディレクトリ構成（Directory Structure）

主要ファイルを抜粋した構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - etl.py
    - quality.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記はリポジトリ内の主要モジュールの一覧です。実際のファイルはさらに細分化される場合があります）

---

## 注意事項

- この README はコードベース（src 内）にある設計コメント・docstring を元にした概要です。実際に運用する際は .env.example（存在する場合）や J-Quants / kabu API の利用規約・キー管理方針に従ってください。
- 発注・実際の資金運用を行う場合は paper_trading 環境で十分に検証してください。KABUSYS_ENV を `live` に設定する前に安全性チェックを行ってください。
- データベースファイルのバックアップや取り扱いには注意してください（DuckDB ファイルは単一ファイルで管理されます）。

---

もし README に追加したい運用手順（デプロイ、CI、バックフィル方法、Slack 通知の設定例など）があれば、その内容を教えてください。必要に応じてサンプルスクリプトや .env.example のテンプレートを作成します。