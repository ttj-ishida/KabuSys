# KabuSys

日本株向けの自動売買 / 研究プラットフォーム。  
DuckDB をデータストアとして、データ収集（J-Quants）、特徴量生成、シグナル生成、バックテスト、ニュース収集など一連の処理を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「外部依存の最小化（研究コードと実行コードの分離）」です。

---

## 特徴（機能一覧）

- データ取得・保存
  - J-Quants API クライアント（差分取得・ページネーション・リトライ・トークン自動リフレッシュ対応）
  - 株価（OHLCV）、財務データ、JPX マーケットカレンダーの収集と DuckDB への冪等保存
- ETL パイプライン
  - 差分更新・バックフィル対応、品質チェックとの連携（pipeline モジュール）
- ニュース収集
  - RSS フィードの安全な取得（SSRF対策・gzip制限・XML脆弱性対策）と raw_news 保存、記事 → 銘柄コード紐付け
- 研究・ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB SQL + Python）
  - ファクター探索用ユーティリティ（forward returns, IC, summary）
  - Zスコア正規化ユーティリティ
- 特徴量エンジニアリング
  - research で計算した生ファクターを正規化・結合して `features` テーブルへ保存（冪等）
  - ユニバースフィルタ（株価・流動性）を実装
- シグナル生成
  - features と ai_scores を統合し final_score を計算。BUY/SELL シグナルを生成して `signals` テーブルへ保存
  - Bear レジーム抑制、エグジット（ストップロス／スコア低下）判定を実装
- バックテスト
  - インメモリの DuckDB にデータをコピーして日次ループでシミュレーション
  - PortfolioSimulator（スリッページ・手数料モデル）、トレード記録、日次スナップショット
  - 評価指標（CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- スキーマ管理
  - DuckDB のスキーマ定義・初期化関数（init_schema）

---

## 動作要件

- Python 3.10 以上（型ヒントに `X | None` を使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- その他、J-Quants API 利用時にはネットワーク接続と有効なリフレッシュトークンが必要

（プロジェクト配布に requirements.txt があればそちらを使用してください）

---

## 環境変数（必須・任意）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。主な設定項目:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（execution 層で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルト有り）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG/INFO/...)
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合は `1`

設定値は kabusys.config.settings から取得します（例: settings.jquants_refresh_token）。

---

## セットアップ手順

1. リポジトリをクローン / 配布アーカイブを展開

2. 必要な Python バージョンを用意（推奨: 3.10+）

3. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

4. 依存パッケージをインストール（例）
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそれを使用してください）

5. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を設定
   - 例 .env:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

6. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ DB も可
     ```

---

## 使い方（主な例）

- バックテスト（CLI）
  - 前提: DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）があること
  - 実行例:
    ```
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
    ```
  - 結果: コンソールに基本的なメトリクスが出力されます。内部的に generate_signals を用いた日次ループでシミュレーションします。

- スキーマ初期化（REPL）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()
  ```

- J-Quants データ取得 + 保存（例）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,2,1))
  saved = jq.save_daily_quotes(conn, recs)
  conn.close()
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  conn.close()
  ```

- 特徴量構築 / シグナル生成（DuckDB 接続が必要）
  ```python
  from kabusys.strategy import build_features, generate_signals
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024,2,20))
  s = generate_signals(conn, target_date=date(2024,2,20))
  conn.close()
  ```

- ETL（パイプライン）例
  - pipeline モジュールには差分取得 / バックフィルを考慮した run_prices_etl 等のジョブがあります。使用例は pipeline.run_prices_etl を参照してください（DuckDB 接続と target_date を渡して実行）。

---

## 主なモジュールとディレクトリ構成

プロジェクトの主要なファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント、保存関数
    - news_collector.py                — RSS 取得・前処理・保存
    - schema.py                        — DuckDB スキーマ定義と init_schema
    - stats.py                         — zscore 等の統計ユーティリティ
    - pipeline.py                      — ETL パイプライン（差分取得・品質チェック）
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算（momentum, volatility, value）
    - feature_exploration.py           — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py           — features テーブル生成（正規化・ユニバースフィルタ）
    - signal_generator.py              — final_score 計算と signals 生成
  - backtest/
    - __init__.py
    - engine.py                        — run_backtest（インメモリコピー、日次ループ）
    - simulator.py                     — PortfolioSimulator（約定・スリッページ・評価）
    - metrics.py                       — バックテスト評価指標計算
    - run.py                           — CLI ラッパー
    - clock.py                         — 将来の拡張用模擬時計
  - execution/                          — 発注/実行関連（空 __init__ 等）
  - monitoring/                         — 監視関連（DB path など設定）

DuckDB スキーマは data/schema.py にすべて定義されています（raw / processed / feature / execution レイヤー）。

---

## 開発メモ / 注意点

- ルックアヘッドバイアス防止のため、計算・シグナル生成は target_date 時点で利用可能なデータのみを参照する設計です。
- 多くの保存処理は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）として設計されています。ETL の再実行が安全になるよう配慮しています。
- J-Quants API はレート制限（120 req/min）に従うよう内部でスロットリングを行います。
- RSS 取得は SSRF や XML 脆弱性対策、レスポンスサイズ制限など安全対策を実装しています。
- DuckDB のバージョン差で一部機能（ON DELETE CASCADE 等）が未サポートである旨をテーブルコメントに残しています。運用時には DuckDB のバージョンと互換性を確認してください。

---

## 参考：よく使う API / エントリポイント

- Schema 初期化
  - kabusys.data.schema.init_schema(db_path)
- J-Quants API
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(conn, records)
- ニュース収集
  - kabusys.data.news_collector.run_news_collection(conn, sources, known_codes)
- 研究 / ファクター
  - kabusys.research.calc_momentum / calc_volatility / calc_value
- 特徴量・シグナル
  - kabusys.strategy.build_features(conn, date)
  - kabusys.strategy.generate_signals(conn, date)
- バックテスト
  - python -m kabusys.backtest.run --start ... --end ... --db path/to/db

---

必要であれば README に「セットアップ用の .env.example」や「CI 用のコマンド」「実運用での注意点（Slack 通知設定や監視）」などのセクションを追加できます。ご希望があれば追記します。