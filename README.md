# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータストアとして用い、J-Quants API 等から市場データ・財務データ・ニュースを取得して ETL、品質チェック、特徴量抽出、監査ログ管理などを行うことを目的としています。

---

## 主要機能概要

- データ取得
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新、ページネーション対応）
  - RSS ベースのニュース収集（SSRF対策、トラッキングパラメータ除去、前処理）
- 永続化 / スキーマ管理
  - DuckDB 用の包括的なスキーマ定義（Raw / Processed / Feature / Execution / Audit 層）
  - 冪等な保存（ON CONFLICT / INSERT ... RETURNING を利用）
- ETL パイプライン
  - 日次差分 ETL（市場カレンダー、株価、財務データの差分取得と保存）
  - バックフィル、営業日調整、品質チェック統合
- データ品質管理
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返す）
- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB の prices_daily/raw_financials を参照）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- 監査（Audit）
  - signal → order_request → execution のトレーサビリティ用テーブル群と初期化機能
- カレンダー管理
  - market_calendar の管理・営業日判定・前後営業日検索のユーティリティ
- 実運用補助
  - 設定管理（環境変数 / .env 自動ロード）
  - Slack / kabuステーション周りの設定エントリ（実装は別モジュールで利用）

---

## 必須 / 推奨環境

- Python 3.9+（コードは型ヒントに | を使用しているため Python 3.10+ を想定している箇所がありますが、3.9 でも動作する設計です）
- DuckDB（Python パッケージ: duckdb）
- defusedxml（RSS の安全なパース用）
- ネットワークアクセス（J-Quants API、RSS）

例（pip）:
```bash
pip install duckdb defusedxml
```

プロジェクト単体で配布設定があれば開発インストール:
```bash
pip install -e .
```

---

## 環境変数（.env）設定

以下の環境変数が使用されます（必須のものには README 上で明示）:

必須
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client 用）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン（使用する場合）
- SLACK_CHANNEL_ID — Slack チャンネルID（使用する場合）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注モジュール使用時）

任意 / デフォルトあり
- KABU_API_BASE_URL — kabu API のベースURL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視用など。デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL。デフォルト: INFO）

自動ロードについて:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を自動読み込みします。
- OS 環境変数の方が優先され、`.env.local` は `.env` より優先して上書きされます。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

簡単な .env の例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your-password
DUCKDB_PATH=~/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ

1. Python 環境の準備（仮想環境推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

2. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # その他、利用する機能に応じて追加の依存をインストールしてください
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` を作成するか、必要な環境変数を export してください。
   - 自動ロードを使う場合、`.env` / `.env.local` にキーを配置します。

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # ファイルを作成して全テーブルを作る
   ```
   - メモリ DB が必要な場合は db_path に ":memory:" を指定できます。

5. （オプション）監査スキーマの初期化
   - init_schema で作成済みの接続に監査テーブルを追加する:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要ユースケースの例）

- 日次 ETL 実行（市場カレンダー取得 → 株価・財務取得 → 品質チェック）
```python
from datetime import date
import duckdb

from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# DB 初期化（既存ならスキップ）
conn = init_schema(settings.duckdb_path)

# ETL 実行（today を省略すると本日）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes に有効な銘柄コードセットを渡すと記事→銘柄紐付けを行う
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)
```

- J-Quants から株価を直接取得して保存
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved} rows")
```

- 研究用ファクター計算（DuckDB 接続と日付を渡す）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
target = date(2024, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target)
```

- ファクターの正規化や IC 計算
```python
from kabusys.data.stats import zscore_normalize
from kabusys.research import calc_ic, rank

# records は calc_momentum 等の結果リスト
z_normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
```

---

## 開発者向けノート / 実装上の注意点

- 設定管理
  - settings は環境変数から読む実装で、必須キー未設定時は ValueError を投げます。
  - 自動ロードはプロジェクトルート探索により .env / .env.local を読み込みます（CWD 依存しません）。
- J-Quants クライアント
  - レート制限（120 req/min）を固定間隔スロットリングで守ります。
  - 401 発生時はリフレッシュトークンで id_token を再取得して1回再試行します。
  - リトライは指数バックオフ（最大3回）を実装しています。
- News Collector
  - SSRF 回避（リダイレクト先検査 / プライベートIP 拒否 / スキーム制限）
  - レスポンスサイズ上限、gzip 解凍後のサイズチェックなど DoS対策を備えています。
- DuckDB 保存関数は基本的に冪等（ON CONFLICT）を意識して設計されています。
- 品質チェックは Fail-Fast ではなく、発見した問題を列挙して呼び出し側に判断させる方式です。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージのルートが `src/kabusys` の想定です（コードベースに基づく抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定読み込み・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py — RSS ニュース収集・解析・DB保存
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL の主要ロジック（run_daily_etl 等）
    - features.py — 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py — market_calendar の管理と営業日ユーティリティ
    - audit.py — 監査ログテーブル定義と初期化
    - etl.py — ETLResult の公開インターフェース
    - quality.py — データ品質チェック
  - research/
    - __init__.py — 研究用関数の再エクスポート
    - feature_exploration.py — 将来リターン / IC / summary
    - factor_research.py — momentum/volatility/value の計算
  - strategy/ — 戦略関連（パッケージ階層。実装は別途）
  - execution/ — 発注・ブローカー連携（パッケージ階層。実装は別途）
  - monitoring/ — 監視機能（パッケージ階層。実装は別途）

---

## よくある運用フロー（例）

- 毎晩（バッチ）
  - calendar_update_job で market_calendar を最新化
  - run_daily_etl を実行して株価・財務・カレンダーを差分更新
  - 品質チェック結果を Slack 等に通知（監視スクリプトから）
- 日次研究 / モデル更新
  - ETL 後に features テーブルを更新、研究用スクリプトでファクターを検証
- 発注フロー（本番）
  - strategy 層で signals を生成 → audit.order_requests に記録 → execution 層を通じてブローカー発注、executions に保存

---

## 補足・今後の拡張案

- kabuステーション実装（execution パッケージ）と Slack 通知の連携
- モデル学習パイプライン（特徴量履歴の保存、学習ジョブ）
- CI による品質チェック、ユニットテストの作成と自動化
- ドキュメントの充実（API リファレンス、運用手順）

---

この README はコードベースの現在の構造・実装方針をもとに作成しています。具体的な運用や追加機能はプロジェクト要件に応じて調整してください。必要であれば、サンプルの運用スクリプトや .env.example のテンプレートも作成します。どれが必要か教えてください。