# KabuSys

日本株向けの自動売買・リサーチ基盤ライブラリです。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、擬似約定シミュレータなどのモジュールを含みます。

---

## 目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（.env）例
- 基本的な使い方
  - DB 初期化
  - ETL（データ取得・保存）
  - 特徴量・シグナル生成
  - バックテストの実行（CLI / API）
  - ニュース収集
- 設計上の注意点
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株アルゴリズムトレードの研究〜運用までをカバーする Python パッケージです。  
主な目的は次の通りです。
- J-Quants API からのデータ取得と DuckDB への保管（冪等保存）
- ファクター（モメンタム・ボラティリティ・バリュー等）の計算と正規化
- features と ai_scores を組み合わせた売買シグナル生成
- ポートフォリオの擬似約定（スリッページ・手数料考慮）によるバックテスト
- RSS を用いたニュース収集とテキスト前処理 / 銘柄抽出

---

## 機能一覧
- data/jquants_client: J-Quants から日足・財務・市場カレンダーを取得（ページネーション、レートリミット、リトライ、トークン自動リフレッシュ組込）
- data/schema: DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
- data/pipeline: 差分取得（バックフィル）、ETL 結果の集約（品質チェック連携想定）
- data/news_collector: RSS 収集、前処理、raw_news/ news_symbols への冪等保存、SSRF対策・サイズ制限等
- research/factor_research: momentum/volatility/value 等のファクター算出
- research/feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/feature_engineering: 生ファクターを統合して features テーブルへ保存（Z スコア正規化、ユニバースフィルタ）
- strategy/signal_generator: features + ai_scores から final_score を算出し BUY/SELL シグナルを作成
- backtest: ポートフォリオシミュレータ、メトリクス計算、バックテストエンジン、CLI 実行モジュール
- execution / monitoring: 発注・監視層（実装はこのコードベースの骨組みを想定）

---

## 必要条件
- Python 3.10+
- 主要依存（本コードベースで参照されているもの）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants / RSS フィード）
- J-Quants のリフレッシュトークン等の環境変数

（実プロジェクトでは requirements.txt / pyproject.toml を用意して依存を固定してください）

---

## セットアップ手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール
   - pip install duckdb defusedxml
   - （パッケージ化されていれば）pip install -e .

3. DuckDB データベースの初期化
   - Python REPL またはスクリプトで schema.init_schema を呼ぶ（例は後述）

4. 環境変数の設定（.env をプロジェクトルートに置くと自動でロードされます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

---

## 環境変数（.env）例
以下の環境変数の設定が必要です（usage に応じて全ては必須ではありませんが、該当機能を使う際に必須となります）。

必須（使用機能により変わります）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id

オプション:
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL  （デフォルト: INFO）
- DUCKDB_PATH=data/kabusys.duckdb  （デフォルト値）
- SQLITE_PATH=data/monitoring.db

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=passwd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- パーサは export KEY=val 形式やクォート、コメント等に対応しています。
- プロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env / .env.local を読み込みます。

---

## 基本的な使い方

### DB 初期化
DuckDB ファイルを初期化してスキーマを作成します。

Python で:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
# 使用後は conn.close()
```

### ETL（データ取得・保存）
jquants_client を使ってデータを取得して保存できます。pipeline 内の便利関数も利用します。

簡単な例（株価取得 → 保存）:
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=..., date_to=..., id_token=None)
saved = jq.save_daily_quotes(conn, records)
```

pipeline モジュールは差分取得や品質チェックを含む ETL ワークフローを提供します（run_prices_etl 等の関数を参照）。

### 特徴量生成 / シグナル生成（API）
DuckDB 接続と日付を渡して実行します。

例: features を作る
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"upserted features: {n}")
```

例: シグナル生成
```python
from kabusys.strategy import generate_signals
n = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals written: {n}")
```

### バックテスト（CLI）
バックテスト用の CLI エントリポイントが提供されています。

コマンド例:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db data/kabusys.duckdb \
  --cash 10000000
```

主要オプション:
- --start / --end : バックテスト期間（YYYY-MM-DD）
- --db : DuckDB ファイルパス（必須）
- --cash, --slippage, --commission, --max-position-pct

内部では run_backtest 関数が利用され、generate_signals を日次で呼び出して擬似約定を行います。

バックテスト API を直接呼ぶ例:
```python
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(res.metrics)
```

### ニュース収集（RSS）
news_collector は RSS から記事を収集し raw_news / news_symbols へ保存します。

例:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: new_saved_count, ...}
```

---

## 設計上の注意点
- ルックアヘッドバイアス防止: 各処理は target_date 時点のデータのみを使用する設計を心がけています。取得時刻（fetched_at）を UTC で保存します。
- 冪等性: DB への保存は ON CONFLICT / DO UPDATE / DO NOTHING により冪等になるよう実装されています。
- レート制限とリトライ: J-Quants クライアントは固定間隔のスロットリングと指数バックオフ・リトライ（特定ステータスに対して）を備えています。401 発生時はリフレッシュを行って再試行します。
- セキュリティ（ニュース収集）: RSS 収集では SSRF 防止、受信サイズ制限、defusedxml による XML 攻撃対策を行っています。

---

## ディレクトリ構成（抜粋）
プロジェクトの主要ファイル／モジュールは以下の通りです（src/kabusys 配下）:

- __init__.py
- config.py                      — 環境変数/設定管理
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（取得・保存）
  - news_collector.py             — RSS 収集・前処理・DB 保存
  - schema.py                     — DuckDB スキーマ定義 & init_schema()
  - pipeline.py                   — ETL パイプライン
  - stats.py                      — zscore_normalize 等ユーティリティ
- research/
  - __init__.py
  - factor_research.py            — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py        — 将来リターン・IC・統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py        — features 作成（正規化・フィルタ）
  - signal_generator.py           — final_score 計算・signals 書き込み
- backtest/
  - __init__.py
  - engine.py                     — run_backtest 等
  - simulator.py                  — PortfolioSimulator / 擬似約定
  - metrics.py                    — バックテスト評価指標
  - run.py                        — CLI エントリポイント
  - clock.py                      — SimulatedClock（将来用）
- execution/                       — 発注層（パッケージ構成）
- monitoring/                      — 監視・メトリクス収集（パッケージ構成）

各モジュールは docstring とロギングを備え、テストしやすい関数分割がされています。

---

## 最後に
この README はコードベースの主要機能と操作手順の概要を示しています。実運用では以下に注意してください:
- secrets（トークン・パスワード）は安全に管理する（.env を適切に .gitignore）
- DuckDB ファイルとバックアップ方針を決める
- テスト環境（paper_trading / development）と本番（live）で設定を分ける

追加でサンプルスクリプトや CI/デプロイ手順が必要であれば教えてください。README を拡張して具体的なワークフロー（ETL の cron ジョブ構成、Slack 通知、監視項目等）を追記できます。