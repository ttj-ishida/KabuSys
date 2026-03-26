# KabuSys

日本株向けの自動売買・研究プラットフォーム（軽量なバックテスト/リサーチ/データ ETL モジュール群）。

このリポジトリは、J-Quants や RSS などからデータを収集し、DuckDB を用いて特徴量作成、シグナル生成、ポートフォリオ構築、バックテストを行うためのモジュール群を提供します。運用（ライブ）・ペーパートレード・研究環境のいずれにも対応する設計です。

---

## 概要

- データ取得（J-Quants API）→ DuckDB 保存 → 研究用ファクター計算 → 特徴量正規化 → シグナル生成 → ポートフォリオ構築 → 約定シミュレーション（バックテスト）
- ニュース（RSS）収集・銘柄紐付け機能を備え、AI スコア等と統合してニュース加重を扱えます。
- バックテストエンジンは、スリッページ・手数料・セクター上限・ポジションサイジング等を再現します。
- 環境変数ベースの設定管理。プロジェクトルートの `.env` / `.env.local` を自動読み込み（不要時は無効化可）。

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants API クライアント（ページネーション・自動トークンリフレッシュ・レート制御・リトライ）
  - 株価（OHLCV）、財務、上場銘柄情報、JPX カレンダーの取得と DuckDB への保存
- ニュース収集
  - RSS フィード取得（SSRF対策、gzip/サイズ制限、記事ID整形）
  - raw_news / news_symbols への冪等保存
- 研究 / ファクター
  - Momentum / Volatility / Value 等のファクター計算（DuckDB SQL + Python）
  - Zスコア正規化ユーティリティ
  - ファクター探索（IC、フォワードリターン、統計サマリー）
- 戦略
  - 特徴量構築（features テーブルへの書き込み）
  - シグナル生成（features と ai_scores を統合、BUY/SELL を signals テーブルへ書き込み）
- ポートフォリオ
  - 候補選定、等配分・スコア配分、リスクベースサイジング、セクター集中制限、レジーム乗数
- バックテスト
  - 日次ループでの売買シミュレーション（スリッページ・手数料・部分約定）
  - バックテストメトリクス計算（CAGR、Sharpe、MaxDD、勝率等）
  - CLI での実行サポート（python -m kabusys.backtest.run）

---

## 前提 / 必要環境

- Python 3.10 以上（型ヒントのユニオン演算子 `|` 等を利用）
- 主な依存ライブラリ（最低限）
  - duckdb
  - defusedxml
- （J-Quants や Slack 連携を利用する場合は外部ネットワークアクセスと API トークン）

依存はプロジェクトのセットアップ方法に従ってインストールしてください（requirements.txt がある場合は `pip install -r requirements.txt`）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   ```

2. 必要な依存をインストール（例）
   ```
   pip install duckdb defusedxml
   ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を用意している想定です。そこからインストールしてください。

3. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成すると、自動的に読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
   - KABU_API_PASSWORD — kabuステーション API パスワード（運用時）
   - SLACK_BOT_TOKEN — Slack ボットトークン（通知等に使用）
   - SLACK_CHANNEL_ID — Slack チャンネル ID

   オプション（多くはデフォルトあり）
   - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
   - LOG_LEVEL — DEBUG/INFO/...
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — monitoring 用 SQLite（デフォルト data/monitoring.db）

4. DuckDB スキーマ初期化
   - このコードベースには schema 初期化関数 `kabusys.data.schema.init_schema` を用いる想定です（実際に schema モジュールを用意してください）。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

5. データ取得（J-Quants から）
   - J-Quants クライアント関数を使ってデータを取得し、DuckDB に保存します。
     - `kabusys.data.jquants_client.fetch_daily_quotes()` → `save_daily_quotes(conn, records)`
     - `fetch_financial_statements()` → `save_financial_statements(conn, records)`
     - `fetch_market_calendar()` → `save_market_calendar(conn, records)`
   - トークンは `JQUANTS_REFRESH_TOKEN` を `.env` に設定しておくと自動で利用されます。

