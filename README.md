# KabuSys

日本株向け自動売買・データプラットフォームのライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、DuckDB スキーマ、ニュース収集、品質チェック、ファクター計算（リサーチ用）、監査ログなど、取引システムと研究環境に必要な機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（Feature一覧）

- データ取得・保存
  - J-Quants API クライアント（rate limit / retry / token refresh 対応）
  - 日足（OHLCV）、財務データ、JPX マーケットカレンダー取得
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分取得・バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- データスキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層の DuckDB スキーマ定義と初期化
- ニュース収集
  - RSS フィードの安全な取得（SSRF対策、gzip上限、XML攻撃対策）
  - 記事IDは正規化URLのハッシュで冪等性を担保
  - 記事と銘柄コードの紐付け（news_symbols）
- 品質チェック
  - 欠損データ、スパイク（急騰/急落）、重複、日付不整合を検出
  - QualityIssue オブジェクトで報告
- リサーチ／特徴量
  - モメンタム、ボラティリティ、バリュー等のファクター計算（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（Spearman ρ）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルによる完全なトレーサビリティ設計

---

## セットアップ手順

前提
- Python 3.10 以上（ソース内での型注釈に `|` を使用）
- DuckDB（Python パッケージ経由で使用）
- ネットワークアクセス（J-Quants、RSS 取得等）

推奨インストール手順（プロジェクトルートで実行）:

1. 仮想環境を作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要ライブラリをインストール  
   （プロジェクトに requirements.txt がある場合はそちらを利用してください。以下は主要な依存例）
   ```
   pip install duckdb defusedxml
   ```

3. 環境変数の設定  
   プロジェクトルートの `.env` または `.env.local` に必要な値を設定できます。自動読み込みは既定で有効です（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

   必須環境変数（コードで _require されるもの）
   - JQUANTS_REFRESH_TOKEN（J-Quants のリフレッシュトークン）
   - KABU_API_PASSWORD（kabu ステーション API パスワード）
   - SLACK_BOT_TOKEN（Slack 通知用 Bot トークン）
   - SLACK_CHANNEL_ID（Slack チャンネル ID）

   推奨/任意
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

   例 `.env`（実運用は秘匿保持してください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な API と実行例）

以下は基本的な使い方例です。Python スクリプトからインポートして利用します。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# メモリ DB の場合: ":memory:"
```

2) 日次 ETL を実行（J-Quants 認証トークンは settings が自動取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 抽出する有効銘柄コードの集合
known_codes = {"7203", "6758", "9432"}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

4) リサーチ用ファクター計算の例
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
d = date(2024, 1, 4)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
fwd = calc_forward_returns(conn, d)
# IC を計算する例: factor_records と forward_records を code でマージして渡す
```

5) J-Quants API の直接利用（トークン取得やフェッチ）
```python
from kabusys.data import jquants_client as jq

# id_token の取得（settings.jquants_refresh_token を使うので通常は省略可能）
id_token = jq.get_id_token()

# 日足取得（ページネーション対応）
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,12,31))
```

6) 品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

注意:
- settings.env を `live` にすると is_live フラグが True になるため、実際の発注等を行う実装を組み合わせる際は注意してください（本リポジトリには発注実装のスケルトンが含まれますが、実運用前に充分なレビュー・テストを行ってください）。
- 自動で .env をプロジェクトルート（.git または pyproject.toml を基準）から読み込みます。テスト時には環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます。

---

## よく使うモジュール一覧（短い説明）

- kabusys.config
  - 環境変数 / .env の読み込みと Settings オブジェクト提供
- kabusys.data.jquants_client
  - J-Quants API クライアント（取得 / 保存ユーティリティ含む）
- kabusys.data.schema
  - DuckDB スキーマ定義と init_schema / get_connection
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - RSSフェッチ、raw_news 保存、銘柄抽出、run_news_collection
- kabusys.data.quality
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
- kabusys.research.factor_research
  - calc_momentum, calc_volatility, calc_value
- kabusys.research.feature_exploration
  - calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize（Z スコア正規化）

---

## ディレクトリ構成

リポジトリ内の主要ファイル／モジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/                (発注/実行関連のパッケージ用ディレクトリ)
    - strategy/                 (戦略実装用ディレクトリ)
    - monitoring/               (モニタリング用)
    - data/
      - __init__.py
      - jquants_client.py       (J-Quants API クライアント)
      - news_collector.py       (RSS 収集・保存)
      - schema.py               (DuckDB スキーマ定義 / init)
      - pipeline.py             (ETL パイプライン)
      - etl.py                  (ETL 公開インターフェース)
      - features.py             (特徴量ユーティリティ公開)
      - calendar_management.py  (マーケットカレンダー管理)
      - audit.py                (監査ログスキーマ)
      - quality.py              (品質チェック)
      - stats.py                (統計ユーティリティ)
    - research/
      - __init__.py
      - feature_exploration.py  (将来リターン・IC・summary)
      - factor_research.py      (momentum / volatility / value)
    - strategy/
    - execution/
    - monitoring/

（上記は現状の主要ファイルを抜粋した構成です。プロジェクトに合わせて拡張してください。）

---

## 開発・運用上の注意点

- DuckDB の SQL 構文や制約に依存するため、DuckDB のバージョンによって動作差異が生じる可能性があります（特に外部キーや ON DELETE の挙動など）。実運用では DuckDB の互換性を確認してください。
- J-Quants API のレート制限やエラーコード（401/429/5xx）に対応した実装を含みますが、実運用では API ポリシーに従い、適切なリトライ／監視を行ってください。
- ニュース収集は外部 URL を扱うため SSRF・XML攻撃・巨大ペイロード対策を実装していますが、運用時にはネットワーク ACL やプロキシなどの追加対策も検討してください。
- 本ライブラリは研究用途から実運用までの基盤を提供しますが、実際の資金を動かす場合は十分なテスト、監査、リスク管理（取引制限、ポジション管理、異常時のフェイルセーフ）を必ず組み込んでください。
- 環境変数やトークンは厳重に管理してください。公開リポジトリや共有環境にハードコーディングしないでください。

---

もし README に含めたい追加のセクション（例: CI/CD、デプロイ手順、詳しい設定例、API モックの方法、サンプル戦略）や、実際に使うためのサンプルスクリプトを希望される場合は教えてください。必要に応じて追記します。