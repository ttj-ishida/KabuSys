# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、バックテスト用シミュレータなど、研究〜実運用の主要コンポーネントを提供します。

主な設計方針は次の通りです。
- ルックアヘッドバイアスを防ぐ（常に target_date 時点のデータのみを使用）
- DuckDB を用いたローカル DB（冪等性を考慮した保存）
- 外部 API 呼び出しは明示的に分離（テスト容易性）
- シンプルな統計ユーティリティ（外部依存を最小化）
- 再現性のためのトークン自動リフレッシュ・レート制御・リトライ実装

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - raw データの DuckDB への冪等保存（ON CONFLICT 処理）
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックのフレームワーク（pipeline モジュール）
- 特徴量計算（research / strategy）
  - Momentum / Volatility / Value 等のファクター計算
  - クロスセクション Z スコア正規化（data.stats.zscore_normalize）
  - features テーブルへの日付単位 UPSERT（冪等）
- シグナル生成（strategy.signal_generator）
  - ファクター + AI スコアを統合して final_score を算出
  - Bear レジーム検知、BUY / SELL 判定、signals テーブルへの書き込み（冪等）
- バックテスト（backtest）
  - インメモリで DB をコピーして日次シミュレーションを実行
  - PortfolioSimulator による擬似約定（スリッページ・手数料モデル実装）
  - メトリクス計算（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- ニュース収集（data.news_collector）
  - RSS フィード取得（SSRF 対策、サイズ制限、XML セーフパーサ）
  - raw_news / news_symbols テーブルへの保存
- DB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義と初期化ユーティリティ

---

## 要件（主な依存パッケージ）

- Python 3.10+
- duckdb
- defusedxml

必要に応じて以下も利用:
- その他標準ライブラリのみで多くの処理を実装（pandas 等非必須）

インストール（プロジェクトルートで）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージをプロジェクトとして使う場合（setup がある場合）
# pip install -e .
```

---

## 環境変数 / 設定

kabusys は .env や環境変数から設定を読み込みます（src/kabusys/config.py）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化

プロジェクトはプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索して `.env` / `.env.local` を自動読み込みします。自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

2. 環境変数を設定（`.env` を作成）
   - 上記「環境変数 / 設定」を参照して `.env` を作成してください。

3. DuckDB スキーマ初期化
   - Python REPL かスクリプトで init_schema を実行して DB を作成します。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリ自動作成されます
   conn.close()
   ```

4. （オプション）J-Quants トークン取得の確認
   - settings.jquants_refresh_token が正しく読み込まれていることを確認します。

---

## 使い方（よく使う操作例）

- バックテスト（CLI）
  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```
  出力にバックテスト結果（CAGR, Sharpe など）が表示されます。

- プログラムからバックテストを呼ぶ
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()
  # result.history, result.trades, result.metrics を利用
  ```

- features の計算（ターゲット日のファクター正規化）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024,1,31))
  print(f"upserted features: {count}")
  conn.close()
  ```

- シグナル生成
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  n = generate_signals(conn, target_date=date(2024,1,31))
  print(f"signals written: {n}")
  conn.close()
  ```

- ニュース収集（RSS）と保存
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  conn.close()
  print(results)
  ```

- J-Quants からデータ取得と保存
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  conn.close()
  ```

---

## 開発者向けヒント

- テスト時や CI では環境自動ロードを無効化する:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- Python の型注釈（3.10 の | 構文）を利用しているため Python 3.10 以上を推奨。
- J-Quants API 呼び出しは RateLimiter とリトライ（指数バックオフ）を組み込んでいます。テストではネットワーク依存部をモックしてください（例: kabusys.data.jquants_client._request や news_collector._urlopen のモック）。
- DuckDB のスキーマ初期化は冪等です。既存データを上書きしないようテーブル作成のみを行います。

---

## ディレクトリ構成 (主要ファイル)

プロジェクトの主要なソース構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存関数
    - news_collector.py      — RSS 収集・正規化・保存
    - pipeline.py            — ETL パイプライン
    - schema.py              — DuckDB スキーマ定義と init_schema
    - stats.py               — 統計ユーティリティ（Zスコア等）
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value の算出
    - feature_exploration.py — forward returns / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features の構築（正規化・フィルタ）
    - signal_generator.py    — final_score 計算・BUY/SELL 判定
  - backtest/
    - __init__.py
    - engine.py              — バックテストエンジン（run_backtest）
    - simulator.py           — PortfolioSimulator（約定モデル）
    - metrics.py             — バックテストメトリクス計算
    - run.py                 — CLI エントリポイント
    - clock.py               — SimulatedClock（将来拡張用）
  - execution/               — 発注/実行層（placeholder）
  - monitoring/              — 監視・メトリクス（placeholder）

各モジュールは docstring と ample なログメッセージで設計意図と動作を記述しています。詳細は各ファイルの冒頭 docstring と関数コメントを参照してください。

---

## ライセンス・その他

- （必要に応じてプロジェクトのライセンス情報をここに記載してください）
- セキュリティ注意: RSS フィードや外部 API を扱うため、SSRF・XML Bomb・大容量レスポンスなどへの対策を組み込んでありますが、運用環境に応じた追加チェック（プロキシ設定、ファイアウォール等）を推奨します。

---

必要であれば、README にサンプル .env.example や典型的なワークフロー（ETL → build_features → generate_signals → run_backtest）を追加できます。追加希望があれば教えてください。