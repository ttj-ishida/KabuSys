# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。データ取得（J‑Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査/スキーマ管理などを一貫して提供します。

主な設計方針：
- DuckDB を中心としたローカル DB にデータを蓄積（冪等性を考慮）
- ルックアヘッドバイアス防止のため、常に target_date 時点のデータのみを使用
- 発注 / 実行層や外部ブローカーには直接依存しない（execution 層の拡張を想定）
- 外部依存は最小限（例: duckdb, defusedxml 等）

バージョン: 0.1.0

---

## 機能一覧

- 環境・設定管理
  - .env または環境変数から設定を自動読込（プロジェクトルート検出）
  - 必須設定の検証（未設定時はエラー）

- データ取得（J‑Quants API クライアント）
  - 株価日足（ページネーション対応）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - レート制限管理・リトライ・トークン自動更新・fetched_at 記録

- データ保存 / スキーマ管理
  - DuckDB のスキーマ初期化（init_schema）
  - 生データ / 処理済みデータ / 特徴量 / 実行（監査含む）レイヤを定義
  - 各種テーブルは冪等に保存（ON CONFLICT / トランザクション）

- ETL パイプライン
  - 日次差分 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル機能

- 研究系ユーティリティ
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ

- 戦略層
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals）: ファクター + AI スコア統合、BUY/SELL 判定、Bear フィルタ、エグジット判定

- ニュース収集
  - RSS フィード取得（SSRF/サイズ/圧縮/XMLの安全対策）
  - 記事の正規化・ID生成（URL 正規化 + SHA256）
  - raw_news / news_symbols への冪等保存、銘柄抽出（4 桁コード）

- マーケットカレンダー管理
  - 営業日の判定、next/prev_trading_day、範囲の営業日取得
  - JPX カレンダー更新ジョブ（calendar_update_job）

- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブル定義（UUID ベースのトレース）

---

## セットアップ手順

必要条件
- Python 3.10+（ソース内で | 型注釈を使用）
- duckdb
- defusedxml

例（仮想環境推奨）:

1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. インストール
   - pip install -e .    # パッケージを editable インストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt/pyproject があればそちらを使用してください）

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（最低限これらを設定してください）:
- JQUANTS_REFRESH_TOKEN  — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API パスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（使用する場合）
- SLACK_CHANNEL_ID       — Slack チャネル ID

任意/デフォルト（未設定時は下記デフォルト）:
- KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

注意: Settings は実行時に環境変数を要求するプロパティを持つため、未設定だと ValueError が発生します。

---

## 使い方（主要な例）

以下は最小限の実行例例です。実際の運用ではログ設定やエラーハンドリングを追加してください。

1) DuckDB スキーマ初期化

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（J‑Quants トークンは settings から取得されます）

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

3) 特徴量を計算して features テーブルへ保存

```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, target_date=date(2024, 1, 1))
print(f"features upserted: {n}")
```

4) シグナル生成（BUY / SELL を signals テーブルへ書き込む）

```python
from datetime import date
from kabusys.strategy import generate_signals

count = generate_signals(conn, target_date=date(2024, 1, 1))
print(f"signals written: {count}")
```

5) ニュース収集と銘柄紐付け

```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 既知の銘柄コードセット（抽出時に照合）
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) カレンダー操作（例: 翌営業日取得）

```python
from datetime import date
from kabusys.data.calendar_management import next_trading_day

d = next_trading_day(conn, date.today())
print(d)
```

---

## よく使う API（関数・モジュール一覧）

- kabusys.config
  - settings: 環境変数から参照する設定オブジェクト
- kabusys.data.schema
  - init_schema(db_path) → DuckDB 接続（スキーマ作成）
  - get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection / extract_stock_codes
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=0.6, weights=None)

---

## ディレクトリ構成（主要ファイル）

概要（src/kabusys/...）:

- __init__.py
- config.py                          — 環境変数 / Settings
- data/
  - __init__.py
  - jquants_client.py                — J‑Quants API クライアント（取得 + 保存）
  - news_collector.py                — RSS 収集・前処理・保存・銘柄抽出
  - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
  - schema.py                        — DuckDB スキーマ定義と初期化（init_schema）
  - stats.py                         — 統計ユーティリティ（zscore_normalize）
  - features.py                      — features の公開インターフェース（再エクスポート）
  - calendar_management.py           — マーケットカレンダー管理
  - audit.py                         — 監査ログ用テーブル定義
- research/
  - __init__.py
  - factor_research.py               — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py           — 将来リターン / IC / サマリ
- strategy/
  - __init__.py
  - feature_engineering.py           — build_features（正規化・ユニバースフィルタ等）
  - signal_generator.py              — generate_signals（最終スコア・BUY/SELL 判定）
- execution/                          — 発注・実行層（拡張想定）
- monitoring/                         — 監視・通知（拡張想定）

（上記は主要モジュールの抜粋です。詳細はソースコード内の docstring を参照してください。）

---

## 開発時の注意・運用メモ

- 環境変数の自動読み込み
  - モジュール import 時にプロジェクトルートを探索し `.env` / `.env.local` を自動で読み込みます。
  - テスト時や特殊な起動で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DuckDB スキーマは冪等に作成されます。既存データを消したくない場合は init_schema を繰り返し実行しても安全です。

- J‑Quants API のレート制限（120 req/min）に合わせたスロットリング／リトライを組み込んでいますが、運用時は API 利用規約に従ってください。

- ニュース収集では SSRF 対策や XML パースのハードニング（defusedxml）を行っています。外部フィードを追加する際は信頼できるソースを優先してください。

- シグナル生成は features / ai_scores / positions に依存します。生成された signals は発注層（execution）で消費される想定です。現在の実装は発注 API への直接送信は含んでいません。

---

## ライセンス / コントリビュート

（このテンプレートにはライセンス情報は含まれていません。実運用や公開の前に適切なライセンスファイルを追加してください。）

貢献や改善提案は PR / Issue にて受け付けてください。コード内の docstring を参考にユニットテストや型チェック（mypy）を整備すると良いです。

---

README の内容に追加したい具体的な実行スクリプト例や CI/CD、運用手順（cron ジョブや systemd タイマー等）があれば教えてください。必要に応じてサンプル run scripts も作成します。