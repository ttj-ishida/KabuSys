# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ集 (KabuSys)。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、DuckDB スキーマ／監査ログなど、戦略開発から実運用までの基盤機能を提供します。

## 概要
KabuSys は以下のレイヤーで構成されたモジュール群です。

- Data layer: J-Quants から株価・財務・市場カレンダーを取得し、DuckDB に保存する ETL。
- Processed / Feature layer: prices_daily / features / ai_scores 等の集計・特徴量生成。
- Research: ファクター計算・IC 計測・将来リターン解析などの研究ユーティリティ。
- Strategy: 特徴量から戦略シグナル（BUY/SELL）を生成するロジック。
- News: RSS からのニュース収集と銘柄紐付け機能。
- Execution / Audit: 発注・約定・ポジション管理用のスキーマ定義と監査ログ（設計済）。
- 設定管理: .env / 環境変数読み込みユーティリティ（自動ロード機能付き）。

設計上のポイント:
- DuckDB を主なデータ永続層として使用（軽量で分析向け）。
- 取得・保存処理は冪等（ON CONFLICT など）を重視。
- ルックアヘッドバイアス対策、レート制限、リトライ、SSRF/入力検証などを考慮した堅牢な実装。

---

## 機能一覧
主な機能（モジュール単位）

- 環境設定読み込み: 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（必要に応じて無効化可能）。
- J-Quants クライアント:
  - 日足（OHLCV）取得（ページネーション対応、リトライ、レート制限、トークン自動リフレッシュ）
  - 財務データ取得
  - 市場カレンダー取得
  - DuckDB への冪等保存ユーティリティ
- ETL パイプライン:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分/バックフィル対応）
  - 品質チェック（quality モジュール経由、設計に記載）
- DuckDB スキーマ定義と初期化（init_schema）
- 特徴量計算（research.factor_research）:
  - Momentum, Volatility (ATR), Value (PER/ROE), Liquidity 等
- 特徴量エンジニアリング（strategy.feature_engineering）:
  - ユニバースフィルタ、Z スコア正規化、features テーブルへの UPSERT（日付単位で置換）
- シグナル生成（strategy.signal_generator）:
  - ファクター + AI スコア統合、final_score 計算、Bear フィルタ、BUY/SELL 生成、signals テーブル書き込み（冪等）
- ニュース収集（data.news_collector）:
  - RSS 取得、前処理、記事 ID 生成、raw_news / news_symbols への保存、SSRF 対策、サイズ上限
- カレンダー管理（data.calendar_management）:
  - 営業日判定、next/prev_trading_day、calendar_update_job
- 統計ユーティリティ（data.stats）:
  - zscore_normalize（クロスセクション正規化）
- 監査ログ（data.audit）:
  - signal_events / order_requests / executions 等の DDL（監査用）

---

## セットアップ手順

前提
- Python 3.10 以降（typing の | 型ヒントを使用）
- pip, virtualenv 等

1. リポジトリをクローン / 作業ディレクトリへ
2. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows (PowerShell/CMD)
   ```
3. インストール（最低限の依存）
   - 必要なパッケージ（例）
     - duckdb
     - defusedxml
   サンプル:
   ```bash
   pip install duckdb defusedxml
   # 開発パッケージがまとまっている場合は setup.py/pyproject.toml 経由でインストール
   # 例: pip install -e .
   ```
   ※ パッケージ配布がない場合はプロジェクト直下で `PYTHONPATH=src` を通して利用可能。

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を配置できます。
   - 自動読み込みはデフォルトで有効。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須・オプション）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード（execution 層利用時）
   - KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN (必須) — Slack 通知用
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (任意, default: data/kabusys.duckdb)
   - SQLITE_PATH (任意, default: data/monitoring.db)
   - KABUSYS_ENV (任意, allowed: development, paper_trading, live) — 実行環境
   - LOG_LEVEL (任意, allowed: DEBUG/INFO/WARNING/ERROR/CRITICAL)

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=YOUR_JQUANTS_REFRESH_TOKEN
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は Python スクリプト/対話での利用例です。`src` が PYTHONPATH に含まれるか pip install 済みである想定です。

1) DuckDB スキーマを初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

2) 日次 ETL の実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量を構築（features テーブルへ書き込み）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, date.today())  # もしくは ETL 後の最終営業日
print(f"features upserted: {n}")
```

4) シグナルを生成して signals テーブルに保存
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, date.today(), threshold=0.6)
print(f"signals written: {count}")
```

5) ニュース収集ジョブ（RSS）を実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# sources を省略すると DEFAULT_RSS_SOURCES を使用
results = run_news_collection(conn, known_codes={"7203", "6758"})  # known_codes は既知の銘柄コード集合
print(results)
```

6) J-Quants からの直接取得（テスト用途）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意点:
- ETL はエラーや品質検査を個別にハンドリングするため、戻り値の `ETLResult` を確認してください。
- feature/signal の各関数は target_date 時点のデータのみを参照し、ルックアヘッドバイアスを回避する設計です。

---

## ディレクトリ構成（抜粋）
リポジトリ内の主要ファイル/モジュールを示します（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・.env 読み込み / Settings
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント／保存ユーティリティ
    - news_collector.py     — RSS 収集・保存・銘柄抽出
    - schema.py             — DuckDB スキーマ定義 & init_schema()
    - stats.py              — zscore_normalize 等
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - calendar_management.py— カレンダー管理（営業日判定等）
    - features.py           — data.stats の再エクスポート
    - audit.py              — 監査ログ DDL（signal_events / order_requests 等）
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Value/Volatility 計算
    - feature_exploration.py— IC 計算・将来リターン・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py— features の構築（正規化、ユニバースフィルタ）
    - signal_generator.py   — final_score 計算・BUY/SELL 生成
  - execution/               — 発注関連のコード（パッケージとして存在）
  - monitoring/              — 監視/通知系（Slack 連携等、補完想定）

（上記は提供されたコードベースの主な部分の一覧です。実際のリポジトリには README 以外のファイルやドキュメント、テストが含まれる可能性があります。）

---

## 開発/運用上の注意
- Python バージョンは 3.10 以上を推奨（型ヒントの | 演算子を使用）。
- DuckDB を用いた SQL 実行はトランザクション（BEGIN / COMMIT / ROLLBACK）を使って原子性を担保しています。操作時は例外ハンドリングを行ってください。
- J-Quants API のレート制限（120 req/min）および HTTP エラーに対するリトライは jquants_client に実装されています。
- ニュース収集は SSRF / XML 安全対策（defusedxml, ホスト判定、サイズ上限）を施していますが、実運用時は RSS ソースの信頼性・ライセンスに注意してください。
- 環境変数が未設定の場合、Settings プロパティで ValueError が発生します。.env.example 等を参考に .env を準備してください。

---

貢献・問い合わせ:
- バグ報告や改善提案は Issue でお願いします。README の補足や CLI ラッパー・オーケストレーションスクリプトの追加は歓迎します。

ライセンスや著作権情報はリポジトリ側の LICENSE を参照してください。