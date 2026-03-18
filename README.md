# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータ層に用い、J-Quants API／RSS 等から市場データ・財務データ・ニュースを収集し、特徴量計算や戦略・発注・監査までを想定したモジュール群を提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（設定項目）
- 使い方（主要 API の例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を主目的としています。

- J-Quants API から株価日足・財務データ・市場カレンダーを安全に取得して DuckDB に蓄積する ETL。
- RSS からニュースを収集して前処理・銘柄紐付けして DuckDB に保存するニュースコレクタ。
- 価格・財務データから Momentum/Volatility/Value 等のファクターを計算する研究ユーティリティ。
- データ品質チェック（欠損・スパイク・重複・日付不整合）と監査（注文→約定トレース）用スキーマ。
- 本番（live）・疑似取引（paper_trading）・開発（development）を想定した設定管理。

設計方針の要点：
- DuckDB を単一の永続層として利用（冪等保存、ON CONFLICT で更新）。
- 外部 API 呼び出しは rate limit・リトライ・トークンリフレッシュ等を考慮。
- セキュリティ対策（RSS の SSRF 防止、XML の defusedxml 利用等）。
- 外部ライブラリへの依存を最小化（ただし duckdb, defusedxml 等は必要）。

---

## 主な機能

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、トークン自動リフレッシュ、DuckDB への保存ユーティリティ）
  - pipeline: 日次 ETL（差分取得・バックフィル・品質チェックの一括実行）
  - schema / audit: DuckDB スキーマ定義・初期化・監査ログ初期化
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定
  - stats / features: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research, feature_exploration: Momentum/Volatility/Value 等のファクター計算、将来リターン計算、IC（スピアマン相関）算出など
- config: .env / 環境変数の自動読み込みと設定アクセス（settings オブジェクト）
- strategy, execution, monitoring: （骨組みのモジュール。発注や監視ロジックの拡張想定）

---

## セットアップ手順

前提
- Python 3.9+（typing の一部表記に依存）
- システムに応じて virtualenv を推奨

1. リポジトリをクローン／配置（この README は src/ 配下のパッケージを想定しています）。

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（例）
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそれを利用してください）

4. 環境変数を設定
   プロジェクトルートに `.env` / `.env.local` を用意することで自動的に読み込まれます（設定無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   サンプル（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL で:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
   監査用 DB を別途初期化する場合:
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 環境変数（主要項目）

config.Settings 経由でアクセスされる項目（必須は NOTE）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token（get_id_token に使用）
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot Token（通知等で使用）
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

注意:
- Settings は .env を自動で読み込みます（プロジェクトルート判定は .git or pyproject.toml を基準）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要 API の例）

以下は代表的な利用例です。実運用ではログ設定や例外処理、トークン管理を適切に追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（J-Quants からデータ取得して保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema を実行済みならこちら
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に保有する銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 保存数}
```

4) ファクター計算（研究用）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
t = date(2024, 1, 31)
mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)
fwd = calc_forward_returns(conn, t)
# IC を計算する例（カラム名を合わせて使用）
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

5) Zスコア正規化
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

6) 市場カレンダーの更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

7) 監査ログテーブルの初期化（既存の DB に追加）
```python
from kabusys.data.audit import init_audit_schema
conn = schema.get_connection("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 開発用ヒント

- tests 等で自動 .env 読み込みを無効にしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- jquants_client の _RateLimiter は module-level の単純実装のため、複数プロセスから同時に呼ぶ際は外側でレート管理を行ってください。
- news_collector は RSS の XML を defusedxml でパースし、SSRF や Gzip Bomb 等を考慮した保護が行われています。外部 URL を扱うコードを差し替える場合はこれらの対策を維持してください。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - quality.py
      - calendar_management.py
      - audit.py
      - etl.py
      - features.py
      - stats.py
      - calendar_management.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      (戦略ロジック拡張ポイント)
    - execution/
      - __init__.py
      (発注ロジック拡張ポイント)
    - monitoring/
      - __init__.py

各モジュールは README 内の「主な機能」に記載の役割を持ちます。詳細実装は該当ファイルをご参照ください。

---

## 最後に

この README はコードベースに基づく概要・使い方のガイドです。実運用前に必ず以下を行ってください：

- .env に必要なシークレット（トークン・パスワード等）を安全に設定
- DuckDB スキーマ初期化と簡易 ETL をローカルで実行して動作確認
- Slack 等通知周りや kabu API の発注ロジックを本番で使う前に必ず Paper Trading 環境で検証

不明点や追加で README に載せたい利用シナリオがあれば教えてください。README を拡張して具体的な CLI/スケジューリング例（cron / systemd / Airflow 等）やデプロイ手順を追記できます。