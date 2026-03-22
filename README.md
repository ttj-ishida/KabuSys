# KabuSys

日本株向けの自動売買システム / 研究・データ基盤・バックテスト・戦略生成を含むパッケージ群。

このリポジトリは、データ取得（J‑Quants）、ETL、特徴量作成、シグナル生成、バックテストシミュレーション、ニュース収集、実行レイヤ（スキーム定義）をワンパッケージで提供します。DuckDB を中心にローカルで完結する設計になっています。

---

## 主な特徴（機能一覧）

- データ取得
  - J‑Quants API クライアント（ページネーション・レート制御・トークン自動リフレッシュ・リトライを実装）
  - 株価日足、財務データ、JPX カレンダーの取得
- ETL / データ基盤
  - 差分更新（バックフィル考慮）と品質チェック（設計）
  - DuckDB スキーマ定義・初期化（冪等）
- ニュース収集
  - RSS フィード収集、前処理、記事ID生成（URL 正規化 + SHA256）
  - SSRF 対策、gzip サイズ制限、XML パースの安全処理（defusedxml）
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）やファクター統計
  - Z スコア正規化ユーティリティ
- 特徴量・シグナル生成（Strategy）
  - features テーブル作成（正規化・クリップ・ユニバースフィルタ）
  - ai_scores と統合して final_score を算出し BUY/SELL シグナル生成
  - Bear レジーム抑制、エグジット（ストップロス等）
- バックテスト
  - インメモリでのバックテスト実行（本番 DB を汚さない）
  - スリッページ / 手数料モデルを考慮した約定シミュレーション
  - パフォーマンス指標計算（CAGR / Sharpe / MaxDD / 勝率 / Payoff）
  - CLI エントリポイントあり（python -m kabusys.backtest.run）
- 実行層（スキーマ）
  - signals / orders / trades / positions 等、発注〜約定〜ポジション管理のスキーマを提供

---

## 必要条件

- Python 3.10 以上（型注釈に | を使うため）
- pip 等で以下をインストールしてください（最小限）:
  - duckdb
  - defusedxml

推奨（プロダクション的に使う場合）:
- logging の設定、Slack 通知に使うトークン等

例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（プロジェクトに requirements.txt がある場合はそちらをご利用ください）

---

## 環境変数（設定項目）

このパッケージは環境変数 / .env から設定を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を読み込みます。テスト時など自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

任意 / 既定値あり:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（値が設定されていると無効）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視等）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

簡単な .env 例（プロジェクトルートに .env を置く）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python と依存パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   ```

2. リポジトリをクローン / ソースを配置
   - パッケージを editable install する場合:
     ```bash
     python -m pip install -e .
     ```
     （このリポジトリに setup / pyproject を用意している場合。なければ PYTHONPATH に src を追加してください）

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境に直接設定します（上記参照）。

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトでスキーマを作成します:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     db = init_schema(settings.duckdb_path)
     db.close()
     ```
   - または明示的にパスを指定:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```

---

## 使い方（主要な操作例）

1. バックテスト（CLI）
   ```bash
   python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2024-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
   ```
   オプション:
   - --start / --end : 日付（YYYY-MM-DD）
   - --cash : 初期資金（JPY）
   - --slippage : スリッページ率（デフォルト 0.001）
   - --commission : 手数料率（デフォルト 0.00055）
   - --max-position-pct : 1 銘柄あたり最大ポジション比率（デフォルト 0.20）
   - --db : DuckDB ファイルパス（必須）

2. ETL（株価差分取得の例）
   - run_prices_etl 等の関数を使ってプログラムから ETL を実行します（J‑Quants API トークンが必要）。
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_prices_etl

   conn = init_schema("data/kabusys.duckdb")
   fetched, saved = run_prices_etl(conn, target_date=date.today())
   conn.close()
   ```

3. 特徴量作成 / シグナル生成（プログラム呼び出し）
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.strategy import build_features, generate_signals

   conn = init_schema("data/kabusys.duckdb")
   build_count = build_features(conn, target_date=date(2024, 1, 31))
   signal_count = generate_signals(conn, target_date=date(2024, 1, 31))
   conn.close()
   ```

4. ニュース収集（RSS）を実行して DB に保存
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = init_schema("data/kabusys.duckdb")
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203", "6758"]))
   conn.close()
   ```

5. J‑Quants からのデータ取得サンプル
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = save_daily_quotes(conn, records)
   conn.close()
   ```

---

## 開発・テスト時の注意点

- 環境変数の自動ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml）を基準に自動で `.env` / `.env.local` を読み込みます。
  - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで意図的に環境を制御したい場合など）。
- DuckDB への挿入は各モジュールで冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を考慮していますが、本番運用前にバックアップを必ず取ってください。
- ニュース収集では外部 URL の検査や受信サイズ制限を行っています。テスト時のモック化箇所はモジュール内にコメントがあります（例: _urlopen の差し替え）。

---

## ディレクトリ構成（主要ファイルの説明）

（パッケージルート: src/kabusys/ 以下）

- __init__.py
  - パッケージ初期化とバージョン

- config.py
  - 環境変数読み込み、Settings クラス（J‑Quants トークン、kabu API パスワード、Slack トークン、DB パス等）

- data/
  - __init__.py
  - jquants_client.py : J‑Quants API クライアント、取得・保存ユーティリティ
  - news_collector.py : RSS フィード収集、記事前処理、DB 保存
  - schema.py : DuckDB スキーマ定義と init_schema/get_connection
  - pipeline.py : ETL パイプラインの差分更新ロジック（run_prices_etl 等）
  - stats.py : zscore_normalize などの統計ユーティリティ

- research/
  - __init__.py
  - factor_research.py : Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー

- strategy/
  - __init__.py
  - feature_engineering.py : 生ファクターから features を構築・正規化
  - signal_generator.py : features と ai_scores を統合してシグナル生成

- backtest/
  - __init__.py
  - engine.py : バックテスト全体ループ（インメモリ DB 作成・日次処理）
  - simulator.py : PortfolioSimulator（擬似約定、履歴・取引記録）
  - metrics.py : バックテスト評価指標の計算
  - clock.py : SimulatedClock（将来的な用途）
  - run.py : CLI エントリポイント（python -m kabusys.backtest.run）

- execution/
  - （発注 API / 実行ロジック (空の __init__ が含まれる) — 発注周りの拡張用）

- monitoring/
  - （監視系 DB / スクリプトのためのファイルを配置する想定）

---

## 貢献・拡張のヒント

- StrategyModel.md / DataPlatform.md / BacktestFramework.md といった設計ドキュメントに従って拡張すると統合が楽です（リポジトリに無ければ設計文書を作ることを推奨）。
- AI スコア連携や Slack 通知、kabu ステーションとの実発注は execution 層に実装してください。現在の戦略モジュールは発注 API に依存しない設計です（ユニットテストが容易）。
- テストは DuckDB の ":memory:" モードを使用すると便利です（schema.init_schema(":memory:")）。

---

## ライセンス・免責

この README はソースコードの説明に基づくドキュメントです。実際に証券売買を行う場合は法令・取引所ルールを遵守し、実運用前に十分なバックテスト・検証・レビューを行ってください。本ソフトウェアの結果に基づく損失等に関して作者は責任を負いません。

---

以上。README に追加したい具体的なコマンドやサンプル（例: .env.example テンプレート、requirements.txt の内容、CI の設定など）があれば追記します。