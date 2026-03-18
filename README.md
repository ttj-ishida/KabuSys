# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB をデータ層に用いた ETL / データ品質管理、J-Quants からのデータ取得クライアント、RSS ニュース収集、ファクター計算とリサーチユーティリティ、監査ログ（オーダー/約定追跡）などを含むモジュール群を提供します。

---

## 概要（Project overview）

KabuSys は以下の目的で設計されています。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- 生データ → 整形データ → 特徴量 → 発注に至る 3 層（＋実行・監査）データモデル
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS からのニュース収集と銘柄抽出
- ファクター（モメンタム／バリュー／ボラティリティ等）計算、および IC / 統計サマリなどのリサーチ機能
- 監査ログ：シグナル→発注→約定の追跡に適したスキーマと初期化ユーティリティ

設計方針として、本番取引 API への直接発注は分離し、データ取得・研究・品質・監査を堅牢に実装することを重視しています。

---

## 主な機能（Features）

- 環境設定管理（.env 自動読み込み、必須チェック）
- J-Quants API クライアント
  - 日足（OHLCV）/ 財務四半期データ / マーケットカレンダーの取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT）
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution / audit）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
- ニュース収集（RSS）と銘柄抽出（正規化・SSRF 防止・gzip/size 保護）
- ファクター計算（momentum / volatility / value）および zscore 正規化
- リサーチ用ユーティリティ：forward returns, IC（Spearman）計算, 統計サマリ
- 監査ログ用スキーマ（signal_events, order_requests, executions）と初期化

---

## 必要条件（Prerequisites）

- Python 3.10 以上（typing の | 演算子等を使用）
- パッケージ
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb>=0.7" "defusedxml"
```

（プロジェクトが requirements.txt を持つ場合はそれを使用してください）

---

## 環境変数 / 設定（Environment）

kabusys は .env / .env.local（プロジェクトルート）または OS 環境変数から設定を読み込みます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。重要なキーは以下の通りです。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション用パスワード（発注モジュールで使用）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意／デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")（デフォルト: INFO）

注意点:
- .env の読み込み優先順: OS 環境 > .env.local > .env
- .env ファイルのパースは独自実装を使用しており、export 形式やクォート・コメントの取り扱いに対応しています。

設定の取得例（コード）:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
db_path = settings.duckdb_path
```

---

## セットアップ手順（Setup）

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo>
   ```

2. Python 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```bash
   pip install --upgrade pip
   pip install duckdb defusedxml
   # 他に必要なライブラリがあれば requirements.txt に従ってください
   ```

4. 環境変数を用意（プロジェクトルートに .env を作成）
   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL もしくはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   # conn を使って以後の ETL / クエリを実行できます
   ```

6. （監査ログ専用 DB を別に使う場合）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（Usage）

ここでは主要なユースケースの例を示します。

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# DB 初期化（既に作成済みならスキップ）
conn = init_schema(settings.duckdb_path)

# または既存接続
# conn = get_connection(settings.duckdb_path)

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- J-Quants から日足データを直接取得して保存する:
```python
from kabusys.data import jquants_client as jq
import duckdb
from kabusys.config import settings

conn = duckdb.connect(settings.duckdb_path)
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
saved = jq.save_daily_quotes(conn, records)
```

- RSS ニュース収集ジョブ実行:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
import duckdb
from kabusys.config import settings

conn = duckdb.connect(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- リサーチ（ファクター計算 / IC）:
```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 2, 28)
momentum = calc_momentum(conn, target)
forwards = calc_forward_returns(conn, target, horizons=[1,5,21])

# 例: mom_1m と fwd_1d の IC
ic = calc_ic(momentum, forwards, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

# Zスコア正規化
normalized = zscore_normalize(momentum, columns=["mom_1m", "ma200_dev"])
```

- データ品質チェックを単体実行:
```python
from kabusys.data.quality import run_all_checks
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2024,2,28))
for i in issues:
    print(i)
```

---

## 主要モジュール一覧（要点）

- kabusys.config
  - 環境変数の自動ロード・必須チェック（settings オブジェクト）
- kabusys.data.jquants_client
  - J-Quants API クライアント（fetch_* / save_*）
- kabusys.data.schema
  - DuckDB スキーマ定義と init_schema()
- kabusys.data.pipeline
  - run_daily_etl / 個別 ETL ジョブ（prices/financials/calendar）
- kabusys.data.news_collector
  - RSS フィード取得・前処理・DB への保存・銘柄抽出
- kabusys.data.quality
  - 各種データ品質チェック
- kabusys.data.stats, features
  - zscore_normalize 等の統計ユーティリティ
- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary
- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）初期化

---

## ディレクトリ構成（Directory structure）

主要ファイルとモジュール（抜粋）:

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
    - audit.py
    - etl.py
    - quality.py
  - research/
    - __init__.py
    - feature_exploration.py
    - factor_research.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各ファイルの責務は上記のセクションで説明した通りです。詳細はソース内の docstring を参照してください。

---

## 運用上の注意 / ベストプラクティス

- .env にシークレットを直接置く場合は Git 管理対象から除外する（.gitignore で除外推奨）。
- J-Quants の API レート制限・トークン管理に注意。get_id_token は自動リフレッシュを行いますが、適切なエラーハンドリングを設けてください。
- DuckDB ファイルはバックアップや GC のポリシーを決めて管理してください（大規模データ時のディスク容量）。
- ETL 実行時はまず calendar を取得してから prices を取得する設計になっています（営業日の調整に利用）。
- 研究（research）モジュールは本番オーダーに直接アクセスしません。実運用時は発注モジュール（execution）とリスク管理を必ず組み合わせてください。

---

## 今後の拡張案 / TODO（簡易メモ）

- 発注実行モジュール（kabu ステーション連携）の実装（受注/約定コールバック処理）
- Slack 通知やモニタリングダッシュボード統合
- テストスイートと CI の整備（unit/integration）
- packaging（pyproject.toml / setuptools / poetry）と配布

---

## サポート / 貢献（短記）

バグ修正・機能追加の貢献は歓迎します。プルリクエストや Issue を通してご連絡ください。リポジトリに README の英語版や開発者向けガイドがあると貢献がしやすくなります。

---

必要であれば、README に実行例のさらなる詳細（cron での日次実行例、Docker コンテナ化手順、CI/CD の例など）を追加します。必要な箇所を教えてください。