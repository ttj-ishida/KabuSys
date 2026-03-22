# KabuSys

KabuSys は日本株向けの自動売買フレームワークです。データ収集（J-Quants 等）→ ETL → ファクター計算 → シグナル生成 → バックテスト → 実運用（execution / monitoring）までの一連処理をモジュール化して提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「テストしやすさ」「DuckDB によるローカル DB 管理」です。

---

## 主要な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（jquants_client）
    - 日足（OHLCV）、財務データ、マーケットカレンダー取得（ページネーション・リトライ・トークン自動更新）
  - ニュース収集（RSS）と銘柄紐付け（news_collector）
  - DuckDB スキーマ定義と初期化（data.schema）
  - ETL パイプライン（data.pipeline） — 差分更新、バックフィル、品質チェック呼び出し（quality は別モジュール想定）

- 研究（Research）
  - ファクター計算（research.factor_research）
    - Momentum / Volatility / Value 等のファクターを prices_daily / raw_financials から計算
  - ファクター探索・評価（research.feature_exploration）
    - 将来リターン計算、IC（Spearman）計算、統計サマリー

- 戦略（Strategy）
  - 特徴量エンジニアリング（strategy.feature_engineering）
    - 生ファクターの正規化、ユニバースフィルタ、features テーブルへの UPSERT
  - シグナル生成（strategy.signal_generator）
    - features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals テーブルへ書き込み

- バックテスト（Backtest）
  - ポートフォリオシミュレータ（backtest.simulator） — スリッページ・手数料・約定ロジック
  - バックテストエンジン（backtest.engine） — 本番 DB を読み取り専用でコピーして日次ループでシミュレーション
  - メトリクス計算（backtest.metrics）
  - CLI 実行スクリプト（backtest.run）

- 実行層（Execution / Monitoring）
  - 発注・約定・ポジション保存用スキーマを提供（data.schema）
  - 実稼働向けに Slack 通知等の設定（config & settings）を想定

---

## システム要件

- Python 3.10+
- DuckDB
- defusedxml（RSS パーシングの安全対策）
- （通信系）標準ライブラリの urllib を使用。J-Quants などの外部 API はネットワークアクセスを必要とします。

パッケージ依存はプロジェクトの pyproject.toml / requirements.txt を参照してください。簡易的には以下をインストールします:

```bash
python -m pip install "duckdb" "defusedxml"
# 開発中はパッケージを編集可能インストール
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／取得

2. Python 環境を用意（推奨: venv）

3. 必要なパッケージをインストール（上記参照）

4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くことで自動的に読み込まれます（kabusys.config にて .git または pyproject.toml を起点に検出）。
   - 自動ロードを無効化する場合：
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時等に便利です）。

   必要な環境変数（主要なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabuステーション等の API パスワード（必須）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
   - DUCKDB_PATH           : DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite （監視用）パス（省略時: data/monitoring.db）
   - KABUSYS_ENV           : 環境 ("development"| "paper_trading" | "live")（省略時: development）
   - LOG_LEVEL             : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（省略時: INFO）

   例 .env（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマの初期化

   Python REPL やスクリプトで初期化できます:

   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```

   またはコマンドラインから（簡易例）:

   ```bash
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

---

## 使い方（代表的な操作）

- バックテスト（CLI）

  プリポピュレート済みの DuckDB（prices_daily, features, ai_scores, market_regime, market_calendar が入っていること）を指定して実行します。

  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 \
    --slippage 0.001 \
    --commission 0.00055 \
    --max-position-pct 0.20 \
    --db data/kabusys.duckdb
  ```

  オプション:
  - --start / --end : バックテスト期間
  - --cash : 初期資金（円）
  - --slippage : スリッページ率
  - --commission : 手数料率
  - --max-position-pct : 1銘柄あたりの最大比率
  - --db : DuckDB ファイルパス

- Python からバックテスト API を使う

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")  # or get_connection
  res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()

  # res.history, res.trades, res.metrics を参照
  ```

- ETL（株価差分取得）例（data.pipeline）

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl, ETLResult

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

  - run_prices_etl, run_news_collection 等の関数は差分取得・保存（冪等）を行います。
  - ETLResult クラスで結果・品質問題・エラーの要約を取得できます。

- ファクター計算 / 特徴量構築 / シグナル生成（戦略ワークフロー）

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features, generate_signals

  conn = init_schema("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  # features を構築し、features テーブルを更新（冪等）
  n = build_features(conn, target)

  # シグナル生成（features, ai_scores, positions を参照して signals に書き込む）
  m = generate_signals(conn, target)
  ```

- ニュース収集（RSS） & 保存

  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  # known_codes は 銘柄コードの set を渡すと記事→銘柄の紐付けを行う
  result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  ```

---

## 重要な設計上の注意点

- 環境変数管理
  - config.Settings クラスで環境変数を参照します。必須変数が未設定の場合は ValueError が発生します。
  - 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を読み込みます。テスト時等に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

- DB の冪等操作
  - 多くの保存処理は ON CONFLICT / DO UPDATE / DO NOTHING を使用して冪等性（重複挿入回避）を確保しています。

- ルックアヘッドバイアス対策
  - features / signals / ETL は target_date 時点までのデータのみを参照するよう設計されています（将来情報を参照しない）。

- テスト容易性
  - ETL / API 呼び出しは id_token 等を注入可能にしているためモックしやすくなっています。
  - バックテストは本番 DB をコピーしてインメモリ DB で実行するため本番テーブルを汚染しません。

---

## ディレクトリ構成

（src 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得 + 保存ユーティリティ）
    - news_collector.py  — RSS 取得・前処理・DB 保存
    - pipeline.py        — ETL 差分更新の制御（run_prices_etl 等）
    - schema.py          — DuckDB スキーマ定義 & init_schema
    - stats.py           — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — raw factor を正規化して features に保存
    - signal_generator.py    — final_score 計算と signals テーブルへの出力
  - backtest/
    - __init__.py
    - engine.py        — バックテストのメインループ（run_backtest）
    - simulator.py     — PortfolioSimulator、約定モデル
    - metrics.py       — バックテスト評価指標
    - run.py           — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py         — SimulatedClock（将来拡張用）
  - execution/         — 発注・約定関連（未実装のファイル群）
  - monitoring/        — 監視関連（例: SQLite に記録等、未実装のファイル群）

---

## 参考 / トラブルシューティング

- ログレベルは環境変数 LOG_LEVEL で制御できます（INFO デフォルト）。
- .env の自動ロードはプロジェクトルートを基準に行われるため、実行カレントディレクトリが異なっても正しく動作します（パッケージ配布後も想定）。
- J-Quants API はレート制限が厳しいため jquants_client は固定間隔スロットリングとリトライ戦略を実装しています。大量取得は時間を要します。
- RSS 取得は SSRF 対策（リダイレクト検査、ホストのプライベート判定）や gzip 上限チェックなど堅牢性向上の措置を行っています。

---

この README はコードベースの概要と主要な操作手順をまとめたものです。詳細な仕様（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）はリポジトリ内の設計ドキュメントを参照してください。ご不明点があれば、どの部分を詳しく知りたいか教えてください。