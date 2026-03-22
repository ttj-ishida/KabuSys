# KabuSys

日本株向けの自動売買システム（ライブラリ / バックテスト / データパイプライン）。  
このリポジトリはデータ取得（J-Quants）、ETL、リサーチ（ファクター計算・探索）、特徴量生成、シグナル生成、バックテストを含むモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアス防止：target_date 時点のデータのみを使用
- 冪等性：DB への INSERT は基本的に ON CONFLICT（アップサート）で重複回避
- 外部 API 呼び出しは data 層に限定し、戦略・バックテスト層は副作用を持たない設計

---

## 機能一覧
- データ取得・保存
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS ニュース収集（SSRF 対策・トラッキングパラメータ除去）
  - DuckDB スキーマ初期化・スキーマ管理
- ETL / パイプライン
  - 差分更新（バックフィル対応）、保存、品質チェック（quality モジュール）
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 特徴量エンジニアリング
  - 生ファクターの正規化（Zスコア）、ユニバースフィルタ、features テーブルへの保存
- シグナル生成
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成
  - Bear レジーム判定やエグジット（ストップロス等）処理
- バックテスト
  - 日次ループによるポートフォリオシミュレーション（スリッページ／手数料モデル）
  - パフォーマンス指標（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio）
  - CLI での実行（python -m kabusys.backtest.run）

---

## 要件（想定）
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリで多くを実装していますが、実行環境には上記パッケージを入れてください。

インストール例（仮）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発インストールがある場合：
# pip install -e .
```

---

## セットアップ手順

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージのインストール
   - pip install duckdb defusedxml

3. DuckDB スキーマ初期化
   - Python から:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # または ":memory:"
     conn.close()
     ```
   - これにより必要なテーブル群が作成されます（冪等）。

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（kabusys.config が起動時に読み込み）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabu API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db

`.env.example` の例:
```
# .env.example
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な操作例）

- DuckDB スキーマ初期化（コマンドライン or スクリプト）
  ```python
  from kabusys.data.schema import init_schema
  init_schema("data/kabusys.duckdb")
  ```

- J-Quants から日足を取得して保存（概念）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- ETL（パイプライン）の個別ジョブ（例: prices ETL）
  - data.pipeline.run_prices_etl を利用（詳細な引数は関数定義参照）

- 特徴量作成
  ```python
  from kabusys.strategy import build_features
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  cnt = build_features(conn, target_date=date(2024, 1, 31))
  print("upserted:", cnt)
  conn.close()
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  conn = duckdb.connect("data/kabusys.duckdb")
  n = generate_signals(conn, target_date=date(2024, 1, 31))
  print("written signals:", n)
  conn.close()
  ```

- バックテスト（CLI 実行）
  ```
  python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
  ```
  主要オプション:
  - --start, --end: バックテスト期間（YYYY-MM-DD）
  - --cash: 初期資金
  - --slippage, --commission: スリッページ・手数料率
  - --max-position-pct: 1銘柄あたりの最大比率
  - --db: DuckDB ファイルパス（事前に prices_daily, features, ai_scores, market_regime, market_calendar が必要）

- バックテスト API 呼び出し（プログラム）
  ```python
  from kabusys.backtest.engine import run_backtest
  conn = init_schema("data/kabusys.duckdb")  # または既存 DB
  result = run_backtest(conn, start_date, end_date)
  print(result.metrics)
  conn.close()
  ```

---

## 設計上の注意点 / ヒント
- config モジュールはプロジェクトルート (.git または pyproject.toml を基準) を探索し、.env/.env.local を自動読み込みします。テスト等で自動ロードを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants クライアントはレート制限・リトライ・401 トークンリフレッシュ等を自動処理します。
- NewsCollector は SSRF 防止のためリダイレクト先のチェック、レスポンスサイズ制限、XML デシリアライズの安全化（defusedxml）を行っています。
- バックテストでは本番 DB を汚染しないために、必要な範囲のテーブルを in-memory DuckDB にコピーして実行します。

---

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py             — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント & 保存処理
    - news_collector.py    — RSS ニュース収集・保存
    - pipeline.py          — ETL パイプライン／差分更新
    - schema.py            — DuckDB スキーマ定義 / 初期化
    - stats.py             — 統計ユーティリティ（z-score 等）
  - research/
    - __init__.py
    - factor_research.py   — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — 将来リターン, IC, summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成（正規化・フィルタ）
    - signal_generator.py    — final_score 計算、BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py            — run_backtest（メインループ）
    - simulator.py         — PortfolioSimulator（擬似約定）
    - metrics.py           — バックテスト指標計算
    - run.py               — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py             — SimulatedClock（将来用）
  - execution/             — 発注周り（空の __init__ 等）
  - monitoring/            — 監視・メトリクス周り（空の __init__ 等）

---

## 開発・運用上の補足
- ログレベルは環境変数 `LOG_LEVEL` で設定（デフォルト INFO）。
- 環境は `KABUSYS_ENV`（development / paper_trading / live）で切替可能。コード内で is_live / is_paper / is_dev により条件分岐が可能。
- DuckDB のファイルパスや監視用 sqlite パスは設定から変更可能（環境変数 DUCKDB_PATH / SQLITE_PATH）。

---

必要であれば README に追加する項目（例）
- より詳しい ETL 手順・品質チェックの使い方
- ローカルでのデータダウンロード例（J-Quants の利用上の注意）
- CI / テストの実行方法
- API ドキュメント（各公開関数の詳細）

追加希望があれば、どのセクションを拡充するか教えてください。