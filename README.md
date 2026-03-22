# KabuSys

日本株向けの自動売買システム（ライブラリ）。データ取得・ETL、特徴量計算、シグナル生成、バックテスト、ニュース収集など、戦略開発と運用に必要な主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下のレイヤーで構成される投資システムの基盤ライブラリです。

- データ層（J-Quants からの株価・財務・カレンダー取得、RSS ニュース収集）
- データベース層（DuckDB スキーマ定義・初期化）
- 研究（research）層（ファクター計算、特徴量探索、IC 等）
- 戦略（strategy）層（特徴量の正規化・合成、最終スコア計算と売買シグナル生成）
- バックテスト（backtest）層（シミュレータ、エンジン、メトリクス）
- 実行（execution）／監視（monitoring）層（発注・監視機能のためのプレースホルダ）

設計上のポイント:
- DuckDB を中心にオンメモリ or ファイル DB を用いる
- J-Quants API への呼び出しはレート制御・リトライ等を含む堅牢な実装
- ETL・DB 操作は冪等（ON CONFLICT 等）を意識
- ルックアヘッドバイアスを避けるため、target_date 時点の利用可能データのみを使用

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・トークン自動更新・レート制御・リトライ）
  - news_collector: RSS 収集、前処理、記事ID生成、ニュース→銘柄紐付け
  - schema: DuckDB スキーマの定義と init_schema()
  - pipeline: 差分 ETL のユーティリティ（差分算出、品質チェックフック等）
  - stats: z-score 正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value などファクター計算
  - feature_exploration: 将来リターン計算、IC、ファクター統計サマリー
- strategy/
  - feature_engineering: 生ファクターを正規化し features テーブルに保存
  - signal_generator: features + ai_scores を統合し BUY/SELL シグナルを生成
- backtest/
  - engine: run_backtest 関数（本番 DB からコピーして日次ループでシミュレーション）
  - simulator: PortfolioSimulator（擬似約定・スリッページ・手数料モデル）
  - metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD, WinRate 等）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）

---

## 動作環境 / 前提

- Python 3.10 以上（型アノテーションで | を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS）
- 環境変数に API トークン等を設定

requirements.txt（例）
```
duckdb
defusedxml
```

※実際の運用では追加パッケージ（Slack クライアント等）が必要になることがあります。

---

## 環境変数（必須・推奨）

config.Settings から参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション用パスワード（発注を行う場合）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : 通知先チャンネル ID

オプション / デフォルトあり:
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite のパス（デフォルト: data/monitoring.db）

.env ファイルについて:
- プロジェクトルートの `.env`、`.env.local` を自動読み込みします（OS 環境変数が優先）。
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例（.env.example 的な内容）:
```
JQUANTS_REFRESH_TOKEN=xxx...
KABU_API_PASSWORD=yyy...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作る（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```

   （簡易に duckdb と defusedxml だけインストールする場合）
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数（.env）を作成
   - プロジェクトルートに `.env` または `.env.local` を配置し、前述のキーを設定してください。

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # パスは環境に合わせて調整
   conn.close()
   ```

---

## 使い方（主要な例）

以下はライブラリの主要 API を利用する簡単な例です。実運用ではログ設定や例外処理を追加してください。

- DuckDB 接続の取得（初期化済み DB を使用）
  ```python
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  ```

- 特徴量構築（features テーブルへの UPSERT。target_date は datetime.date）
  ```python
  from datetime import date
  from kabusys.strategy import build_features

  build_features(conn, target_date=date(2024, 1, 31))
  ```

- シグナル生成（signals テーブルへ書込み）
  ```python
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
  ```

- バックテスト実行（CLI）
  DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar）が事前に存在している必要があります。
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 \
    --db data/kabusys.duckdb
  ```

  主要フラグ:
  - --start / --end : バックテスト期間（YYYY-MM-DD）
  - --cash : 初期資金（デフォルト: 10000000）
  - --slippage / --commission : スリッページ / 手数料率
  - --max-position-pct : 1銘柄あたりの最大ポジション比率（デフォルト: 0.20）

- ニュース収集と保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄コードの集合（抽出に利用）
  run_news_collection(conn, known_codes={"7203", "6758"})
  ```

---

## ディレクトリ構成（主なファイル）

（root 以下の src/kabusys を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数読み込み・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + 保存関数
    - news_collector.py      # RSS 収集・前処理・保存
    - schema.py              # DuckDB スキーマ定義 / init_schema
    - pipeline.py            # ETL 差分更新ユーティリティ（run_prices_etl 等）
    - stats.py               # zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     # momentum/volatility/value/fundamental の計算
    - feature_exploration.py # forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py # features の構築（正規化・フィルタ）
    - signal_generator.py    # final_score 計算・BUY/SELL 判定
  - backtest/
    - __init__.py
    - engine.py              # run_backtest（本体ループ）
    - simulator.py           # PortfolioSimulator
    - metrics.py             # バックテスト評価指標
    - run.py                 # CLI エントリポイント
    - clock.py               # SimulatedClock（将来拡張用）
  - execution/                # 発注系（プレースホルダ）
  - monitoring/               # 監視系（プレースホルダ）

---

## 注意点 / 補足

- セキュリティ:
  - RSS 取得部では SSRF 対策、サイズ制限、defusedxml を利用した XML パースを実装しています。
  - J-Quants API 呼び出しはレート制御とリトライロジックが組み込まれています。
- データ品質:
  - ETL は差分取得とバックフィル（デフォルト 3 日）をサポートし、品質チェックフックがあります（quality モジュール想定）。
- 実運用:
  - 発注・実行（execution）や監視（monitoring）周りはプロジェクト要件に応じて実装を追加してください。
  - live 環境で発注を行う場合は十分なテスト・アクセス制御を行ってください。

---

README に記載のない利用方法や、各モジュールの API ドキュメント（引数詳細や戻り値定義）が必要でしたら、どのモジュールを優先して詳述するか教えてください。README をプロジェクトの実際の README.md 形式に整形・微調整することもできます。