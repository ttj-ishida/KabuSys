# KabuSys

日本株向け自動売買基盤（KabuSys）の軽量実装モック。  
データ取得（J-Quants / RSS）、データベース（DuckDB）スキーマ管理、ETLパイプライン、品質チェック、監査ログ等の基盤機能を提供します。戦略層・実行層・モニタリング層のフレームワークを備え、実運用（live）／ペーパートレード（paper_trading）／開発（development）から切り替えて利用できます。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動ロード（無効化可）
  - 必須変数の取得と検証（env 値チェック）
- J-Quants API クライアント（jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）とリトライ（指数バックオフ）、401時の自動トークンリフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - fetched_at による取得時刻トレース（Look-ahead bias 対策）
- ニュース収集（news_collector）
  - RSS フィード取得・前処理（URL除去・空白正規化）
  - URL 正規化と SHA-256（先頭32文字）による記事ID生成で冪等性保証
  - SSRF 対策、gzip サイズ上限、XML パースの堅牢化（defusedxml）
  - DuckDB への一括挿入（INSERT ... RETURNING）と銘柄コード抽出・紐付け
- DuckDB スキーマ管理（schema / audit）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - インデックス作成、監査ログ（signal / order / execution のトレーサビリティ）
- ETL パイプライン（pipeline）
  - 差分更新（最終取得日からの差分・バックフィル）
  - カレンダー先読み、品質チェックの統合（quality モジュール）
  - run_daily_etl による日次 ETL 実行（個別ジョブも提供）
- マーケットカレンダー管理（calendar_management）
  - 市場の営業日判定（is_trading_day / next_trading_day / get_trading_days 等）
  - 夜間バッチ更新ジョブ（calendar_update_job）
- データ品質チェック（quality）
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返す）
  - run_all_checks による一括実行
- 監査ログ初期化（audit）
  - 独立した監査用スキーマの初期化（UTC タイムゾーン固定可）

注: strategy / execution / monitoring パッケージはインターフェースを想定した空のモジュール（拡張ポイント）として用意されています。

---

## セットアップ手順

前提:
- Python 3.9+（型注釈に union 型や typing の機能を使用）
- ネットワークアクセス（J-Quants API / RSS）

1. リポジトリをクローン、仮想環境を作成
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必須（最低限）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 実プロジェクトでは requirements.txt / pyproject.toml に依存を記載してください。

3. 環境変数を設定
   - プロジェクトルートに `.env` を置くか、OS 環境変数を設定します。
   - 自動読み込みはデフォルトで有効。テスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabu API のパスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - 任意:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（簡単なコード例）

以下は主要なユーティリティの利用例です。実行はプロジェクトルートから行ってください。

1. DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを作成して全テーブルを作成
```

2. J-Quants から株価を取得して保存（差分ETLの個別利用）
```python
from datetime import date
import duckdb
from kabusys.data import pipeline

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を省略すると今日が対象
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. RSS ニュース収集と銘柄紐付け
```python
from kabusys.data import news_collector, schema
import duckdb

conn = schema.get_connection("data/kabusys.duckdb")
# 既知銘柄コードセット（例: 事前に取得した上場銘柄コード集合）
known_codes = {"7203", "6758", "9984"}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

4. 監査スキーマ初期化（別 DB でも良い）
```python
from kabusys.data import audit
conn = audit.init_audit_db("data/audit.duckdb")
```

5. 品質チェック実行
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

6. J-Quants API 直接利用（トークン取得 / データ取得）
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使って取得
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意点:
- jquants_client は内部でレート制御・再試行・トークン自動更新を行います。大量リクエストを行う場合は設計方針を守ってください（120 req/min）。
- news_collector は SSRF・XML bomb 等の脅威に配慮した実装です。外部 URL の扱いは十分注意してください。

---

## ディレクトリ構成

コードベースの主要ファイル／モジュール構成は次の通りです（簡易表示）。

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py  -- J-Quants API クライアント（取得 / 保存 / レート制御）
    - news_collector.py  -- RSS 収集・前処理・DB保存・銘柄抽出
    - schema.py          -- DuckDB スキーマ定義・初期化
    - pipeline.py        -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py -- マーケットカレンダー管理（営業日判定 / 更新ジョブ）
    - audit.py           -- 監査ログスキーマ（signal / order / execution）
    - quality.py         -- データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py        -- 戦略層の拡張ポイント（現状空）
  - execution/
    - __init__.py        -- 発注・ブローカ連携の拡張ポイント（現状空）
  - monitoring/
    - __init__.py        -- モニタリング / アラートの拡張ポイント（現状空）

---

## 実運用上の注意 / 設計メモ

- レート制限: J-Quants は 120 req/min を想定。クライアントは固定間隔スロットリングで制御していますが、利用時は全体的な呼び出し頻度を考慮してください。
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE / DO NOTHING を利用して冪等化しています。外部からの直接書き込みがあるケースは注意。
- トレーサビリティ: audit スキーマによりシグナル→発注→約定の連鎖を UUID ベースで追跡できます。監査ログは基本的に削除しない方針です。
- 環境: .env の自動読み込みはプロジェクトルート検出（.git または pyproject.toml）を基に行います。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- セキュリティ: news_collector は SSRF 対策や XML パース対策を実装していますが、外部リソースの取り扱いでは常に注意してください。

---

## 今後の拡張ポイント

- strategy 層: 特徴量取得・ポートフォリオ最適化・ランキング戦略の実装
- execution 層: 実際の証券会社 API（kabuステーション等）との接続、注文再送・約定コールバック処理
- monitoring 層: Prometheus / Grafana / Slack 通知等の統合
- テスト: ユニットテスト、統合テスト、モックによるネットワーク依存の切り離し
- ドキュメント: API リファレンス、DataPlatform.md / DataSchema.md のリンクと詳細

---

必要であれば、README に含めるサンプル .env.example のテンプレートや、Docker / CI 環境での起動手順（docker-compose 等）の雛形も作成します。どの情報を優先して追加しますか？