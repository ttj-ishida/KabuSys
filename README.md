# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリセットです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・実行レイヤーまでを含む設計になっています。

この README ではプロジェクト概要、主な機能、セットアップ手順、簡単な使い方、ディレクトリ構成を記載します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの市場データ・財務データ・マーケットカレンダーの取得（レート制限とリトライ対応）
- DuckDB を用いたデータベーススキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（Momentum / Volatility / Value 等）と Z スコア正規化
- 戦略用特徴量作成（features テーブルへの保存）とシグナル生成（signals テーブル）
- RSS ベースのニュース収集と記事→銘柄マッチング
- 発注／監査ログ用スキーマ（発注トレースのための監査テーブル）
- 環境変数／設定管理（.env 自動読み込み機能）

設計上のポイント：

- ルックアヘッドバイアスを避けるため、計算は target_date 時点の利用可能データのみを使用
- DuckDB を中核にし、SQL と Python の組合せで高速な集計を実現
- 外部依存は必要最小限（例: duckdb、defusedxml 等）で、テスト注入しやすい設計

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env / 環境変数の自動ロード（プロジェクトルート判定）、必須変数取得ユーティリティ
- kabusys.data.jquants_client
  - J-Quants API クライアント（ページネーション、リトライ、トークン自動リフレッシュ）
  - データ保存ユーティリティ（raw_prices / raw_financials / market_calendar などへ冪等保存）
- kabusys.data.schema
  - DuckDB 用のスキーマ定義と init_schema(db_path) による初期化
- kabusys.data.pipeline
  - 差分 ETL（run_daily_etl 等）、市場カレンダー更新、価格・財務データ取得のラッパー
- kabusys.data.news_collector
  - RSS 取得、前処理、raw_news への冪等保存、記事 → 銘柄紐付け
- kabusys.research
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - 解析ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）
- kabusys.strategy
  - build_features(conn, target_date)：特徴量の正規化と features へ保存
  - generate_signals(conn, target_date, ...)：features / ai_scores / positions を用いて signals を生成
- kabusys.data.stats
  - zscore_normalize：クロスセクションの Z スコア正規化
- kabusys.data.calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job など
- kabusys.data.audit
  - 監査ログ用テーブル定義（signal_events / order_requests / executions など）

---

## セットアップ手順

前提：Python 3.9+（型ヒントで | を用いているため少なくとも 3.10 を推奨）／pip

1. レポジトリをチェックアウト／クローン
   - 例: git clone <repository_url>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows では .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用）

   主要な依存例：
   - duckdb（オンディスク DB）
   - defusedxml（RSS XML の安全パース）
   - その他は用途に応じて（例: requests 等を追加しても良い）

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込みます（※自動読み込みは既定で有効）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   必須環境変数（コード内で _require() が使用されているもの）：
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabu ステーション API 用パスワード
   - SLACK_BOT_TOKEN : Slack 通知用トークン
   - SLACK_CHANNEL_ID : Slack チャネル ID

   任意／デフォルトあり：
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development|paper_trading|live、デフォルト development)
   - LOG_LEVEL (DEBUG|INFO|...、デフォルト INFO)

   .env 例（.env.example を参照して作成してください）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（DuckDB スキーマ作成）
   - Python REPL かスクリプトで:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を渡すとインメモリ DB で動作します（テスト用）。

---

## 使い方（簡単なサンプル）

以下は主要なワークフローのサンプルコードです。実運用ではログ設定・エラーハンドリング・スケジューリング等を追加してください。

1) DuckDB 初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（市場カレンダー・株価・財務データの取得）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を省略すると今日（営業日に調整）を対象に実行
print(result.to_dict())
```

3) 研究ファクター → 特徴量の生成（features テーブルへ保存）
```
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2025, 1, 31))
print("upserted features:", count)
```

4) シグナル生成（signals テーブルへ書き込み）
```
from kabusys.strategy import generate_signals
from datetime import date
total = generate_signals(conn, date(2025, 1, 31))
print("signals written:", total)
```

5) ニュース収集（RSS）と銘柄紐付け
```
from kabusys.data.news_collector import run_news_collection
# known_codes は既知の銘柄コードセット（例: all listed codes）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count}
```

6) J-Quants の生データフェッチを直接利用（例）
```
from kabusys.data import jquants_client as jq
rows = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
saved = jq.save_daily_quotes(conn, rows)
```

注意点：
- generate_signals は features / ai_scores / positions を参照します。事前に features を作成し、ai_scores／positions が必要であれば適宜投入してください。
- run_daily_etl は品質チェック（quality モジュール）を呼ぶため、品質チェックの結果が ETLResult に含まれます（致命的エラーは flags）。

---

## 設計・動作上の注意

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。CWD に依存しないよう設計されています。
- 自動ロードの優先順位: OS 環境変数 > .env.local > .env（.env.local は .env を上書き可能）
- J-Quants API はレート制限（120 req/min）を厳守するよう内部でスロットリングしています。
- API の 401 返却時は ID トークンを自動リフレッシュし 1 回だけリトライします。
- DB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装されています。
- news_collector は SSRF や XML Bomb 等を考慮して実装されています（スキーム検証、最大受信バイト数、defusedxml など）。

---

## ディレクトリ構成（ソース概要）

以下は `src/kabusys` 以下の主要ファイルとその役割の概観です。

- kabusys/
  - __init__.py
  - config.py              — 環境変数／設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント / 保存ユーティリティ
    - news_collector.py     — RSS 取得・前処理・raw_news 保存・銘柄抽出
    - schema.py             — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— マーケットカレンダー更新・営業日判定ユーティリティ
    - audit.py              — 発注 / 監査用テーブル定義
    - features.py           — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py    — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py— forward returns / IC / summary utilities
  - strategy/
    - __init__.py
    - feature_engineering.py— build_features（正規化・ユニバースフィルタ）
    - signal_generator.py   — generate_signals（final_score 計算、BUY/SELL 生成）
  - execution/              — 発注／execution 層（空 __init__.py が存在、拡張ポイント）
  - monitoring/             — 監視用機能（フォルダ placeholder）

各ファイル内に詳細なドキュメント文字列（docstring）と設計コメントが含まれています。実装仕様（StrategyModel.md / DataPlatform.md 等）が参照される設計になっています。

---

## 開発／貢献メモ

- 単体テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動 .env ロードを無効化できます。
- 外部 API 呼び出し部分（jquants_client._request や news_collector._urlopen）はテスト時にモック差替え可能なように設計されています。
- DuckDB のスキーマは冪等に作成されるため、初回のみ init_schema を呼べば良い設計です。
- エラーログ・警告はログレベルに応じて出力されます。LOG_LEVEL 環境変数で制御してください。

---

必要に応じて README に追記（例: CI の設定、デプロイ手順、cron による定期実行方法、より詳細なサンプルスクリプト）します。追加で載せたい情報があれば教えてください。