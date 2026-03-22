# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、バックテスト、ニュース収集、バックエンド用スキーマなどを含む一連の機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避けるため「対象日（target_date）時点でシステムが知りうるデータのみ」を扱う
- DuckDB を主要なローカルデータストアとして利用し、冪等保存（ON CONFLICT）を重視
- テスト可能性を意識したインターフェース（id_token 注入など）
- 外部依存は最小限（標準ライブラリ + 必要なパッケージのみ）

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー）
  - raw テーブルへの冪等保存（save_* 関数群）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックのためのユーティリティ
- ニュース収集
  - RSS 収集、前処理、raw_news 保存、記事→銘柄の紐付け
  - SSRF 対策、Gzip / サイズ制限、トラッキングパラメータ除去
- 特徴量 (Feature Engineering)
  - research の生ファクターを正規化・統合して `features` テーブルへ保存
- シグナル生成
  - `features` / `ai_scores` を統合して final_score を計算し `signals` を出力
  - Bear レジーム抑制、売買（BUY/SELL）判定、エグジット条件実装
- バックテストフレームワーク
  - インメモリ DuckDB にデータをコピーして日次シミュレーション実行
  - 約定モデル（スリッページ・手数料）、ポートフォリオシミュレータ、メトリクス計算
  - CLI エントリポイント: python -m kabusys.backtest.run
- 研究用ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、ファクターの統計サマリ
- データスキーマ管理
  - DuckDB のスキーマ初期化（init_schema）・接続ユーティリティ

---

## 動作環境 / 必要パッケージ

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- その他：標準ライブラリ（urllib, datetime, logging 等）

インストール例（仮の requirements）:
```
python -m pip install duckdb defusedxml
```

プロジェクトが配布する requirements.txt がある場合はそれを使ってください。

---

## 環境変数（.env）

アプリ設定は環境変数から取得されます。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

重要な環境変数（Settings）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment (development / paper_trading / live)。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO

.env の書式はシェル互換（export KEY=val / quoted values / コメント）に対応しています。

---

## セットアップ手順

1. Python 3.10+ を用意する
2. 必要パッケージをインストール
   ```
   python -m pip install duckdb defusedxml
   ```
3. プロジェクトルートに `.env`（または `.env.local`）を作成し、必要な環境変数を設定する（上記参照）。
4. DuckDB スキーマを初期化
   - Python REPL / スクリプトで:
     ```py
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - またはテストやバックテストで ":memory:" を利用可能:
     ```py
     conn = init_schema(":memory:")
     ```
5. （任意）J-Quants からの初回データ取得やニュース収集を行う

---

## 使い方（代表的な操作例）

- DuckDB スキーマ初期化（再掲）
  ```py
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()
  ```

- 株価差分 ETL（data.pipeline から run_prices_etl などを呼び出して利用）
  ```py
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data import pipeline

  conn = init_schema("data/kabusys.duckdb")
  target = date.today()
  fetched, saved = pipeline.run_prices_etl(conn, target_date=target)
  conn.close()
  ```

- ニュース収集（RSS を取得して DB に保存）
  ```py
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  conn.close()
  ```

- 特徴量作成（feature_engineering.build_features）
  ```py
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()
  ```

- シグナル生成（strategy.signal_generator.generate_signals）
  ```py
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  conn.close()
  ```

- バックテスト（CLI）
  ```
  python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 \
      --db data/kabusys.duckdb
  ```
  - あるいは Python から run_backtest を直接呼ぶ:
    ```py
    from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.backtest.engine import run_backtest

    conn = init_schema("data/kabusys.duckdb")
    result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
    conn.close()
    print(result.metrics)
    ```

- バックテスト結果のメトリクス取得
  - run_backtest は BacktestResult を返し、history / trades / metrics が含まれます。
  - metrics は CAGR、Sharpe、MaxDrawdown、WinRate、PayoffRatio、TotalTrades を提供。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの簡易ツリー（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数設定管理
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント & 保存関数
    - news_collector.py       # RSS 収集・前処理・保存
    - schema.py               # DuckDB スキーマ初期化
    - stats.py                # zscore 等の統計ユーティリティ
    - pipeline.py             # ETL パイプライン（差分取得等）
  - research/
    - __init__.py
    - factor_research.py      # momentum / value / volatility の計算
    - feature_exploration.py  # 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py  # features 作成・正規化
    - signal_generator.py     # final_score 計算・signals 生成
  - backtest/
    - __init__.py
    - engine.py               # run_backtest（主ループ）
    - simulator.py            # 約定・ポートフォリオシミュレータ
    - metrics.py              # バックテスト評価指標
    - run.py                  # CLI エントリポイント
    - clock.py                # 模擬時計（将来用）
  - execution/                # 発注層（空 __init__、拡張地点）
  - monitoring/               # 監視系（未記載の拡張用）

---

README に記載のない詳細（例: StrategyModel.md、DataPlatform.md、BacktestFramework.md）はコード中の docstring や関数ドキュメントを参照してください。

ご不明点や README に追加したい項目（例: CI / テストの実行方法、より詳細な ETL 手順、.env.example の具体例など）があればお知らせください。