# KabuSys

日本株アルゴリズムトレーディング基盤（リサーチ / シグナル生成 / バックテスト / データ収集）の軽量ライブラリです。DuckDB をデータストアとして用い、J-Quants や RSS などからデータを収集し、特徴量計算・シグナル生成・バックテストを行うモジュール群を提供します。

## 主要機能（ハイライト）
- データ収集
  - J-Quants API クライアント（株価日足・財務データ・市場カレンダーの取得、リトライ・レート制限・トークン更新対応）
  - RSS ベースのニュース収集器（正規化・SSRF対策・トラッキングパラメータ除去）
- データ ETL / 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility / Liquidity）
  - ファクター探索（将来リターン計算 / IC 計算 / 統計サマリー）
  - Zスコア正規化ユーティリティ
- 戦略 / シグナル生成
  - 特徴量作成（feature_engineering.build_features）
  - 最終スコア計算と BUY/SELL シグナル生成（strategy.signal_generator.generate_signals）
  - Bear レジーム抑制や AI スコア統合対応
- ポートフォリオ構築
  - 候補選定、等配分 / スコア配分、リスクベースのポジションサイジング
  - セクター集中制限、レジーム乗数
- バックテスト
  - シンプルなポートフォリオシミュレータ（約定・スリッページ・手数料モデル、日次スナップショット）
  - バックテストエンジン（データを一時インメモリにコピーして安全に実行）
  - パフォーマンスメトリクス（CAGR、Sharpe、Max Drawdown、勝率等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- 実運用（execution / monitoring）用の骨組み（モジュールエクスポートあり）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に | 演算子を使用）
- DuckDB が使用できること（DuckDB Python パッケージを利用）

1. リポジトリをクローン / 取得
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要最低限（コードベース参照）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 実際のプロジェクトでは requirements.txt や pyproject.toml を提供している想定なので、そちらからインストールしてください:
     - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 必須の環境変数（config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（実運用用）
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — Slack のチャネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development / paper_trading / live) — default: development
     - LOG_LEVEL (DEBUG/INFO/...) — default: INFO
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```

5. データベース初期化
   - 本リポジトリでは schema 初期化関数が kabusys.data.schema.init_schema(db_path) として想定されています（実装ファイルはプロジェクト内にあるはずです）。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # 必要なテーブルの作成や初期マスタ投入を行う
     conn.close()
     ```

---

## 使い方（代表的な操作）

以下は主要機能を呼び出す例です。実行前に DuckDB に必要なテーブル（prices_daily、raw_prices、raw_financials、features、ai_scores、market_regime、market_calendar など）が準備されている必要があります。

1. バックテスト（CLI）
   - コマンド例:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --db data/kabusys.duckdb \
       --cash 10000000 \
       --allocation-method risk_based
     ```
   - 必要な DB テーブル:
     - prices_daily, features, ai_scores, market_regime, market_calendar など

2. バックテスト（プログラムから）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.backtest.engine import run_backtest

   conn = init_schema("data/kabusys.duckdb")
   result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
   conn.close()

   # 結果の利用
   print(result.metrics.cagr, result.metrics.sharpe_ratio)
   ```

3. ファクター構築（特徴量作成）
   ```python
   from datetime import date
   from kabusys.strategy.feature_engineering import build_features
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2024, 1, 31))
   conn.close()
   print(f"built features for {count} codes")
   ```

4. シグナル生成
   ```python
   from datetime import date
   from kabusys.strategy.signal_generator import generate_signals
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   n = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
   conn.close()
   print(f"generated {n} signals")
   ```

5. ニュース収集（RSS）と保存
   ```python
   from kabusys.data.jquants_client import _get_cached_token, fetch_listed_info
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")

   # 既知銘柄リストの取得（例: fetch_listed_info の結果を使う）
   listed = fetch_listed_info()  # date 指定可能
   known_codes = {r['code'] for r in listed}

   results = run_news_collection(conn, known_codes=known_codes)
   print(results)

   conn.close()
   ```

6. J-Quants からのデータ取得と保存
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   records = fetch_daily_quotes(date_from=..., date_to=...)
   saved = save_daily_quotes(conn, records)
   conn.close()
   print(f"saved {saved} rows")
   ```

---

## 環境変数の自動読み込みについて
- パッケージ内の `kabusys.config` はプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を順に読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - data/
    - jquants_client.py               — J-Quants API クライアント / 保存ユーティリティ
    - news_collector.py               — RSS ニュース収集・保存
    - ... (schema, stats, calendar_management 等が想定される)
  - research/
    - factor_research.py              — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py          — 将来リターン / IC / 統計
  - strategy/
    - feature_engineering.py          — features テーブル構築
    - signal_generator.py             — final_score 計算・BUY/SELL 生成
  - portfolio/
    - portfolio_builder.py            — 候補選定 / 重み計算
    - position_sizing.py              — 株数決定・丸め・集計キャップ
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
    - __init__.py
  - backtest/
    - engine.py                       — バックテスト エンジン（全体ループ）
    - simulator.py                    — 擬似約定シミュレータ
    - metrics.py                      — バックテスト指標計算
    - run.py                          — CLI エントリポイント
    - clock.py
  - portfolio/
  - execution/                        — 実運用向け発注インターフェース（骨格）
  - monitoring/                       — 監視 / Slack 通知等（骨格）

（注: 上記はコードベース内の主要モジュールを抜粋したもので、実際のファイルは他にも存在する可能性があります。）

---

## 実運用上の注意点
- Look-ahead バイアス対策: features / signals / raw データは「いつ利用可能になったか（fetched_at）」を考慮して構築してください。J-Quants クライアント側で fetched_at を UTC で記録する設計です。
- バックテストでは本番 DB を汚さないために、内部でインメモリ DuckDB に必要なテーブルをコピーして処理します（_build_backtest_conn）。
- Bear レジームでは BUY シグナルを抑制する設計になっています（signal_generator 参照）。
- news_collector は SSRF 対策・gzip 解凍サイズチェック等の安全対策を実装済みですが、運用時はネットワーク設定やタイムアウト等を環境に合わせて調整してください。
- 実運用で注文を出す場合は、kabu ステーション API 周り（execution モジュール）の追加実装が必要です（現在は骨格が提供されています）。

---

必要であれば、README に
- DB スキーマ定義（テーブル一覧とカラム）
- サンプル .env.example
- CI / テストの実行手順
- よくあるトラブルシュート（トークン更新失敗や API rate limit）
を追加できます。どの情報を優先して追記するか教えてください。