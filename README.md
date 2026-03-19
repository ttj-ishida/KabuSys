# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）の README。  
このリポジトリは、データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどの機能群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。主な役割は以下の通りです。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制御・リトライ含む）
- DuckDB を用いた (Raw → Processed → Feature → Execution) のデータレイヤ
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量エンジニアリングと正規化（Z スコア）
- 戦略のシグナル生成（最終スコア計算、BUY / SELL 判定）
- ニュース収集（RSS）と記事 → 銘柄紐付け
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 発注／実行／監査ログ用スキーマ（監査トレーサビリティの整備）

設計上のポイント：
- ルックアヘッドバイアス回避のため「target_date 時点で利用可能なデータのみ」を使う
- DuckDB を中心とした冪等（idempotent）な保存処理
- 外部 API 呼び出しは data 層に集約、戦略層は発注 API に依存しない

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（認証・ページネーション・保存関数）
  - pipeline: 日次 ETL（差分取得、バックフィル、品質チェック）
  - schema: DuckDB スキーマ定義と初期化（init_schema）
  - news_collector: RSS 収集・正規化・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: Z スコア正規化ユーティリティ
- research
  - factor_research: momentum / value / volatility ファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy
  - feature_engineering.build_features: ファクターの正規化→features テーブルへ UPSERT
  - signal_generator.generate_signals: features / ai_scores / positions を元に BUY/SELL シグナル生成
- execution（パッケージ化済み、発注ロジックはここに実装）
- monitoring（監視・通知等の補助）

---

## 要件

- Python 3.10 以上（型注釈で `|` 演算子を使用しているため）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ：urllib, datetime, logging, pathlib, typing など

pip によるインストール例（必要に応じて仮想環境を作成してください）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
pip install -e .
```
（プロジェクトに setup/pyproject があれば `pip install -e .` を利用）

---

## 環境変数（設定）

自動で .env / .env.local をプロジェクトルートから読み込みます（無効化は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。

主な環境変数（config.Settings 参照）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env.example を用意し、上記を設定してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # 無ければ個別に duckdb, defusedxml 等をインストール
   pip install -e .
   ```

3. 環境変数 (.env) を作成
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、必須変数を設定します。
   例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=zzzzz
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで schema.init_schema を実行して DB を初期化します。

---

## 使い方（クイックスタート）

以下は Python スクリプト上での基本的な操作例です。

1) スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants からの株価・財務・カレンダー取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量構築（features テーブル作成）
```python
from kabusys.strategy import build_features
from datetime import date

cnt = build_features(conn, target_date=date.today())
print(f"features upserted: {cnt}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

n = generate_signals(conn, target_date=date.today())
print(f"signals written: {n}")
```

5) ニュース収集ジョブ実行（RSS → raw_news）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(res)
```

6) カレンダー更新（夜間ジョブ）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

7) J-Quants API を直接使ってデータ取得・保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = save_daily_quotes(conn, records)
```

注意点：
- 多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。
- ETL / 保存処理は冪等（ON CONFLICT）実装のため同じデータを複数回実行しても安全な設計です。
- シグナル生成や特徴量作成は target_date の時点で利用可能なデータのみを使用することを前提としています。

---

## ディレクトリ構成（主なファイル）

以下はソースツリー（src/kabusys 以下）の主要ファイル／モジュールです。実ファイルはさらに細分化されています。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存関数）
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（差分更新 / 日次実行）
    - news_collector.py             — RSS 収集・DB 保存・銘柄抽出
    - calendar_management.py        — カレンダー管理（営業日判定等）
    - features.py                   — features まわりの公開 API（zscore 再エクスポート）
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログ（トレーサビリティ用テーブル）
  - research/
    - __init__.py
    - factor_research.py            — momentum/volatility/value の計算
    - feature_exploration.py        — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py        — 生ファクターを正規化して features テーブルへ
    - signal_generator.py           — final_score 計算・BUY/SELL シグナル生成
  - execution/                       — 発注 / execution 層（初期化済み）
  - monitoring/                      — 監視用モジュール（補助）

---

## 開発・運用に関する補足

- ロギングは設定（LOG_LEVEL）に従って動きます。production（live）モードでは十分にログや通知の設定を行ってください。
- J-Quants API はレートリミット（120 req/min）に対応する実装になっています。大量のページネーションを行う処理はその制約を踏まえてください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行います。テスト時や CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- DuckDB ファイル（デフォルト data/kabusys.duckdb）はバックアップ・管理を推奨します。インメモリ DB（":memory:"）もサポートしていますが永続化されません。
- ニュース収集時の SSRF 防止、XML パース安全化（defusedxml）の採用、レスポンスサイズ制限などセキュリティ配慮がなされています。

---

## よくある質問（FAQ）

Q: どの Python バージョンが必要ですか？  
A: Python 3.10 以上を想定しています（型注釈に `|` を使用）。

Q: データベース初期化はどうやる？  
A: `from kabusys.data.schema import init_schema; conn = init_schema("data/kabusys.duckdb")` を実行してください。

Q: ETL の差分取得は自動でやってくれる？  
A: run_daily_etl / run_prices_etl 等は DB にある最終取得日を元に差分を算出し、バックフィルオプションもあります。

---

もし README に含めてほしい追加情報（CI 手順、テスト、デプロイ手順、.env.example のサンプル完全版、実運用での注意点など）があれば教えてください。必要に応じて追記します。