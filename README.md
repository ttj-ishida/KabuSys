# KabuSys

日本株向けの自動売買／データプラットフォーム（ライブラリ）。  
DuckDB をデータ層に使い、J-Quants からのデータ収集、特徴量作成、シグナル生成、バックテスト、ニュース収集などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API からの株価・財務・カレンダーの差分取得と DuckDB への冪等保存
- 生データ（Raw）→ 整形済み（Processed）→ 戦略用特徴量（Feature）→ 発注・約定（Execution）までのデータレイヤ管理
- 研究用ファクター計算 / 特徴量正規化
- 戦略のシグナル生成（BUY / SELL）
- バックテストフレームワーク（シミュレーション、取引記録、評価指標）
- RSS ベースのニュース収集と銘柄紐付け

設計上のポイント：
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 冪等な DB 書き込み（ON CONFLICT / トランザクション）
- ネットワーク・XML・SSRF 等の防御（ニュース収集・API クライアント）
- テストしやすい設計（id_token 注入、KABUSYS_DISABLE_AUTO_ENV_LOAD 等）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新・保存関数）
  - pipeline: 差分ETL（価格・財務・カレンダー）と品質チェックのラッパー
  - news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出
  - schema: DuckDB スキーマ定義と初期化（init_schema）
  - stats: Z スコア正規化等の統計ユーティリティ
- research/
  - factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering: raw factor を正規化して features テーブルへ書き込み
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナル生成
- backtest/
  - engine: バックテストの全体フロー（run_backtest）
  - simulator: 擬似約定・ポートフォリオ管理（スリッページ・手数料モデル）
  - metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- その他
  - config: 環境変数管理（.env 自動読み込み、必須項目チェック）
  - execution / monitoring: 発注・監視に関するプレースホルダモジュール（実装を拡張）

---

## 必要条件（主な依存パッケージ）

（requirements.txt があればそちらを使用してください。なければ以下をインストールしてください）

- Python 3.10+
- duckdb
- defusedxml

インストール例（環境に合わせて仮想環境を推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発用にローカルインストールする場合:
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. Python 環境を準備（仮想環境推奨）：

   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # あれば
   pip install duckdb defusedxml
   pip install -e .
   ```

3. 環境変数設定（.env をプロジェクトルートに置くことで自動読み込みされます）
   - 自動ロードは config.py にてプロジェクトルート（.git または pyproject.toml）を検出して行われます。
   - テストや明示的無効化には `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。

   主要な環境変数（必須）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

   オプション:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH: デフォルト "data/monitoring.db"

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DuckDB スキーマ初期化：

   Python REPL かスクリプトで:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # :memory: も可
   conn.close()
   ```

   これにより必要なテーブル・インデックスが作成されます。

---

## 使い方（代表的な操作例）

- J-Quants からデータ取得して保存（概念例）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # 例: ある日付範囲の株価を取得して保存
  recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = jq.save_daily_quotes(conn, recs)
  print("saved", saved)
  conn.close()
  ```

- ETL パイプライン（差分更新）例（pipeline の関数を直接使用する）:

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  conn.close()
  ```

  pipeline モジュールは品質チェックや backfill のロジックを含みます（詳細は pipeline.run_* を参照）。

- 特徴量構築とシグナル生成（strategy API）:

  ```python
  from datetime import date
  from kabusys.strategy import build_features, generate_signals
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  d = date(2024, 3, 1)
  n = build_features(conn, target_date=d)
  print("features upserted:", n)
  s = generate_signals(conn, target_date=d)
  print("signals generated:", s)
  conn.close()
  ```

- バックテスト（CLI）:

  コマンドラインで以下のように実行できます。DB は事前に prices_daily, features, ai_scores, market_regime, market_calendar が準備されている必要があります。

  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```

- バックテスト（API）:

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(result.metrics)
  conn.close()
  ```

- ニュース収集と銘柄紐付け:

  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を取れる実装があれば渡す（銘柄コード抽出のため）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
  conn.close()
  ```

---

## 環境変数（config による取得）

config.Settings で参照される主な環境変数（必須は注記）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動ロードを無効化可能（テスト時等に便利）

config モジュールはプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読込します。既存の OS 環境変数は保護されます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル構成と役割の概観です。

- src/kabusys/
  - __init__.py
  - config.py                 : 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py       : J-Quants API クライアント + 保存関数
    - news_collector.py       : RSS → raw_news 保存、銘柄抽出
    - pipeline.py             : ETL 差分更新ロジック
    - schema.py               : DuckDB スキーマ定義・init_schema
    - stats.py                : zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py      : momentum/value/volatility ファクター計算
    - feature_exploration.py  : forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py  : features テーブル構築（正規化・フィルタ適用）
    - signal_generator.py     : final_score 計算・BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py               : run_backtest（メインループ）
    - simulator.py            : PortfolioSimulator（約定・履歴管理）
    - metrics.py              : バックテスト評価指標
    - run.py                  : CLI エントリポイント
    - clock.py                : SimulatedClock（将来拡張用）
  - execution/                : 発注関連（プレースホルダ）
  - monitoring/               : 監視関連（プレースホルダ）

---

## 開発・テストのヒント

- テスト時に .env 自動読み込みを止めたい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- DB を叩くユニットテストでは duckdb のインメモリ接続（":memory:"）を使うと便利です。
- ネットワーク呼び出し（J-Quants, RSS）はモック注入可能な設計になっています（例: jquants_client._request の差し替え、news_collector._urlopen のモック）。

---

## 参考・補足

- 各モジュール内に詳細な docstring があり、設計方針や数値の由来（閾値やウィンドウ長）も記載しています。実装やパラメータ変更時は該当ソースを参照してください。
- データベーススキーマは data/schema.py に集中して定義されています。スキーマ変更はここで行い、init_schema を使って適用してください。

---

必要であれば README にサンプル .env.example、requirements.txt の推奨内容、CI やデプロイ手順（systemd / Airflow などでの ETL スケジューリング）を追加できます。どの情報を優先して追加しますか？