---

## 使い方（主要コマンド / API）

### バックテスト（CLI）
DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等）が準備されていることが前提です。

例：
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 --db data/kabusys.duckdb \
  --allocation-method risk_based --lot-size 100
```

実行後、CAGR・Sharpe 等の集計結果が標準出力に表示されます。

### プログラムから呼ぶ（一部例）

- 特徴量構築（features テーブルへ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy.feature_engineering import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  cnt = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()
  print(f"upserted features: {cnt}")
  ```

- シグナル生成（signals テーブルへ書き込み）
  ```python
  from kabusys.strategy.signal_generator import generate_signals
  cnt = generate_signals(conn, target_date=date(2024, 1, 31))
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(res)  # {source_name: saved_count}
  ```

- J-Quants からのデータ取得と保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=..., date_to=...)
  n = save_daily_quotes(conn, records)
  ```

- バックテストを Python API で直接呼ぶ
  ```python
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  metrics = result.metrics
  ```

---

## 設定の挙動（.env 自動ロード）

- 自動ロード順序（既定）:
  1. OS 環境変数（常に優先）
  2. .env（プロジェクトルートが自動検出される場合）
  3. .env.local（上書き、.env の値を上書き可能）

- 無効化:
  - テストなどで自動ロードを行いたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- 必須環境変数が未設定の場合、Settings プロパティ（例: settings.jquants_refresh_token）を参照した際に ValueError が発生します。

- KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれか。`is_live`, `is_paper`, `is_dev` のプロパティで判定可能。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理
- data/
  - jquants_client.py — J-Quants API クライアント・保存ロジック
  - news_collector.py — RSS 収集・前処理・保存
  - (schema.py 等を置く想定)
- research/
  - factor_research.py — Momentum/Volatility/Value ファクター
  - feature_exploration.py — IC, forward returns, summary
- strategy/
  - feature_engineering.py — features 作成パイプライン
  - signal_generator.py — final_score 計算と BUY/SELL 生成
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・キャップ・スケールダウン
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- backtest/
  - engine.py — バックテストのメインループ（run_backtest）
  - simulator.py — 約定シミュレータ、履歴・トレード記録
  - metrics.py — バックテスト評価指標の計算
  - run.py — CLI エントリポイント
  - clock.py — 将来拡張用の模擬時計
- portfolio/, execution/, monitoring/ — 各層のエントリ（モジュール群）

（実際のツリーはリポジトリに合わせて若干の差異がある可能性があります。上はコードベースから抜粋した主要ファイルです。）

---

## 開発上の注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス回避: 特徴量・シグナル生成は target_date 時点までのデータのみ参照します。
- 冪等性: DB への挿入は基本的に ON CONFLICT（または DO NOTHING / RETURNING）で重複を排除します。
- 豊富なログ出力: 内部の警告・情報ログを活用してデータ欠損やスキップ理由を追跡できます。
- ネットワーク安全: RSS 取得で SSRF 対策・サイズ上限・gzip 解凍上限などの保護を実装しています。
- テスト容易性: env 自動ロードの無効化や、ネットワーク呼び出し部分をモックしやすい設計になっています。

---

## よくある操作メモ

- `.env` の値を反映したくない CI/テスト時: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用。
- バックテストでレジームデータがないときは `market_regime` が空で `bull` にフォールバックします。
- ニュースの銘柄抽出は単純に 4 桁の数字（日本株）を抽出して既知銘柄集合と照合します。必要に応じて精度向上の前処理を検討してください。

---

README に記載のない詳細（例: schema の実装、requirements、CI 設定）はプロジェクトに応じて補完してください。必要であれば README の補足セクション（データ初期ロード手順の詳細、テーブル定義サンプル、運用時の Slack 通知設定など）を追記します。