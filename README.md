# KabuSys

日本株向けの自動売買フレームワーク（ライブラリ）。データ取得・ETL、ファクター計算、特徴量エンジニアリング、シグナル生成、バックテスト、ニュース収集、発注／実行レイヤーの基盤機能を提供します。

主に DuckDB を用いたローカルデータプラットフォームと、J-Quants API / RSS からデータを取得するモジュール群、および戦略・バックテスト実行用のユーティリティを含みます。

## 主な機能

- データ取得・保存
  - J-Quants API クライアント（株価日足・財務・マーケットカレンダー）
  - RSS ニュース収集と銘柄抽出
  - DuckDB スキーマ定義と初期化（冪等）
- ETL / データパイプライン
  - 差分更新、バックフィル、品質チェック（quality モジュールと連携）
- 研究・ファクター計算
  - Momentum / Volatility / Value ファクターの計算（prices_daily / raw_financials を参照）
  - 将来リターン、IC（Spearman）計算、ファクター統計サマリ
- 特徴量エンジニアリング
  - 生ファクターの正規化・フィルタリング・features テーブルへの保存（冪等）
- シグナル生成
  - features と AI スコアを統合して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存
  - Bear レジーム判定やストップロス判定などのロジックを実装
- バックテストフレームワーク
  - インメモリ DuckDB を用いた再現可能なバックテスト実行（売買シミュレータ、メトリクス算出）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- 発注 / 実行層（骨組み）
  - schema による execution テーブル定義（signal_queue / orders / trades / positions 等）

## 要件（概略）

- Python 3.10+
- 必須パッケージ（抜粋）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging など

（実際の requirements.txt がある場合はそちらを使ってください）

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb defusedxml
   ```
   実プロジェクトでは requirements.txt / poetry / pip-tools 等を使って管理してください。

4. 環境変数を設定
   プロジェクトルートに `.env`（任意）や `.env.local` を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます）。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV           : 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
   - LOG_LEVEL             : ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

## 初期化（DuckDB スキーマ作成）

Python REPL またはスクリプトで schema を初期化します。

```python
from kabusys.data.schema import init_schema

# ファイル DB の初期化（親ディレクトリがなければ自動作成）
conn = init_schema("data/kabusys.duckdb")
# 処理終了後は close()
conn.close()
```

インメモリ DB が必要な場合は `":memory:"` を渡します（バックテスト時に内部で使用されます）。

## 使い方（主要ワークフローの例）

1) データ取得 → 保存（J-Quants）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# 全銘柄の 2024-01-01 〜 2024-03-31 の日足取得
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,3,31))
saved = jq.save_daily_quotes(conn, records)
print("saved prices:", saved)

conn.close()
```

2) ニュース収集（RSS）と銘柄抽出
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes を渡すと記事内の4桁銘柄コード抽出・紐付けが行われます
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(res)
conn.close()
```

3) 特徴量構築（features テーブル）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,3,31))
print("built features:", n)
conn.close()
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,3,31))
print("signals generated:", count)
conn.close()
```

5) バックテスト（CLI）
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
主なオプション:
- --start / --end : 開始・終了日（ISO）
- --cash : 初期資金（JPY）
- --slippage : スリッページ率（例: 0.001）
- --commission : 手数料率（例: 0.00055）
- --max-position-pct : 1銘柄あたり最大比率
- --db : DuckDB ファイルパス（必須）

バックテストは以下を行います:
- 本番 DB の必要テーブルをコピーしてインメモリ DB を構築
- 日次ループでシグナル約定・時価評価・シグナル再生成を実行
- 最終的に取引履歴とメトリクス（CAGR, Sharpe, MaxDD 等）を出力

## 主要 API（概要）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_base_url, settings.duckdb_path, settings.env, settings.log_level など

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar

- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes

- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)

- kabusys.research.*
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)

- kabusys.backtest
  - run_backtest(conn, start_date, end_date, initial_cash=..., slippage_rate=..., commission_rate=..., max_position_pct=...)
  - CLI: python -m kabusys.backtest.run

## 環境変数の自動ロード挙動

- パッケージ起点でプロジェクトルート（.git または pyproject.toml を基準）を探索し、ルートの `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先度は OS 環境変数 > `.env.local` > `.env` です。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## ディレクトリ構成（概観）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と設定管理（.env 読み込み、自動ロード）
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント（取得・保存）
    - news_collector.py : RSS フィード取得・前処理・DB保存・銘柄抽出
    - schema.py         : DuckDB スキーマ定義と init_schema
    - stats.py          : z-score 正規化など統計ユーティリティ
    - pipeline.py       : ETL パイプライン（差分更新・品質チェック）
  - research/
    - __init__.py
    - factor_research.py     : Momentum / Value / Volatility ファクター計算
    - feature_exploration.py : 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py : features の構築（正規化・ユニバースフィルタ等）
    - signal_generator.py    : final_score 計算、BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py      : バックテストエンジン（全体ループ）
    - simulator.py   : ポートフォリオシミュレータ（擬似約定）
    - metrics.py     : バックテストメトリクス計算
    - run.py         : CLI エントリポイント
    - clock.py       : 模擬時計（将来拡張用）
  - execution/
    - __init__.py    : 発注／実行レイヤー（骨組み）
  - monitoring/      : 監視関連（DB path 等を想定）

（上記は主要ファイルの抜粋。実際のリポジトリのファイル数・構造を参照してください）

## 設計上の留意点

- ルックアヘッドバイアス防止: 多くの処理は target_date 時点のデータのみを使用するよう設計されています（fetched_at の記録やデータ取得・合成の扱いを含む）。
- 冪等性: データ保存処理は ON CONFLICT / UPSERT を用いるか、日付単位の置換で冪等化を図っています。
- エラー処理: ETL は品質問題を検出しても可能な限り処理を続行する設計（呼び出し元で最終判断を行う）。
- ネットワーク安全性: RSS 収集で SSRF 対策や gzip 解凍サイズチェック、defusedxml の利用などを行っています。

## 開発・貢献

- コントリビュート前に Issue を立てて概要を共有してください。
- コードスタイル・テストのガイドラインはプロジェクトルートの CONTRIBUTING.md（存在する場合）に従ってください。

---

README はここまでです。必要であれば、具体的な例（.env.example のテンプレート、requirements.txt の推奨内容、より詳細な運用手順）を追加します。どの部分を詳しく補足しましょうか？