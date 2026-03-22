# KabuSys

KabuSys は日本株を対象とした自動売買／データプラットフォームのライブラリです。  
DuckDB をデータストアに用い、J-Quants API や RSS を通じたデータ収集、特徴量生成、シグナル生成、バックテスト用シミュレータを含む一連の処理を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「単体での DB 操作・テスト可能性」であり、研究（research）→ データ（data）→ 戦略（strategy）→ 実行（execution）→ バックテスト（backtest）の各層を分離して実装しています。

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS ベースのニュース収集（トラッキングパラメータ除去、SSRF 対策）
  - DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - ETL パイプラインの補助（差分取得、バックフィルなど）
- ファクター・特徴量処理（research / strategy）
  - モメンタム、ボラティリティ、バリューなどのファクター計算
  - Z スコア正規化ユーティリティ
  - 特徴量のマージ・ユニバースフィルタ・クリップ処理（features テーブルへの保存）
- シグナル生成
  - 正規化済み特徴＋AIスコアを統合して final_score を計算
  - Bear レジーム判定・BUY/SELL シグナル生成、signals テーブルへの書き込み（冪等）
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル対応）
  - 日次ループによるシグナルトリガー・約定処理・評価
  - メトリクス計算（CAGR、Sharpe、Max Drawdown、勝率など）
  - CLI からのバックテスト実行（python -m kabusys.backtest.run）
- ユーティリティ
  - 環境変数/設定読み込み（.env 自動読込機構）
  - ロギング / 設定検証

---

## 必要条件

- Python 3.10 以上（明示的に | 型注釈（X | Y）を使用しているため）
- 主要依存ライブラリ（最低限）:
  - duckdb
  - defusedxml

必要に応じて他のパッケージ（例: テスト用のモック等）を追加してください。

---

## セットアップ手順

1. リポジトリを取得（例: git clone）し、プロジェクトルートに移動します。
2. 仮想環境を作成・有効化：
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
3. 必要パッケージをインストール：
   ```
   pip install duckdb defusedxml
   ```
   （requirements.txt があれば `pip install -r requirements.txt` を使用）

4. パッケージを開発インストール（任意）：
   ```
   pip install -e .
   ```
   （プロジェクトが pip インストール可能な形になっている場合）

5. DuckDB スキーマを初期化してデータベースを準備（例）：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   デフォルトのパスは設定（環境変数）に依存します。

---

## 環境変数（主なもの）

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。`.env.example` を参考に環境を用意してください。主なキーは次のとおりです：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視系）データベースパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）

必要な環境変数を設定した .env ファイルをプロジェクトルートに置いてください。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()
  ```

- J-Quants から日足を取得して保存（プログラム例）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  token = get_id_token()  # settings からリフレッシュトークンを参照して取得
  records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  saved = save_daily_quotes(conn, records)
  conn.close()
  ```

- ニュース収集（RSS）と保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  conn.close()
  ```

- 特徴量ビルド（features テーブルへの保存）
  ```python
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  n = generate_signals(conn, target_date=date(2024, 1, 31))
  conn.close()
  ```

- バックテスト（CLI）
  リポジトリルートで次を実行します：
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```
  オプションで `--slippage` / `--commission` / `--max-position-pct` を指定できます。

- バックテストを Python API から呼ぶ例
  ```python
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(result.metrics)
  conn.close()
  ```

---

## 開発者向けメモ

- ロギング: 各モジュールは logging.getLogger(__name__) を用いており、環境変数 LOG_LEVEL で制御します。
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から `.env` / `.env.local` を自動ロードします。
  - 自動読込を無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- テスト時は設定を差し替えるため `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使うか、環境変数を明示的に設定してください。
- ネットワーク呼び出し（J-Quants / RSS）にはリトライ・レート制限・SSRF 対策が組み込まれています。テスト時はネットワークをモックしてください。

---

## ディレクトリ構成

概要（主要ファイルのみ）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - news_collector.py               — RSS 収集・前処理・保存
    - schema.py                       — DuckDB スキーマ定義・初期化
    - stats.py                        — 統計ユーティリティ（Zスコア等）
    - pipeline.py                     — ETL パイプライン補助（差分取得等）
  - research/
    - __init__.py
    - factor_research.py              — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py          — forward return / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py          — features テーブル構築
    - signal_generator.py             — final_score 計算と signals 書き込み
  - backtest/
    - __init__.py
    - engine.py                       — バックテストの全体ループ
    - simulator.py                    — ポートフォリオシミュレータ（約定・評価）
    - metrics.py                      — バックテスト評価指標
    - run.py                          — CLI エントリポイント
    - clock.py                        — 将来拡張用の模擬時計
  - execution/                        — （将来的な発注・執行モジュール）
  - monitoring/                       — （監視・アラート用モジュール）
- pyproject.toml / setup.cfg / .gitignore など（プロジェクトルート）

各ファイルの docstring に設計意図や処理フローの説明が記載されています。実装を追う際はそれらを参照してください。

---

## 参考・設計ドキュメント（コード中参照）

コードは README に記載されている外部設計書（例: StrategyModel.md、DataPlatform.md、BacktestFramework.md、Engine.md 等）に従って実装されています。これらの仕様書がプロジェクト内に存在する場合はそちらも参照してください。

---

この README はコードベースから抽出した主要情報に基づいています。追加で欲しい内容（例: API リファレンス、より具体的な ETL 実行手順、CI 設定、例データの準備方法など）があれば教えてください。