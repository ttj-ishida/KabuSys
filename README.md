# KabuSys

日本株向け自動売買プラットフォームのリファレンス実装です。  
データ取得（J‑Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、およびシンプルな発注/シミュレーション機能を含むモジュール群で構成されています。

主な設計方針は以下です：
- ルックアヘッドバイアス回避（計算・シグナルは target_date 時点の情報のみ使用）
- DuckDB を用いたローカル DB スキーマ（冪等な INSERT/UPSERT）
- 最小限の外部依存（duckdb, defusedxml 等）
- テスト容易性（id_token 注入、in‑memory DB 等）

---

## 機能一覧

- データ取得（J‑Quants API クライアント）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの取得（ページネーション、レート制御、リトライ、トークン自動リフレッシュ対応）
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックフック（quality モジュール想定）
- データスキーマ（DuckDB）
  - raw / processed / feature / execution 層のテーブル定義と初期化
- 研究（research）
  - ファクター計算（momentum / volatility / value）、将来リターン計算、IC・統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクターの正規化・ユニバースフィルタ・features テーブルへの保存
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成、Bear レジーム抑制、signals テーブルへの保存
- バックテスト（backtest）
  - PortfolioSimulator（擬似約定、スリッページ・手数料モデル）、バックテストエンジン、メトリクス計算、CLI 実行用スクリプト
- ニュース収集（data.news_collector）
  - RSS 取得、前処理、記事保存、銘柄コード抽出（SSRF対策、gzip/サイズ制限、XML攻撃対策）
- J‑Quants 用保存ユーティリティ（raw_prices, raw_financials, market_calendar などに冪等で保存）

---

## 必要条件（概略）

- Python 3.9+（アノテーション・typing 機能を利用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, logging, datetime, pathlib 等）を使用

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

プロジェクトで使用する追加のパッケージがあれば requirements.txt を用意してインストールしてください。

---

## 環境変数 / 設定

パッケージ起動時に `.env` / `.env.local` を自動で読み込みます（プロジェクトルートは .git または pyproject.toml により探索）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（Settings で参照される）:

- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用 DB）パス（省略時: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

サンプル .env（プロジェクトルートに配置）:
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

## セットアップ手順（例）

1. リポジトリをクローンして仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   ```

2. 環境変数を設定（.env をプロジェクトルートに作成）
   - 上記サンプルを参考に必要な値を設定してください。

3. DuckDB スキーマ初期化
   ```python
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```
   または、インメモリ DB を試す場合:
   ```python
   python -c "from kabusys.data.schema import init_schema; init_schema(':memory:')"
   ```

4. （任意）market calendar などの初期データを ETL で取り込む（下記参照）

---

## 使い方

以下は主要機能の実行例です。各関数はモジュールから直接呼び出すか、提供された CLI を利用します。

- DuckDB 接続の取得 / スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema('data/kabusys.duckdb')  # 初期化して接続
  # あるいは既存 DB に接続（スキーマ初期化しない）
  conn2 = get_connection('data/kabusys.duckdb')
  ```

- J‑Quants から日次株価を取得して保存（jquants_client）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema('data/kabusys.duckdb')
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print('saved', saved)
  conn.close()
  ```

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema('data/kabusys.duckdb')
  known_codes = {'7203','6758','9984'}  # 既知銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- 特徴量の生成（features テーブルへ書き込み）
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema('data/kabusys.duckdb')
  count = build_features(conn, target_date=date(2024,1,31))
  print('features upserted:', count)
  conn.close()
  ```

- シグナル生成（signals テーブルへ書き込み）
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema('data/kabusys.duckdb')
  num = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
  print('signals written:', num)
  conn.close()
  ```

- バックテスト（プログラム実行）
  - CLI（推奨）:
    ```bash
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
    ```
  - プログラムから:
    ```python
    from kabusys.backtest.engine import run_backtest
    from kabusys.data.schema import init_schema
    from datetime import date

    conn = init_schema('data/kabusys.duckdb')
    res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
    print(res.metrics)
    conn.close()
    ```

- ETL パイプライン（差分更新）の例（pipeline モジュール）
  - pipeline モジュールには run_prices_etl 等の関数があります（J‑Quants 連携）。呼び出し例:
    ```python
    from kabusys.data.pipeline import run_prices_etl, ETLResult
    from kabusys.data.schema import init_schema
    from datetime import date

    conn = init_schema('data/kabusys.duckdb')
    fetched, saved = run_prices_etl(conn, target_date=date.today())
    print('fetched:', fetched, 'saved:', saved)
    conn.close()
    ```

注意: 実運用では ETL を定期ジョブ（cron / Airflow 等）で回し、features → generate_signals → execution 層へ連携するワークフローを構成します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py              — J‑Quants API クライアント（fetch/save）
      - news_collector.py              — RSS ベースのニュース収集
      - pipeline.py                    — ETL パイプライン（差分更新等）
      - schema.py                      — DuckDB スキーマ定義・初期化
      - stats.py                       — zscore_normalize 等統計ユーティリティ
    - research/
      - __init__.py
      - factor_research.py             — momentum/volatility/value の計算
      - feature_exploration.py         — forward returns / IC / summary
    - strategy/
      - __init__.py
      - feature_engineering.py         — features の正規化・保存
      - signal_generator.py            — final_score 計算・signals 書き込み
    - backtest/
      - __init__.py
      - engine.py                      — run_backtest 実装
      - simulator.py                   — PortfolioSimulator（擬似約定）
      - metrics.py                     — バックテスト指標計算
      - run.py                         — CLI エントリポイント
      - clock.py
    - execution/                         — 発注・execution 層（未実装ファイル群）
    - monitoring/                        — 監視・Slack 連携等（想定）
    - research/                          — 研究用ユーティリティ（factor_research 等）
    - backtest/                          — バックテスト関連

---

## 開発・テストに関するメモ

- .env の自動読み込みはプロジェクトルート検出に依存します（.git / pyproject.toml）。テストで自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のインメモリ DB を利用してユニットテストを容易に行えます（init_schema(":memory:")）。
- network / API 呼び出しはモジュールの関数単位で id_token の注入や _urlopen のモック差替えが可能なよう設計されています。

---

## よくある質問（FAQ）

Q: schema の初期化でファイルの親ディレクトリがないとエラーになりますか？  
A: init_schema() は親ディレクトリを自動作成します（":memory:" は例外）。

Q: J‑Quants のレート制限はどうなっていますか？  
A: jquants_client はデフォルトで 120 req/min に従う固定間隔スロットリングを行います。内部で指数バックオフとリトライも実装済みです。

Q: シグナル生成や特徴量生成は冪等ですか？  
A: はい。build_features / generate_signals は target_date 単位で既存データを削除してから挿入するため繰り返し実行しても整合性が保たれます（トランザクション処理）。

---

## 参考・今後の拡張案

- execution 層の実装（kabu API 実行、order 管理）
- Slack 通知や監視アラートの実装（monitoring）
- AI スコア計算モジュール（ai_scores 生成）
- パラメータ最適化／ウォークフォワード評価のための追加ツール

---

README の補足・改善依頼やコードの追加・修正を歓迎します。問題報告やプルリクエストはリポジトリの issue/PR で行ってください。