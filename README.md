# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants や RSS 等からデータを収集して DuckDB に保存し、ETL（差分取得・品質チェック）、マーケットカレンダー管理、監査ログ（発注〜約定のトレース）などの基盤機能を提供します。

主な設計方針：
- API レート制限・リトライ・トークン自動リフレッシュに対応
- データ取得日時（fetched_at）を記録して Look‑ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT）で重複を排除
- RSS 収集は SSRF / XML Bomb / 大量レスポンス等の対策あり
- 品質チェック（欠損・重複・スパイク・日付不整合）を SQL で高速に実施

バージョン: 0.1.0

---

## 主な機能一覧

- 設定管理
  - .env/.env.local または環境変数を自動読み込み（プロジェクトルート基準）
  - 必須環境変数の集中管理（`kabusys.config.settings`）
- データ取得（J-Quants）
  - 日足 OHLCV（ページネーション対応）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - レート制限・リトライ・トークン自動更新対応
- ニュース収集
  - RSS フィード取得、テキスト前処理、記事ID生成（URL正規化+SHA-256）
  - SSRF / XML 脅威 / レスポンスサイズ制限対策
  - raw_news / news_symbols への冪等保存
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のDDL定義と初期化
  - 監査ログ用スキーマ（signal_events, order_requests, executions）
- ETL パイプライン
  - 差分取得（DB の最終取得日から必要範囲を自動算出）
  - backfill オプションで API の後出し修正を吸収
  - 品質チェック（quality モジュール）を統合
- カレンダー管理
  - 営業日判定、next/prev/trading_days 等のユーティリティ
  - 夜間バッチによるカレンダー差分更新
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出と報告

---

## 動作要件 / 依存

- Python 3.10 以上（typing の union 演算子 `|` を使用）
- 必要パッケージ（最小）:
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージを editable install する場合（プロジェクトが pip インストール可能な構成であれば）
# pip install -e .
```

標準ライブラリ（urllib, logging など）を広く使用しています。

---

## 環境変数 / 設定

自動読み込み:
- パッケージはソースファイルの位置から親ディレクトリを遡り、`.git` または `pyproject.toml` のあるディレクトリをプロジェクトルートとみなします。そのルートにある `.env` → `.env.local` を順に読み込みます（OS 環境変数を保護）。

自動読み込みを無効化する:
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを抑制します（テスト等で利用）。

代表的な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL      : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        : Slack Bot トークン（必須）
- SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : SQLite 用パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

設定参照例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## セットアップ手順

1. レポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境と依存のインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```

3. 環境変数を設定（`.env` または環境側で設定）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

4. DuckDB スキーマ初期化
   - デフォルトパスを使う場合（settings.duckdb_path に従う）:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema(":memory:")  # テスト用にメモリDB
   # またはファイルDB:
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

5. 監査ログテーブルを追加する場合:
   ```python
   from kabusys.data import audit
   audit.init_audit_schema(conn)  # 既存の conn に audit スキーマを追加
   ```

---

## 使い方（主要例）

- 日次 ETL（株価 / 財務 / カレンダー取得 + 品質チェック）
```python
from kabusys.data import schema, pipeline

# DB を初期化または接続
conn = schema.init_schema("data/kabusys.duckdb")

# ETL 実行（省略時は today）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data import schema, news_collector

conn = schema.init_schema("data/kabusys.duckdb")

# known_codes は銘柄候補セット（例: 上場銘柄の4桁コード集合）
known_codes = {"7203", "6758", "9984"}

results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- J-Quants の個別呼び出し例
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
from datetime import date

token = None  # 省略するとモジュール内キャッシュ+settings を使う
records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
# DuckDB 接続 conn を用意して
# jq.save_daily_quotes(conn, records)
```

- 品質チェックを個別実行
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

ログレベルは環境変数 `LOG_LEVEL` で制御できます（settings.log_level）。

---

## 主要モジュールとディレクトリ構成

リポジトリ（src 配下）の主なファイル:
```
src/
  kabusys/
    __init__.py
    config.py                    # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py          # J-Quants API クライアント + 保存ロジック
      news_collector.py          # RSS ニュース収集・前処理・保存
      schema.py                  # DuckDB スキーマ定義・初期化
      pipeline.py                # ETL パイプライン（差分取得・品質チェック統合）
      calendar_management.py     # 市場カレンダー更新・営業日ユーティリティ
      audit.py                   # 監査ログ（発注〜約定トレーサビリティ）
      quality.py                 # データ品質チェック
    strategy/
      __init__.py                # 戦略モジュール（将来的に戦略ロジックを配置）
    execution/
      __init__.py                # 発注/約定系（ブローカー接続等を実装）
    monitoring/
      __init__.py                # 監視/メトリクス集約用（未実装）
```

主要テーブル（DuckDB）例:
- Raw: raw_prices, raw_financials, raw_news, raw_executions
- Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature: features, ai_scores
- Execution: signals, signal_queue, orders, trades, positions, portfolio_performance
- Audit: signal_events, order_requests, executions

---

## 開発上の注意 / 補足

- API のレート制限やリトライ挙動は jquants_client に実装されています。実運用時は `KABUSYS_ENV`（paper_trading / live）に応じた動作確認を行ってください。
- ニュース収集では外部からの RSS を扱うため、SSRF, XML 脅威、圧縮爆弾（gzip）対策が組み込まれていますが、追加のセキュリティ対策（プロキシ、接続制限等）は運用ポリシーに従ってください。
- DuckDB のパスは settings で制御できます。バックアップやファイル排他に注意してください。
- strategy / execution / monitoring は拡張ポイントとして空のパッケージを用意しています。ここに戦略実装やブローカーインタフェース、監視フローを追加してください。

---

もし README に追加したい使用例（スケジューリング例、CI/CD、Slack 通知連携の詳細など）があれば内容に合わせて追記します。