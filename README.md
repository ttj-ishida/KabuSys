# KabuSys

日本株向けの自動売買（データ取得・特徴量生成・シグナル生成・バックテスト）ライブラリ／フレームワークです。  
DuckDB を中心にデータ基盤を構築し、研究（research）→特徴量作成（strategy）→シグナル生成→バックテスト／実運用のレイヤーを分離して実装しています。

主な設計方針：
- ルックアヘッドバイアスを回避（各処理は target_date 時点のデータのみを参照）
- DuckDB を用いた冪等性のあるデータ保存（ON CONFLICT / トランザクション）
- テストしやすい（依存注入、id_token 注入等）
- ネットワークリトライ・レート制御・SSRF対策など実運用を意識した実装

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（差分取得 / ページネーション / トークン自動更新 / レート制御）
  - RSS ニュース収集（SSRF対策・トラッキング除去・記事ID生成・銘柄抽出）
  - DuckDB スキーマ定義・初期化（init_schema）
- データパイプライン（ETL）
  - 差分更新、保存、品質チェック（pipeline モジュール）
- 研究用ユーティリティ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC計算・統計サマリー（feature_exploration）
  - Zスコア正規化など統計ユーティリティ
- 戦略（strategy）
  - 特徴量エンジニアリング（build_features）
  - シグナル生成（generate_signals） — final_score 計算、Bear 判定、BUY/SELL 生成
- バックテスト
  - シミュレータ（PortfolioSimulator）
  - バックテストエンジン（run_backtest）と CLI（python -m kabusys.backtest.run）
  - メトリクス計算（CAGR, Sharpe, MaxDD, 勝率 等）
- 実行層（execution）・モニタリング（placeholders／拡張用）

---

## 必要条件／インストール

- Python 3.10 以上（PEP 604 の型構文などを使用）
- 推奨パッケージ（最小限）
  - duckdb
  - defusedxml

例（仮想環境を使った手順）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# またはパッケージ化されている場合:
# pip install -e .
```

※ requirements.txt / packaging がある場合はそちらを使用してください。

---

## 環境変数（.env）

プロジェクトは .env / .env.local / OS 環境変数から設定を読み込みます（自動読み込み）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV: 設定モード（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（最小ワークフロー）

1. リポジトリをクローンして仮想環境を作成・依存をインストール
2. 環境変数を .env に設定（上記参照）
3. DuckDB スキーマ初期化
   - Python REPL などで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ディレクトリが自動作成されます
     conn.close()
     ```
4. J-Quants データ取得（ETL）やニュース収集、特徴量生成を実行
   - ETL の例（Python スクリプト内で）:
     ```python
     from datetime import date
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_prices_etl, run_prices_etl  # 他の ETL 関数も同様

     conn = init_schema("data/kabusys.duckdb")
     # 例: 当日までの株価差分 ETL
     from datetime import date
     target = date.today()
     fetched, saved = run_prices_etl(conn, target_date=target)
     conn.close()
     ```
   - ニュース収集例:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.data.news_collector import run_news_collection
     conn = init_schema("data/kabusys.duckdb")
     res = run_news_collection(conn, known_codes={"7203","6758"})
     conn.close()
     ```
5. 特徴量作成 / シグナル生成
   - build_features / generate_signals を呼び出す（DuckDB 接続と target_date を渡す）
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.strategy import build_features, generate_signals
     from datetime import date
     conn = init_schema("data/kabusys.duckdb")
     d = date(2024, 1, 31)
     n = build_features(conn, d)
     s = generate_signals(conn, d)
     conn.close()
     ```
6. バックテスト（CLI 例）
   - DB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が揃っていれば実行可能:
     ```bash
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2024-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
     ```

---

## 使い方（主な API / コマンド）

- DB スキーマ初期化
  - kabusys.data.schema.init_schema(db_path)

- データ取得 / 保存
  - kabusys.data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(...)
  - kabusys.data.jquants_client.fetch_financial_statements(...) / save_financial_statements(...)
  - kabusys.data.jquants_client.fetch_market_calendar(...) / save_market_calendar(...)

- ニュース収集
  - kabusys.data.news_collector.fetch_rss(url, source) → 記事リスト
  - kabusys.data.news_collector.save_raw_news(conn, articles)
  - run_news_collection(...) で一括収集＋保存＋銘柄紐付け

- 特徴量・シグナル
  - kabusys.strategy.build_features(conn, target_date)
  - kabusys.strategy.generate_signals(conn, target_date, threshold=None, weights=None)

- バックテスト
  - run_backtest(conn, start_date, end_date, initial_cash=..., ...) → BacktestResult
  - CLI: python -m kabusys.backtest.run --start ... --end ... --db path/to/duckdb

- 研究用ユーティリティ
  - kabusys.research.calc_forward_returns(...)
  - kabusys.research.calc_ic(...)
  - kabusys.research.factor_summary(...)

---

## ディレクトリ構成（主要ファイル）

（リポジトリの `src/kabusys/` を起点）

- kabusys/
  - __init__.py
  - config.py                     — 環境変数管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - news_collector.py          — RSS ニュース取得＆保存、銘柄抽出
    - schema.py                  — DuckDB スキーマ/初期化
    - stats.py                   — Zスコア等統計ユーティリティ
    - pipeline.py                — ETL パイプライン（差分取得・品質チェック）
  - research/
    - __init__.py
    - factor_research.py         — momentum/value/volatility 等ファクター算出
    - feature_exploration.py     — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py    — ファクター正規化・features 作成
    - signal_generator.py       — final_score 計算・BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py                 — バックテストエンジン（run_backtest）
    - simulator.py              — ポートフォリオシミュレータ
    - metrics.py                — バックテスト評価指標
    - run.py                    — CLI エントリポイント
    - clock.py                  — 将来用の模擬時計
  - execution/                  — 発注 API 連携（実運用層）
  - monitoring/                 — 監視 / メトリクス（拡張用）

（上記は主要ファイルを抜粋しています）

---

## 開発メモ / 注意点

- Python 3.10+ を想定しています（型ヒントに PEP 604 形式を使用）。
- DuckDB のバージョンによっては外部キーや一部動作（ON DELETE 等）のサポート違いがあり、コード内にその旨の注記があります。
- J-Quants API 呼び出しはレート制御・リトライ・トークン自動更新を実装しています。実行環境の API 制限に注意してください。
- ニュース収集は defusedxml を使用し、SSRF / XML Bomb 等の対策が入っています。外部 URL の扱いにも注意してください。
- 実運用（ライブ口座）で利用する場合は KABUSYS_ENV を `live` に設定し、安全面・法的要件・注文管理を十分に確認してください。

---

この README はコードベースの主要な用途と起動手順・アーキテクチャをまとめたものです。詳しい実装やパラメータのチューニングは各モジュール（data/, research/, strategy/, backtest/）の docstring を参照してください。必要であれば、README にサンプルスクリプトや CI / テスト手順を追記します。