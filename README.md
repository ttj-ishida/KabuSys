# KabuSys

日本株向けの自動売買システム用ライブラリ（モジュール群）。データ取得・ETL、ファクター計算、特徴量生成、シグナル生成、バックテスト、ニュース収集、DuckDBスキーマなど、量的運用に必要な主要コンポーネントを含みます。

主な目的は「研究→本番」まで一貫して使えるモジュール提供であり、ルックアヘッドバイアス回避、冪等性、堅牢なエラー/ネットワーク処理などに配慮して実装されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要ユースケース）
- 環境変数（.env）
- ディレクトリ構成

---

プロジェクト概要
- DuckDB をデータレイヤに採用し、J-Quants API から株価・財務・カレンダーを取得して Raw → Processed → Feature → Execution の多層スキーマに格納します。
- 研究（research）向けのファクター計算、特徴量エンジニアリング、シグナル生成ロジック、バックテストエンジン（シミュレータ・メトリクス）を提供します。
- ニュース収集（RSS）と銘柄紐付け機能、J-Quants クライアント（リトライ・レート制御・トークンリフレッシュ対応）などデータ取得基盤も含まれます。
- 発注／実行系（execution）やモニタリング（monitoring）用の拡張ポイントを用意しています（実装はモジュールに依存）。

機能一覧
- データ取得
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - ニュース(RSS)収集器（fetch_rss / save_raw_news / extract_stock_codes）
- データ保存・スキーマ
  - DuckDB スキーマ定義と初期化（init_schema）, DB 接続取得
  - Raw / Processed / Feature / Execution 用テーブル定義（冪等性を考慮）
- ETL パイプライン
  - 差分更新ロジック・バックフィル（pipeline モジュール）
  - 品質チェックフック（quality モジュール想定）
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / summary）
  - Zスコア正規化ユーティリティ
- 戦略（strategy）
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals）: 各コンポーネントスコア・AI スコア統合・Bear フィルタ・BUY/SELL 生成
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）
  - 日次ループを含む run_backtest（DB をコピーしてインメモリで実行）
  - バックテストメトリクス計算（CAGR, Sharpe, MaxDD, WinRate, Payoff, Trades）
  - CLI エントリポイント: python -m kabusys.backtest.run
- 設定管理
  - 環境変数/.env 自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - Settings クラス経由で必須設定取得

---

セットアップ手順（開発環境想定）
前提: Python >= 3.10（typing の "X | None" を使用しているため）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化
   - macOS / Linux
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   - 最小依存例:
     ```
     pip install duckdb defusedxml
     ```
   - 他にログ設定やテスト用ライブラリ等を追加してください。パッケージ化されていれば `pip install -e .` などで開発インストールできます。

4. DuckDB スキーマの初期化
   - Python REPL で:
     ```py
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ディレクトリを自動作成
     conn.close()
     ```

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動読み込みされます（LOAD 順: OS env > .env.local > .env）。
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須変数等は下記「環境変数」セクション参照。

---

使い方（主要ユースケース）

1) DuckDB スキーマ初期化
```py
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 作成後は conn 経由でクエリ実行可能
conn.close()
```

2) J-Quants からデータ取得（例: 日次株価を取得して保存）
```py
from datetime import date
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
token = jq.get_id_token()  # settings.jquants_refresh_token が必要
recs = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, recs)
print("saved:", saved)
conn.close()
```

3) ニュース収集（RSS）と銘柄紐付け
```py
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 事前に有効な銘柄コードセットを用意しておくと抽出して紐付ける
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)
conn.close()
```

4) 特徴量構築 / シグナル生成
```py
from datetime import date
from kabusys.strategy import build_features, generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024,1,31))
signals = generate_signals(conn, target_date=date(2024,1,31))
conn.close()
```

5) バックテスト（CLI）
- 事前に DB (prices_daily, features, ai_scores, market_regime, market_calendar など) を用意しておく必要があります。
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db data/kabusys.duckdb \
  --cash 10000000
```
- Python API からは run_backtest を直接呼べます:
```py
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(res.metrics)
conn.close()
```

6) 設定値の取得
```py
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```
- Settings は環境変数を参照し、未設定の必須値は ValueError を投げます。

---

環境変数（.env）
自動読み込み対象: プロジェクトルートの .env / .env.local（OS 環境変数が優先）。必要に応じて .env.example を参照して作成してください。

主な変数
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード（execution 層利用時）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（monitoring 用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — デフォルト DB パス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — set=1 で自動 .env ロードを無効化

注意:
- Settings クラスのプロパティは必要に応じて ValueError を吐きます。初期化前に必須 env を設定してください。

---

ディレクトリ構成（抜粋）
（実際は src/kabusys 配下にモジュールが配置されている想定）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - backtest/
      - __init__.py
      - engine.py
      - simulator.py
      - metrics.py
      - run.py
      - clock.py
    - execution/         # 発注・実行層用（__init__ 等）
    - monitoring/       # 監視・通知機能（将来的拡張）

各モジュールの概要
- data/schema.py: DuckDB の全テーブル定義と init_schema(), get_connection()
- data/jquants_client.py: API 呼び出し・保存ユーティリティ（リトライ・レート制御）
- data/news_collector.py: RSS 取得 → raw_news 保存 → 銘柄抽出・紐付け
- research/*: ファクター計算・探索ツール（バックテスト前の研究用）
- strategy/*: features の構築とシグナル生成ロジック（冪等、日次置換）
- backtest/*: インメモリでのバックテスト実行、シミュレータとメトリクス
- config.py: 環境変数の読み込み・Settings クラス（.env 自動ロード機能）

---

設計上の注意点 / 運用メモ
- ルックアヘッドバイアス回避: 各ファクションは target_date 時点までの情報のみを使う設計になっています。
- 冪等性: DB への保存は基本的に ON CONFLICT DO UPDATE / DO NOTHING を使用して重複を排除しています。
- ネットワーク耐性: J-Quants クライアントはレート制限を守り、リトライ/トークンリフレッシュを行います。
- テスト向け: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動 .env ロードを無効化できます。
- Python バージョン: 3.10 以上を推奨します（typing の | 演算子等を使用）。

---

開発・拡張
- execution 層や monitoring の実装はプロジェクト固有のブローカー API（kabuステーション等）や監視要件に応じて追加してください。
- ETL のスケジューリングやログ収集、監査ログ（ETLResult.to_dict の出力など）を組み合わせると運用性が向上します。

---

以上。必要であれば README に含めるサンプル .env.example、requirements.txt、または各モジュールの API 参照例（より詳細なコードスニペット）を追加します。どの情報を優先して追記しますか?