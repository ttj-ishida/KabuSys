# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。データ取得（J-Quants）、ETL、特徴量作成、戦略シグナル生成、ニュース収集、監査ログ管理、マーケットカレンダー管理など、量的運用システムの主要コンポーネントを含みます。

---

## 主な特徴

- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェックフック）
- 特徴量エンジニアリング（クロスセクション Z スコア正規化、ユニバースフィルタ）
- シグナル生成（複数ファクターの重み付け統合、買い／売り判定、Bear フィルタ）
- ニュース収集（RSS パーシング、SSRF 対策、トラッキングパラメータ除去、銘柄抽出）
- マーケットカレンダー管理（JPX カレンダー、営業日判定・探索ユーティリティ）
- 監査ログ（シグナル〜約定のトレーサビリティ設計）
- 研究用ユーティリティ（将来リターン計算・IC、ファクター探索）

---

## 依存関係 / 動作環境

- Python 3.10 以上（PEP 604 の型記法などを使用）
- 必須パッケージ（例）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install duckdb defusedxml
# または開発時
pip install -e .
```

（プロジェクトに requirements.txt があればそれを使用してください）

---

## 環境変数 / 設定

kabusys は環境変数またはプロジェクトルートに配置した `.env` / `.env.local` から自動的に設定を読み込みます（CWD に依存しないルート検出）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 投稿先チャンネルID（必須）

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）デフォルト `INFO`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite パス（監視等、デフォルト `data/monitoring.db`）

注意: 必須変数が未設定の場合、`kabusys.config.settings` のプロパティアクセスで `ValueError` が発生します。

例: `.env`（参考）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（概略）

1. Python 3.10+ を用意し、依存パッケージをインストール
   - duckdb, defusedxml など

2. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
```bash
git clone <repo>
cd <repo>
pip install -e .
```

3. `.env` をプロジェクトルートに作成し、必要な環境変数を設定

4. DuckDB スキーマを初期化
   - Python REPL やスクリプト内で:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

---

## 使い方（主要 API の例）

基本は Python API を直接呼び出してジョブを実行します。

- DuckDB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
print(result.to_dict())
```

- 特徴量作成（features テーブルへ保存）
```python
from kabusys.strategy import build_features
from datetime import date
n = build_features(conn, target_date=date(2024, 1, 5))
print(f"built {n} features")
```

- シグナル生成（signals テーブルへ保存）
```python
from kabusys.strategy import generate_signals
from datetime import date
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 銘柄抽出に使う有効コードの集合（例: set of "7203", "6758", ...）
stats = run_news_collection(conn, known_codes=known_codes)
print(stats)  # {source_name: saved_count, ...}
```

- 研究向けユーティリティ（将来リターン・IC 等）
```python
from kabusys.research import calc_forward_returns, calc_ic
# 事前に prices_daily と factor_records を用意しておく
fwd = calc_forward_returns(conn, target_date=date.today(), horizons=[1,5,21])
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_5d")
```

---

## 推奨ワークフロー（運用例）

1. 毎朝（または夜間）:
   - run_daily_etl() を実行してデータを最新化
   - calendar_update_job() を併用してカレンダーを先読み

2. データ取得後:
   - build_features() で戦略用特徴量を作成

3. シグナル生成:
   - generate_signals() で BUY / SELL シグナルを作成 → signals テーブルに保存

4. 実行層（execution）:
   - signals をキュー化して発注・約定を記録（execution 層は別モジュールに実装）

5. ニュース収集は並列ジョブで定期実行:
   - run_news_collection() → raw_news / news_symbols を更新

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理（.env 自動ロード、settings オブジェクト）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - schema.py — DuckDB スキーマ定義・初期化（init_schema / get_connection）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - news_collector.py — RSS ニュース収集・保存
  - calendar_management.py — マーケットカレンダー管理ユーティリティ
  - features.py — データ向けユーティリティ再エクスポート（zscore_normalize）
  - stats.py — 統計ユーティリティ（z-score 正規化）
  - audit.py — 監査ログ（signal_events / order_requests / executions）スキーマ
  - pipeline (その他): quality モジュール参照（品質チェック） — 実装は別ファイル想定
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum / volatility / value）
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — features テーブル作成ロジック
  - signal_generator.py — final_score 計算と signals への書き込み
- execution/ — 発注・約定管理（パッケージ化済みだが実装は別ファイル）
- monitoring/ — 監視系（sqlite を想定）など

（上記はコードベースからの抜粋です。実際のツリーはリポジトリ参照）

---

## 開発（テスト・デバッグ）ヒント

- 自動環境変数読み込みを無効化する:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してテスト用の環境設定を自前で制御できます。
- DuckDB のインメモリモード:
  - テスト時は `init_schema(":memory:")` でメモリ DB を使用できます。
- jquants_client の HTTP 呼び出しは urllib を使っているため、ユニットテストでは該当関数（_request / _urlopen 等）をモックすると良いです。
- news_collector._urlopen をモックして HTTP を差し替え可能（テスト用フックが用意されています）。

---

## よくある操作コマンド（例）

- スキーマ初期化
```bash
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

- 簡易 ETL（当日分）
```bash
python -c "from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; c=init_schema('data/kabusys.duckdb'); print(run_daily_etl(c).to_dict())"
```

---

## ライセンス / 貢献

リポジトリに LICENSE があればそれに従ってください。バグ修正や新機能提案は Pull Request を送ってください。

---

必要であれば README に具体的な .env.example や SQL テーブル設計ドキュメント（DataSchema.md、StrategyModel.md 等）からの参照リンクや、運用スクリプト（systemd / cron / Airflow など）のサンプルも追加できます。どの情報を追記したいか教えてください。