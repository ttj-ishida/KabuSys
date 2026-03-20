# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
DuckDB をデータレイヤーに用い、J-Quants API から市場データ・財務データ・カレンダーを取得して ETL → 特徴量生成 → シグナル生成 → 発注監査ログまでのワークフローをサポートします。

以下はこのリポジトリの README.md（日本語）です。

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群を提供します。

- データ取得／保存（J-Quants API クライアント、ニュース RSS 収集、DuckDB スキーマ定義）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量（features）構築とシグナル生成（戦略ロジックの実装）
- マーケットカレンダー管理（営業日判定、next/prev）
- 発注・監査用スキーマ（orders/executions/trades/positions 等）
- 環境変数管理と設定（.env 自動読み込み）

設計上の特徴：
- ルックアヘッドバイアスを避けるため、target_date 時点の情報のみを利用する実装
- DuckDB に対する冪等保存（ON CONFLICT / INSERT … DO UPDATE / RETURNING など）
- ネットワーク／API 呼び出しに対する堅牢なリトライ・レート制御・SSRF 対策
- テスト容易性のためトークン注入や自動ロード抑止フラグを用意

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（token refresh、ページネーション、レートリミット、保存ユーティリティ）
  - save_daily_quotes / save_financial_statements / save_market_calendar 等の冪等保存関数

- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) で DB 初期化

- data/pipeline.py
  - 日次 ETL（run_daily_etl）と個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）

- data/news_collector.py
  - RSS 取得、記事前処理、raw_news / news_symbols への保存、SSRF・gzip・XML攻撃対策

- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job: カレンダーの夜間差分更新

- research/factor_research.py, feature_exploration.py
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算 / IC（Spearman）計算 / 統計サマリー

- strategy/feature_engineering.py
  - research で計算した raw ファクターを正規化・フィルタ適用して features テーブルに保存

- strategy/signal_generator.py
  - features と ai_scores を統合して final_score を算出し BUY/SELL シグナルを signals テーブルへ保存

- config.py
  - 環境変数の自動ロード（プロジェクトルートの .env / .env.local を優先）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
  - settings オブジェクト経由でアクセス可能

---

## 要求環境

- Python 3.10 以上（PEP 604 の union 型表記などを使用）
- 必要な Python パッケージ（代表例）
  - duckdb
  - defusedxml

（実運用ではその他ログ周り、Slack 連携、kabuステーション API クライアント等が別途必要になる可能性があります）

例（仮の最低依存インストール）:
```bash
python -m pip install "duckdb>=0.6" "defusedxml"
```

---

## セットアップ手順

1. リポジトリをクローンし、パッケージをインストール（開発環境向け）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m pip install -e .
   ```
   （setup.py / pyproject.toml がある場合はプロジェクトに応じたインストール方法を使用）

2. 必要パッケージをインストール
   ```bash
   python -m pip install duckdb defusedxml
   ```

3. 環境変数を準備
   - プロジェクトルートに `.env`（および開発環境では `.env.local`）を配置すると自動で読み込まれます。
   - 自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

   必須環境変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化（初回）
   Python REPL かスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   # あるいはファイルパスを直接指定
   # conn = init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（サンプル）

以下は主要なワークフロー（ETL → 特徴量 → シグナル生成）の最小実行例です。

1) DuckDB 初期化（上記参照）

2) 日次 ETL 実行
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量ビルド（features テーブル作成）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"built features for {count} symbols")
```

4) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
num_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"generated {num_signals} signals")
```

5) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コード集合
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 主要な設定項目（env）

config.Settings で取得する設定（主なもの）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment（development | paper_trading | live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

.env 例:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C00000000
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成

以下は src/kabusys 配下の主要ファイル構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py      — RSS ニュース収集・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — 統計ユーティリティ（z-score 等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー判定・更新ジョブ
    - audit.py               — 監査ログスキーマ（signal_events, order_requests, executions）
    - features.py            — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築
    - signal_generator.py    — シグナル生成ロジック
  - execution/               — 発注に関するモジュール（今後追加・実装）
  - monitoring/              — モニタリング用モジュール（今後追加・実装）

---

## 注意点 / 運用上のヒント

- 自動環境変数読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` / `.env.local` を自動で読み込みます。
  - テスト時や明示的に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DuckDB スキーマは冪等に作成されます。初回は init_schema() を呼び出してください。すでにテーブルが存在すれば何もしません。

- J-Quants API のレート制御やリトライは jquants_client が担います。大量取得やループ呼び出し時には _MIN_INTERVAL_SEC を考慮してください。

- シグナル生成は features / ai_scores / positions テーブルに依存します。実運用ではポジション管理と注文実行ロジックを確実に実装してから使用してください。

- ログとモニタリングは必須です。LOG_LEVEL を適切に設定し、ETLResult の to_dict() 等で運用ログを残すことを推奨します。

---

## 貢献・拡張

- execution 層（kabuステーション連携、ブローカラッパー）の実装
- ポートフォリオ最適化・リスク管理モジュールの追加
- AI スコア生成パイプラインの実装（ai_scores の投入）
- 品質チェックの拡充（data.quality モジュール）

---

この README はコードベースのコメントと API からまとめた概要です。より詳細な仕様（StrategyModel.md, DataPlatform.md, Research 文書等）がプロジェクト内にあればそちらも参照してください。質問や補足が必要でしたら、実行したいシナリオ（ETL 実行、シグナル生成、自動売買接続など）を教えてください。具体的な使用例やスクリプトを提案します。