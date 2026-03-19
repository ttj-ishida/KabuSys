# KabuSys

日本株向けの自動売買・データプラットフォーム基盤ライブラリです。  
J-Quants 等のマーケットデータから ETL を行い、特徴量（features）を構築、戦略シグナルを生成し、発注・監視レイヤへとつなぐことを目的としています。

概要、主な機能、セットアップ・使い方、主要モジュール構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下のレイヤで構成される日本株自動売買システムのライブラリ群です。

- Data Layer：J-Quants からのデータ取得、DuckDB によるスキーマ定義・保存、RSS ニュース収集、品質チェック、カレンダー管理、ETL パイプライン
- Research Layer：各種ファクター計算（モメンタム、ボラティリティ、バリュー等）と探索用ユーティリティ（IC、前方リターン、要約統計）
- Strategy Layer：特徴量正規化・合成（features 作成）、最終スコア計算と売買シグナル生成
- Execution / Monitoring Layer：発注・約定・ポジションの監査や監視（コードベース上にレイヤ名を定義。実装は実際のブローカー連携に応じて拡張）

設計のポイント：
- ルックアヘッドバイアス対策（計算時は target_date 時点のデータのみを使用）
- 冪等性（DB 保存は ON CONFLICT / upsert を利用）
- 外部依存を最小限に（DuckDB と標準ライブラリで多くを実装）
- ネットワークリクエストでのレート制御・リトライ・トークンリフレッシュ等の堅牢化

---

## 主な機能一覧

- J-Quants API クライアント（ページネーション対応、レート制御、トークンの自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB に冪等保存
- DuckDB スキーマ定義と初期化（init_schema）
  - raw / processed / feature / execution 層のテーブルを定義
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- ニュース収集（RSS → raw_news、SSRF 対策・XML デフューズ処理・テキスト前処理・銘柄抽出）
- 市場カレンダー管理（営業日判定、前後営業日探索、カレンダー更新ジョブ）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量構築（Z スコア正規化・ユニバースフィルタ・features テーブルへの書き込み）
- シグナル生成（各コンポーネントスコアを統合し BUY/SELL シグナルを生成）
- 統計ユーティリティ（zscore_normalize、IC、rank、factor_summary 等）
- 監査ログスキーマ（シグナル → 発注 → 約定 のトレーサビリティ）

---

## 動作環境・依存関係

- Python 3.10 以上（PEP 604 の union 型などを利用）
- 主な Python パッケージ（代表例）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）

パッケージ化・依存ファイルはリポジトリ側の管理に従ってください。開発環境では仮想環境を推奨します。

例：
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install duckdb defusedxml
# プロジェクトを editable インストールする場合（pyproject/ setup がある前提）
# python -m pip install -e .
```

---

## 環境変数（主な必須項目）

KabuSys は環境変数（.env / .env.local / OS 環境変数）から設定を読み込みます（自動ロード）。必須の環境変数は下記です。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層利用時）
- SLACK_BOT_TOKEN — Slack 通知を行う場合に使用
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視用途など）

自動環境読み込みを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからインポートすると .env 自動読み込みを抑止できます（テスト等で便利）。

.env のパースはシェル風の基本的な構文（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ）に対応します。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -U pip
   python -m pip install duckdb defusedxml
   ```
2. 必要な環境変数を設定
   - リポジトリルートに `.env` を作成（.env.example を参照）
   - または OS レベルでエクスポート
3. DuckDB スキーマを初期化
   - Python REPL やスクリプトで以下を実行:
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # ファイル作成とテーブル初期化
   # またはメモリ DB:
   # conn = init_schema(":memory:")
   ```
4. ETL 実行（例）
   ```python
   from datetime import date
   import kabusys
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   res = run_daily_etl(conn, target_date=date.today())
   print(res.to_dict())
   ```

---

## 使い方（代表的な API）

以下は代表的な処理の呼び出し例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 市場カレンダーの更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(res)
```

- 特徴量構築（feature layer への upsert）
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, target_date=date(2024, 1, 31))
print("built features:", n)
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
print("signals written:", count)
```

- ファクター計算・研究ユーティリティ
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

m = calc_momentum(conn, date(2024,1,31))
fwd = calc_forward_returns(conn, date(2024,1,31), horizons=[1,5,21])
ic = calc_ic(m, fwd, "mom_1m", "fwd_5d")
```

---

## 注意事項 / 運用上のポイント

- J-Quants API のレート制限を守るため、client 内にレートリミッタ（固定間隔スロットリング）とリトライロジックがあります。過剰な並列呼び出しは避けてください。
- 金融データの取得は API 側で後出し修正が入ることがあるため、ETL はバックフィル（直近数日を再取得）する設計です。
- features / signals 等は日付単位で DELETE → INSERT の形で置換（トランザクション）を行い冪等性を確保しています。
- ニュース収集は RSS を前提にしており、SSRF・XML Bomb 対策（defusedxml、リダイレクト検査、最大受信サイズチェック）を実装しています。
- 本ライブラリは発注（broker）連携部分を抽象化しており、実際のブローカー API に接続する実装は environment や運用要件に応じて追加してください（kabuステーション連携等）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの `src/kabusys/` 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理 （.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py      — RSS ニュース取得・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義・init_schema / get_connection
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - pipeline.py            — ETL パイプライン（差分更新・run_daily_etl 等）
    - calendar_management.py — market_calendar 管理・営業日判定・calendar_update_job
    - features.py            — data 層の特徴量ユーティリティ再エクスポート
    - audit.py               — 監査ログスキーマ（signal_events / order_requests / executions）
    - (その他: quality, execution などを想定)
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py — 前方リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — features を構築して DB に保存
    - signal_generator.py    — final_score 計算・BUY/SELL シグナル生成
  - execution/               — 発注関連（パッケージとして存在）
  - monitoring/              — 監視・アラート関連（パッケージとして存在）

---

## 開発・貢献

- 各モジュールは docstring に設計方針・処理フローを記載してあるため、まずはドキュメントを参照してください。
- テストを書く際は .env の自動ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してからインポートしてください。
- DB を使用するユニットテストは DuckDB の ":memory:" を活用すると簡便です（init_schema(":memory:")）。

---

この README はリポジトリ内の docstring / モジュール設計に基づいて要点をまとめています。より詳しい仕様（StrategyModel.md / DataPlatform.md / Research ドキュメント等）がリポジトリに含まれている場合はそれらも参照してください。必要であれば利用例や運用手順（cron や CI/CD での ETL スケジュール化、Slack 通知のセットアップ等）の追加ドキュメントを作成します。