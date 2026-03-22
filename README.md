# KabuSys

日本株向けの自動売買／データプラットフォーム基盤（リサーチ・ETL・特徴量生成・シグナル生成・バックテスト）です。  
このリポジトリはデータ取得（J‑Quants 等）、DuckDB を使ったデータ格納、ファクター計算、シグナル生成、擬似約定によるバックテストまでを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次のレイヤーを想定した設計になっています。

- Raw Layer: API から取得した生データ（株価、財務、ニュース、実行ログ 等）
- Processed Layer: 日次 OHLCV や整形済み財務データ、マーケットカレンダー
- Feature Layer: 戦略・AI 用特徴量（features / ai_scores / market_regime 等）
- Execution Layer: シグナル / 注文 / 約定 / ポジション 等

各機能はモジュール化されており、ETL（差分取得 + 品質チェック）、特徴量エンジニアリング、シグナル生成、バックテストフレームワーク、ニュース収集などを組み合わせて利用できます。

---

## 主な機能一覧

- データ取得
  - J-Quants API クライアント（ページネーション・トークンリフレッシュ・レート制御・リトライ）
  - RSS ベースのニュース収集（SSRF 対策／トラッキングパラメータ除去／記事IDのハッシュ化）
- ETL / パイプライン
  - 差分更新（最終取得日からの再取得／バックフィル）
  - DuckDB への冪等保存（ON CONFLICT ロジック）
  - データ品質チェック（欠損・スパイク・重複 等、quality モジュールを想定）
- 研究（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリー
  - Z スコア正規化ユーティリティ
- 戦略（Strategy）
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals）：複数コンポーネントの重み付け集約、Bear レジーム抑制、売買シグナルの冪等保存
- バックテスト
  - 日次ループによるシミュレーション（スリッページ・手数料モデルを実装）
  - ポートフォリオシミュレータ（擬似約定、マーク・トゥ・マーケット、トレード履歴）
  - バックテスト評価指標（CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- スキーマ管理
  - DuckDB 用スキーマ定義と初期化（init_schema）

---

## 必要条件

- Python 3.10 以上（型注釈に `|` 型が使われているため）
- 主な依存パッケージ（実行環境に合わせて適宜インストールしてください）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API／RSS フィード等）を利用する場合は外部接続が必要

※ requirements.txt や pyproject.toml がある場合はそちらに従ってください。

---

## 環境変数（主要）

アプリケーションは環境変数（または .env / .env.local）から設定を読み込みます。自動ロードはプロジェクトルートの .git / pyproject.toml を探索して行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に必要な環境変数:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- kabuステーション API（発注連携がある場合）
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- Slack（通知等）
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- データベースパス
  - DUCKDB_PATH (省略時: data/kabusys.duckdb)
  - SQLITE_PATH (監視用 DB 等。省略時: data/monitoring.db)
- 実行環境 / ログ
  - KABUSYS_ENV: development | paper_trading | live (省略時: development)
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL (省略時: INFO)

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをチェックアウトし、仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   # またはプロジェクトの依存ファイルがある場合はそれを使う
   # pip install -r requirements.txt
   ```

3. 環境変数を設定（.env をプロジェクトルートに作成）

4. DuckDB スキーマの初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   - メモリ DB を使う場合は `":memory:"` を指定できます。

---

## 使い方（代表的な操作）

以下は典型的なワークフローの例です。

1. データベース初期化（上記参照）

2. 株価・財務データ取得（J-Quants）と保存
   - jquants_client の `fetch_*` と `save_*` を組み合わせて使用します。
   - 例（簡略）:
     ```python
     from kabusys.data import jquants_client as jq
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     records = jq.fetch_daily_quotes(date_from=...)
     jq.save_daily_quotes(conn, records)
     conn.close()
     ```

3. ニュース収集（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # known_codes: 銘柄抽出に使う有効コード集合（任意）
   result = run_news_collection(conn, sources=None, known_codes=None, timeout=30)
   conn.close()
   ```

4. 特徴量の構築（features テーブルへ UPSERT）
   ```python
   from datetime import date
   import duckdb
   from kabusys.strategy import build_features

   conn = duckdb.connect("data/kabusys.duckdb")
   n = build_features(conn, target_date=date(2024, 01, 05))
   print(f"features updated: {n}")
   conn.close()
   ```

5. シグナル生成（signals テーブルへ保存）
   ```python
   from datetime import date
   import duckdb
   from kabusys.strategy import generate_signals

   conn = duckdb.connect("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2024, 01, 05), threshold=0.6)
   print(f"signals written: {total}")
   conn.close()
   ```

6. バックテスト（CLI）
   - DB が事前に prices_daily / features / ai_scores / market_regime / market_calendar を満たしている必要があります（run_backtest の docstring 参照）。
   ```
   python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2024-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
   ```
   - または API を直接呼ぶ:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.backtest.engine import run_backtest
     conn = init_schema("data/kabusys.duckdb")
     res = run_backtest(conn, start_date, end_date)
     print(res.metrics)
     conn.close()
     ```

---

## ディレクトリ構成（抜粋）

リポジトリの主要なモジュール構成:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings
  - data/
    - __init__.py
    - schema.py                — DuckDB スキーマ定義 / init_schema
    - jquants_client.py        — J-Quants API クライアント（fetch/save）
    - news_collector.py        — RSS ニュース収集・保存
    - pipeline.py              — ETL パイプライン制御（差分更新等）
    - stats.py                 — z-score 正規化など統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py       — モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py   — 将来リターン計算、IC、summary、rank
  - strategy/
    - __init__.py
    - feature_engineering.py   — features 作成（Z スコア正規化、ユニバースフィルタ）
    - signal_generator.py      — final_score 計算、BUY/SELL 判定、signals 書き込み
  - backtest/
    - __init__.py
    - engine.py                — run_backtest（バックテスト制御）
    - simulator.py             — PortfolioSimulator（擬似約定）
    - metrics.py               — バックテスト評価指標計算
    - run.py                   — CLI エントリポイント
    - clock.py                 — 将来拡張用の模擬時計
  - execution/                 — 発注・実行ロジック（プレースホルダ）
  - monitoring/                — 監視・通知（プレースホルダ）
  - research/                  — 研究用ユーティリティ（上記参照）

---

## 開発・テスト時のヒント

- 自動環境変数ロードはプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を読み込みます。テストで自動ロードを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の初期化は冪等です。既存テーブルがあればスキップされます。
- ニュース収集では defusedxml を利用して XML 関連の脆弱性対策を行っているため、XML 構造のテストに注意してください。
- J-Quants API 呼び出しはレートリミット（120 req/min）を守る設計です。大量データ取得を行う際は時間的余裕を持ってください。
- 型アノテーションやログ出力が多いので、開発中は LOG_LEVEL を DEBUG にして詳細ログを確認するとよいです。

---

## 注意事項 / TODO

- 一部の機能（Execution 層の外部 API 呼び出しや監視・通知の詳細）はプレースホルダの実装です。実運用で接続する場合はさらに実装・安全性検証が必要です。
- 実際の資金を扱う際は本番用設定（KABUSYS_ENV=live）や発注 API の認証・二重チェックを十分に行ってください。
- バックテストはヒストリカルデータの整合性に依存します。ETL と品質チェックを組み合わせてデータ品質を担保してください。

---

必要であれば README にサンプル .env.example、より詳細な CLI オプション一覧、各 DB テーブルのスキーマ要約（columns）やユースケース別の典型的なコマンド集を追加できます。どの情報を優先して追記しましょうか？