# KabuSys

日本株向けの自動売買基盤ライブラリ (KabuSys)。  
市場データ取得、ETL、ファクター計算、特徴量生成、シグナル生成、ニュース収集、監査用スキーマなどを含むモジュール群を提供します。

## プロジェクト概要
KabuSys は以下の目的で設計されています。

- J-Quants API から株価・財務・カレンダー等のデータを取得して DuckDB に保存する ETL パイプライン
- 研究用ファクター（Momentum / Volatility / Value など）の計算（research 層）
- 特徴量の正規化・統合（strategy 層の前処理）
- 戦略シグナル（BUY / SELL）の算出（strategy 層）
- RSS ニュース収集と銘柄紐付け（news collector）
- 発注 / 監査用スキーマ（execution / audit）
- 冪等性・トレーサビリティ・レート制限・エラーハンドリングに配慮した実装

設計方針の要点:
- ルックアヘッドバイアス防止のため、常に target_date 時点までの情報のみを使用
- DuckDB をローカル DB として利用（スキーマ定義・初期化機能あり）
- 冪等 (idempotent) な DB 書き込み（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）
- 外部依存は最小限（標準ライブラリ + 必要なライブラリ: duckdb, defusedxml など）

---

## 主な機能一覧
- データ取得
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - レート制限（120 req/min）、リトライ、トークン自動リフレッシュ
- ETL パイプライン
  - 差分取得・バックフィル・品質チェックを含む run_daily_etl
- データスキーマ
  - DuckDB 用スキーマ定義と初期化（raw / processed / feature / execution 層）
- 研究用ファクター計算
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- 特徴量生成
  - build_features: ファクターを統合・Zスコア正規化・クリップして features テーブルへ保存
- シグナル生成
  - generate_signals: features + ai_scores を統合して final_score を計算、BUY/SELL シグナルを作成
- ニュース収集
  - RSS フィード取得、テキスト前処理、記事ID生成（URL 正規化 + SHA-256）、raw_news 保存、銘柄抽出 / 紐付け
  - SSRF 対策、XML 攻撃対策、応答サイズ制限
- カレンダー管理
  - market_calendar の差分更新、営業日判定ヘルパー (is_trading_day / next_trading_day / prev_trading_day / get_trading_days)
- 統計ユーティリティ
  - zscore_normalize（クロスセクション Z スコア正規化）

---

## 動作要件
- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS）

（実運用では仮想環境を推奨します）

---

## インストール（開発時）
リポジトリルートで:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install duckdb defusedxml
# 開発用にソースを editable install する場合:
pip install -e .
```

必要な追加パッケージがあればプロジェクトの requirements.txt に追記してください。

---

## 環境変数 / .env
自動的にプロジェクトルートの `.env` / `.env.local` を読み込む仕組みがあります（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

必須環境変数（config.Settings で参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 bot token
- SLACK_CHANNEL_ID — Slack channel ID

その他（省略可能、デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live; default: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL; default: INFO)

例 (.env):

```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（初期化）
1. 環境変数 (.env) を作成
2. DuckDB スキーマ初期化

Python REPL またはスクリプトで:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env の DUCKDB_PATH に対応
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

init_schema は必要なディレクトリを自動作成し、テーブル・インデックスを作成します（冪等）。

---

## 使い方（主要ワークフロー例）

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）:

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)  # 初回のみ init_schema
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量をビルドして features テーブルへ保存:

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print("features upserted:", count)
```

- シグナル生成（features + ai_scores → signals）:

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema(settings.duckdb_path)
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals written:", total)
```

- ニュース収集ジョブの実行:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema(settings.duckdb_path)
# known_codes: 抽出時に有効とみなす銘柄コードのセットを渡すと銘柄紐付けが行われる
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(results)
```

- カレンダー更新ジョブ:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意: 上記関数はエラーハンドリングを含んでおり、失敗したステップはログに出力され戻り値や ETLResult に記録されます。

---

## API/モジュール概要
- kabusys.config
  - settings: 環境変数読み込みとアクセス用プロパティ
  - 自動 .env ロード、必須変数チェック
- kabusys.data
  - jquants_client.py: J-Quants API クライアント、保存関数（save_*）
  - schema.py: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py: ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
  - news_collector.py: RSS 取得・前処理・保存・銘柄抽出
  - calendar_management.py: market_calendar 更新・営業日ユーティリティ
  - stats.py: zscore_normalize
  - features.py: zscore_normalize の再エクスポート
  - audit.py: 監査トレーサビリティ用 DDL（signal_events, order_requests, executions 等）
- kabusys.research
  - factor_research.py: calc_momentum / calc_volatility / calc_value
  - feature_exploration.py: calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - feature_engineering.py: build_features（Zスコア正規化・ユニバースフィルタ・アップサート）
  - signal_generator.py: generate_signals（スコア計算・BUY/SELL 生成・SELL 優先）
- kabusys.execution
  - 発注層（現在 __init__ のみ。実装は別モジュールで行う想定）
- kabusys.monitoring
  - 監視・メトリクス関連（export はされているが実装はプロジェクトに応じて拡張）

---

## ディレクトリ構成（抜粋）
ルートの `src/kabusys` 配下に主要モジュールがあります。代表的な構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
      - ...（quality モジュール等が想定されます）
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/
      - (監視関連モジュール)

---

## 運用上の注意 / ベストプラクティス
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化するとテストの再現性が向上します。
- J-Quants API のレート制限（120 req/min）に従ってください。jquants_client は内部で簡易 RateLimiter を実装していますが、運用時は呼び出し頻度に注意してください。
- DB 初期化は一度行えば十分です。init_schema は冪等です。
- シグナル生成では Bear レジーム判定やストップロス等のロジックが含まれますが、実際の発注は execution 層と連携して慎重に実装してください（live 環境では必ず紙上検証・段階的ロールアウトを行ってください）。
- ニュース収集では外部 RSS の取り扱いに注意（SSRF 保護、XML 攻撃対策、サイズ制限 を実装済み）。

---

## ログ / デバッグ
- ログ出力は標準的な logging ライブラリを利用。`LOG_LEVEL` 環境変数で制御できます。
- モジュールは重要な操作で info/debug/warning/error を出力するため、問題解析にログを活用してください。

---

## 今後の拡張案（参考）
- execution 層の broker API 実装（kabuステーション等）と監査ログの連携
- AI スコア生成・外部モデルとの連携（ai_scores テーブルの producer）
- Web UI / ダッシュボードによる運用監視
- テストカバレッジ拡充と CI パイプライン

---

この README はコードベースから主要な機能・使い方・初期化手順を抜粋して記載しています。さらに詳しい仕様（StrategyModel.md / DataPlatform.md 等）や運用手順はプロジェクト内の設計ドキュメントを参照してください。質問や README の追加改善希望があればお知らせください。