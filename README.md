# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB を中心に、J-Quants からのデータ取得、ETL、品質チェック、ニュース収集、ファクター計算、監査ログなどを一貫して提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## 主要機能

- データ取得・保存
  - J-Quants API クライアント（株価日足、財務データ、JPX マーケットカレンダー）
  - 取得データを DuckDB に冪等（ON CONFLICT）で保存
  - API レート制御（120 req/min）、リトライ、トークン自動リフレッシュ

- ETL・データ基盤
  - 日次 ETL（calendar / prices / financials）の差分更新・バックフィル対応
  - データ品質チェック（欠損、スパイク、重複、日付整合性）
  - DuckDB 用スキーマ定義・初期化ユーティリティ

- ニュース収集
  - RSS フィードから記事取得・前処理・DB 保存（raw_news）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で冪等保存
  - SSRF 対策・サイズ制限・XML 安全パース

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（Audit）
  - シグナル → 発注 → 約定のトレーサビリティ用テーブル群
  - UUID ベースの冪等キー、UTC タイムスタンプの保存方針

---

## 必要要件

- Python 3.9+
- duckdb
- defusedxml

（プロジェクト用途に応じて urllib, logging, math など標準ライブラリを使用）

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# pip install -e .  # パッケージ配布用 setup/pyproject があれば
```

---

## 環境変数 / 設定

設定は実行時に環境変数、もしくはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます。  
（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）

主な環境変数（Settings により参照）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード。

- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)  
  kabu API のベース URL。

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン。

- SLACK_CHANNEL_ID (必須)  
  通知先の Slack チャンネル ID。

- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)  
  DuckDB ファイルパス。例: data/kabusys.duckdb

- SQLITE_PATH (任意, デフォルト: data/monitoring.db)  
  監視用 SQLite パス（用途により使用）。

- KABUSYS_ENV (任意, デフォルト: development)  
  有効値: development / paper_trading / live

- LOG_LEVEL (任意, デフォルト: INFO)  
  有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

`.env` のサンプル:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（基本）

1. 依存ライブラリをインストール
   - duckdb, defusedxml など

2. 環境変数を設定（`.env` をプロジェクトルートに配置）

3. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してテーブル群を作る
```

4. 監査ログスキーマ（必要に応じて）
```python
from kabusys.data import audit
# init_schema で得た conn を渡す
audit.init_audit_schema(conn, transactional=True)
```

---

## 使い方（主な API / ワークフロー例）

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 市場カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print("saved calendar records:", saved)
```

- ニュース収集ジョブを走らせる
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 抽出に使う有効な銘柄コードの集合を渡す（例: {'7203','6758',...}）
res = run_news_collection(conn, sources=None, known_codes={'7203', '6758'})
print(res)
```

- ファクター計算（リサーチ）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize
from datetime import date

# conn は DuckDB 接続、prices_daily/raw_financials が整備されていること
mom = calc_momentum(conn, date(2024, 1, 31))
vol = calc_volatility(conn, date(2024, 1, 31))
val = calc_value(conn, date(2024, 1, 31))
fwd = calc_forward_returns(conn, date(2024, 1, 31), horizons=[1,5,21])

# 例: ファクターと将来リターンで IC を計算
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")

# Z スコア正規化
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- J-Quants から生データを取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

- データ品質チェックを実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2024,1,31))
for i in issues:
    print(i)
```

---

## 自動 .env 読み込みの挙動

- パッケージ import 時にプロジェクトルート（`.git` または `pyproject.toml` を基準）を探索し、`.env` → `.env.local` の順で読み込みを試みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動読み込みを無効化するには、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

以下はコードベースの主要ディレクトリ構成（src 以下）です:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - news_collector.py      # RSS ニュース収集
    - schema.py              # DuckDB スキーマ定義・初期化
    - stats.py               # 統計ユーティリティ（zscore 等）
    - pipeline.py            # ETL パイプライン
    - features.py            # 特徴量インターフェース
    - calendar_management.py # 市場カレンダー管理
    - quality.py             # 品質チェック
    - audit.py               # 監査ログ初期化
    - etl.py                 # ETL 公開 API
  - research/
    - __init__.py
    - factor_research.py     # Momentum/Volatility/Value 等
    - feature_exploration.py # 将来リターン・IC・統計サマリ
  - strategy/                 # 戦略関連（骨組み）
  - execution/                # 発注・ブローカー連携（骨組み）
  - monitoring/               # 監視系（骨組み）

（README に記載のないテストや CLI があれば別途参照してください）

---

## 設計上の注意点 / ポリシー

- DuckDB を永続保管層として想定。初期化は idempotent（既存テーブルはスキップ）。
- J-Quants API 呼び出しはレート制御・リトライ・トークンリフレッシュを実装済み。429/408/5xx のリトライや Retry-After を尊重。
- データ品質チェックは Fail-Fast ではなく、問題を列挙して呼び出し元が判断できるように設計。
- ニュース収集は SSRF 対策、XML 攻撃対策、サイズ上限等を備える。
- すべてのタイムスタンプは原則 UTC で扱う（監査ログ等）。

---

## 参考 / 次のステップ

- 実運用する際は「live」環境設定・Slack 通知・発注モジュールの実装（kabu API 経由）・監査ログ運用ルールの整備が必要です。
- テスト用に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を併用し、環境依存を排したユニットテストを作成してください。

---

必要があれば、README に挙げた各 API の具体的な引数詳細やサンプルワークフロー（Docker / systemd タイマーでの定期実行例、CI/CD 用の注意点等）を追記します。どの部分を詳しく記述しましょうか？