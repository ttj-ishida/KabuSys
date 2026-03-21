# KabuSys — 日本株自動売買システム

軽量なリサーチ・データ基盤と戦略層を備えた日本株向け自動売買フレームワークです。  
データ取得（J-Quants API）→ ETL（DuckDB）→ ファクター計算 → シグナル生成 → 発注監査の各レイヤーを分離して実装しています。

主な設計方針
- レイヤードアーキテクチャ（Raw / Processed / Feature / Execution）
- ルックアヘッドバイアス防止（計算は target_date 時点のデータのみを使用）
- DuckDB を中心としたローカル DB（高速なクロスセクション集計向け）
- 冪等性（ON CONFLICT / トランザクションを利用）
- API のレート制御・リトライ・トークン自動更新

---

## 機能一覧

- データ収集
  - J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー）
  - RSS ベースのニュース収集（トラッキングパラメータ除去・SSRF 対策）
- ETL / データ基盤
  - DuckDB スキーマ初期化（init_schema）
  - 日次差分 ETL（run_daily_etl）: 市場カレンダー、株価、財務を差分取得して保存
  - 品質チェック統合（quality モジュール経由）
- リサーチ / ファクター
  - Momentum / Volatility / Value ファクター計算（research/factor_research）
  - 将来リターン・IC・統計サマリー（research/feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats）
- 特徴量 & シグナル生成（strategy）
  - features を構築する処理（strategy.feature_engineering.build_features）
  - 正規化済みファクター＋AIスコアを統合してシグナルを生成（strategy.signal_generator.generate_signals）
  - BUY/SELL（エグジット）判定と signals テーブルへの保存（冪等）
- 発注監査 / 実行層（スキーマ定義および監査ログ）
  - signal_events / order_requests / executions 等の監査テーブル設計
- 設定管理
  - .env、自動読み込み・保護、必須 env の取り扱い（kabusys.config）

---

## 必要条件 / 依存関係

- Python 3.10+（型ヒントで | 型等を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
  - （実運用では requests 等の追加がある場合あり）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージとして配布されている場合:
# pip install -e .
```

---

## 環境変数（主なもの）

設定は .env または OS 環境変数から読み込まれます（kabusys.config が自動でプロジェクトルートの .env / .env.local を読み込みます）。
自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（利用する機能に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（execution 層向け）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/...)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

設定取得例（Python）:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.is_live)
```

---

## セットアップ手順（ローカル実行・開発向け）

1. リポジトリをクローンして仮想環境を用意
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   # 必要に応じて開発用依存をインストール
   ```

2. 環境変数を準備
   - プロジェクトルートに `.env`（または `.env.local`）を作成。例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

3. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   もしくはインメモリでの検証:
   ```python
   conn = init_schema(":memory:")
   ```

---

## 使い方（主要なワークフロー例）

以下は Python REPL / スクリプトで利用する最小例です。

1) データベースの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（市場カレンダー・株価・財務の差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

3) 特徴量の構築（features テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, target_date=date.today())
print("features updated:", count)
```

4) シグナル生成（signals テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import generate_signals
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals written:", n)
```

5) ニュース収集（RSS → raw_news、news_symbols）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードセット（抽出に使用）
result = run_news_collection(conn, known_codes={"7203","6758"})
print(result)  # {source_name: saved_count}
```

6) J-Quants API の低レベル呼び出し（例）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使って自動取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意: 実運用ではエラーハンドリングやログ出力、トークンの保護、rate limit を考慮してください。jquants_client は自動で rate limit・リトライ処理を実装しています。

---

## よく使う API（モジュール一覧と用途）

- kabusys.config
  - settings: 環境設定アクセサ（必須 env の検証・パス取得等）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, save_*（DuckDB 保存）
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.data.stats
  - zscore_normalize
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features, generate_signals

---

## ディレクトリ構成（主要ファイル）

以下はコードベースの主要ファイル／モジュール構成の概観です（src/kabusys 配下）。

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
    - (その他: quality, etc. が想定される)
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
  - monitoring/  (監視用ロジック等: 省略されているが __all__ に含まれる可能性あり)

（README に示したのは抜粋です。実際のリポジトリにはさらにユーティリティ・ドキュメントが含まれることがあります。）

---

## 開発・テストに関するヒント

- 自動 .env ロードを無効にする:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  単体テストで環境変数の影響を受けないようにしたい場合に便利です。

- DuckDB のインメモリ DB を使うと CI / 単体テストが高速になります:
  ```python
  conn = init_schema(":memory:")
  ```

- news_collector は外部ネットワークアクセスを伴うため、ユニットテストでは fetch_rss / _urlopen をモックしてください。

---

## 注意事項

- 本コードベースは「リサーチ／バックテスト」「データ基盤」および「戦略生成」ロジックを含みますが、実際のマネーを扱うライブ運用には追加の安全策（外部監査、リスク管理、接続のセキュリティ硬化、証券会社 API の堅牢な実装）が必要です。
- 環境変数やトークンは安全に管理してください（コミットしないこと）。
- J-Quants API 利用時は提供側の利用規約・レート制限を守ってください。

---

必要があれば、README に以下を追加で記載できます:
- .env.example のテンプレート
- 開発依存パッケージの requirements-dev.txt
- CI 用の簡単なテスト実行例
- スキーマ / 各テーブルの詳細な説明（DataSchema.md 相当の抜粋）

どの項目を優先して追記しますか？