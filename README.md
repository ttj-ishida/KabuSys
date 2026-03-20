# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB をデータ層に、J-Quants API など外部データソースを取り込み、研究（factor）→特徴量生成→シグナル生成→発注監査までを想定したモジュール群を提供します。

---

## 主要な特徴（概要）
- DuckDB ベースのスキーマ定義と初期化（冪等）
- J-Quants API クライアント（レート制御・自動リトライ・トークンリフレッシュ）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェックフック）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Zスコア正規化・ユニバースフィルタ）
- シグナル生成ロジック（重み付け合成、Bear レジーム処理、エグジット判定）
- ニュース収集（RSS 取得・前処理・記事→銘柄紐付け）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（信号→発注→約定のトレーサビリティ用テーブル群）

---

## 機能一覧（モジュール別短評）
- kabusys.config
  - 環境変数読み込み・管理（.env / .env.local をプロジェクトルートから自動ロード）
  - 必須設定の取得ヘルパー（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API ラッパ（fetch/save/トークン管理/リトライ/レート制御）
  - schema: DuckDB スキーマ定義・init_schema / get_connection
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 収集・前処理・DB保存・銘柄抽出
  - calendar_management: market_calendar を利用した営業日判定等
  - stats / features: Zスコア正規化など
  - audit: 発注・約定の監査用テーブル定義（監査ログ初期化）
- kabusys.research
  - factor_research: momentum / volatility / value の計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、要約統計
- kabusys.strategy
  - feature_engineering.build_features: research の生ファクターから features テーブル作成
  - signal_generator.generate_signals: features + ai_scores を統合して BUY/SELL 信号生成
- kabusys.execution
  - 発注／証券会社連携層のためのプレースホルダ（将来的に実装）

---

## 必要条件 / 推奨環境
- Python 3.10+（型表記に | Union を使用しているため）
- 主要な依存パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib, datetime, logging 等を使用

インストール例（仮）:
```bash
python -m pip install "duckdb" "defusedxml"
# 開発パッケージがある場合は requirements.txt / pyproject.toml を参照して pip install -e .
```

---

## 環境変数
settings クラスで参照する主な環境変数（必須に注意）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するには 1 を設定

自動 .env ロード:
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）を特定し、
  OS 環境 > .env.local > .env の順で読み込みます。
- テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（簡易）
1. リポジトリをクローン / ソースを取得
2. Python 仮想環境を作成して有効化
   - python -m venv .venv && source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt があればそれに従う）
4. .env を作成（.env.example を参考に必須変数を設定）
5. DuckDB スキーマ初期化（例: スクリプトまたは対話で下記を実行）

---

## 簡単な使い方（コード例）
以下は代表的な操作例です。実行前に環境変数と DuckDB パスを設定してください。

- データベース初期化:
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ作成してテーブル群を作る
```

- 日次 ETL 実行（J-Quants からの差分取得・保存）:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定しないと今日が対象
print(result.to_dict())
```

- 特徴量（features）構築:
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 3, 1))
print(f"features upserted: {count}")
```

- シグナル生成:
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
num = generate_signals(conn, target_date=date(2025, 3, 1))
print(f"signals written: {num}")
```

- RSS ニュース収集と保存（銘柄紐付け付き）:
```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes は既知の銘柄コードセット（例: {'7203','6758',...}）
res = run_news_collection(conn, known_codes={'7203', '6758'})
print(res)  # {source_name: saved_count}
```

- カレンダー更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 推奨ワークフロー（日次運用）
1. market_calendar を更新（calendar_update_job）
2. run_daily_etl で市場データ・財務データを差分取得・保存
3. build_features で features テーブルを更新
4. （AIスコア等があれば保存）
5. generate_signals でシグナルを作成
6. execution 層（将来的に）で発注・orders/trades を記録し audit を残す

---

## ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - schema.py — DuckDB スキーマ定義 / init_schema
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - news_collector.py — RSS 取得・保存・銘柄抽出
  - calendar_management.py — 営業日ロジック / calendar_update_job
  - audit.py — 監査ログ用テーブル DDL
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - features.py — features 再エクスポート
- research/
  - __init__.py
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — forward returns / IC / summary
- strategy/
  - __init__.py
  - feature_engineering.py — build_features
  - signal_generator.py — generate_signals
- execution/ (空のパッケージ: 発注層の実装場所)
- monitoring/ (監視・Slack 連携等を想定するモジュール群)

（リポジトリルートに .env.example / pyproject.toml / README.md 等を想定）

---

## テスト・デバッグ時の注意
- 自動 .env ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- DuckDB をインメモリで実行したい場合:
  - init_schema(":memory:")
- ログレベルは環境変数 LOG_LEVEL で調整

---

## 付記 / 設計に関するポイント
- 各 ETL / 書き込み操作は冪等性を考慮（ON CONFLICT / upsert を多用）
- Look-ahead バイアス対策：target_date 時点のみのデータ使用、fetched_at の記録
- API 呼び出しはレート制御・自動リトライ・トークンリフレッシュを実装
- ニュース収集では SSRF・XML Bomb・大量レスポンス対策を実施

---

この README はコードベース（src/kabusys/*）から主要点を抜粋して作成しています。詳細な使用方法・設定例・DB スキーマの仕様（DataSchema.md 等）はプロジェクトのドキュメントや設計資料を参照してください。必要であれば README に含める実行スクリプト例や .env.example のテンプレートを作成します。どの情報を追記しますか？