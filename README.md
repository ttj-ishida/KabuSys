# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB を用いたデータレイク、J-Quants API 経由のデータ取得、ニュース収集、特徴量計算、ETL パイプライン、品質チェック、監査ログ等を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するための内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API から株価・財務・市場カレンダー等を取得し DuckDB に保存する
- RSS を用いたニュース収集と記事の前処理・銘柄抽出
- DuckDB 上でのスキーマ定義および初期化
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ファクター（Momentum / Value / Volatility 等）や特徴量探索、IC 計算などの研究ユーティリティ
- 発注・監査用スキーマ（監査ログ・注文トレーサビリティ）

設計上の要点：
- DuckDB を中心としたローカルデータベース設計（冪等な INSERT）
- API 呼び出しに対するレートリミット・リトライ・トークン自動リフレッシュ対応
- RSS 収集に対する SSRF / XML Bomb 等の安全対策
- 研究・特徴量計算は外部ライブラリに依存しない純粋な実装（標準ライブラリのみ）

---

## 主な機能一覧

- data:
  - jquants_client: J-Quants API クライアント（ページネーション、レートリミット、リトライ、id token 自動更新）
  - news_collector: RSS 取得・前処理・DuckDB への冪等保存、銘柄抽出
  - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline / etl: 差分 ETL、日次 ETL エントリポイント、品質チェック統合
  - quality: 欠損・スパイク・重複・日付不整合のチェック
  - calendar_management: JPX カレンダーの管理（営業日判定、next/prev_trading_day 等）
  - audit: 発注〜約定の監査ログスキーマ初期化ユーティリティ
  - stats: Z スコア正規化など統計ユーティリティ
- research:
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）、ファクター統計サマリ
  - factor_research: Momentum / Volatility / Value 等のファクター計算
- strategy / execution / monitoring:
  - パッケージ用意（将来的な戦略実装・発注実装・監視ロジック向け）

---

## 前提条件

- Python 3.10 以上（typing の `|` などを使用）
- 必要パッケージ（一例）:
  - duckdb
  - defusedxml

インストール例（プロジェクトルートで仮想環境を作成してから）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発時: pip install -e .
```

（パッケージ化されている場合は requirements.txt / pyproject.toml に従ってください）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動ロード機能あり）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN -- J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      -- kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN        -- Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       -- Slack チャンネル ID（必須）

オプション:
- KABUSYS_ENV            -- 実行環境 ("development" / "paper_trading" / "live")、デフォルト "development"
- LOG_LEVEL              -- ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")、デフォルト "INFO"
- DUCKDB_PATH            -- DuckDB ファイルパス、デフォルト `data/kabusys.duckdb`
- SQLITE_PATH            -- SQLite（モニタリング用）パス、デフォルト `data/monitoring.db`
- KABUSYS_DISABLE_AUTO_ENV_LOAD -- 自動 .env 読込を無効化するフラグ（値がセットされていれば無効）

.env ロード順序（優先度低→高）:
1. .env
2. .env.local（.env を上書き、ただし OS の環境変数は保護）
3. OS 環境変数が最優先（上書きされない）

注意: Settings クラス経由で設定値にアクセスできます。
例: from kabusys.config import settings; settings.jquants_refresh_token

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を用意
2. 依存パッケージをインストール（duckdb, defusedxml など）
3. プロジェクトルートに `.env`（または `.env.local`）を作成し必須変数を設定
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=yyyyy
     SLACK_BOT_TOKEN=xxxxx
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```
4. DB スキーマの初期化
   - Python REPL またはスクリプト内で:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
     ```
   - 監査ログ用 DB を別途初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要ワークフロー例）

1. 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# DB 初期化（初回のみ）
conn = init_schema(settings.duckdb_path)

# 日次 ETL 実行（target_date を省略すると今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

2. ニュース収集ジョブ（RSS）を実行して保存する

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes を渡すと記事中の銘柄コード抽出と紐付けを行う
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 保存件数}
```

3. J-Quants から株価を直接取得する（ページネーション対応）

```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
from datetime import date

# トークンは自動的に settings.jquants_refresh_token から取得される
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# DuckDB に保存
from kabusys.data.schema import init_schema
conn = init_schema(settings.duckdb_path)
jq.save_daily_quotes(conn, records)
```

4. 研究用：ファクター計算・IC 計算

```python
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
target_date = date(2024, 1, 31)

mom = calc_momentum(conn, target_date)
vol = calc_volatility(conn, target_date)
val = calc_value(conn, target_date)

fwd = calc_forward_returns(conn, target_date, horizons=[1,5,21])

# 例: mom の mom_1m と fwd_1d の IC を計算
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

---

## 注意点 / 実装上の特記事項

- jquants_client:
  - API レート制限（120 req/min）を内部で守る RateLimiter を使用
  - 指定の HTTP ステータスに対して指数バックオフでリトライ
  - 401 を受けた場合はリフレッシュトークンで自動的に id_token を再取得して 1 回リトライ
  - 保存処理は冪等（ON CONFLICT）になっているため再実行に安全

- news_collector:
  - RSS を取得する際に SSRF / private host / gzip bomb / XML 攻撃対策を実装
  - 記事IDは正規化した URL の SHA-256 ハッシュの先頭 32 文字で一意化し冪等性を保証
  - 銘柄抽出は 4 桁数字（例: "7203"）を known_codes でフィルタ

- schema:
  - Raw / Processed / Feature / Execution / Audit 各層のテーブルを定義
  - init_schema は冪等でテーブルとインデックスを作成
  - audit に関する DDL は init_audit_schema / init_audit_db を通じて初期化可能

- quality:
  - 欠損、重複、スパイク（前日比閾値）、日付不整合をチェックし QualityIssue のリストを返す
  - run_all_checks でまとめて実行可能（ETL の結果に組み込み推奨）

---

## ディレクトリ構成

（抜粋：src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラスを提供
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント、保存ユーティリティ
    - news_collector.py      -- RSS 取得・前処理・DuckDB 保存ロジック
    - schema.py              -- DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETL レスポンス型の再エクスポート
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize 等）
    - features.py            -- 特徴量用公開インターフェース
    - calendar_management.py -- 市場カレンダー管理（営業日判定、更新ジョブ）
    - audit.py               -- 監査ログ（order_requests / executions 等）初期化
  - research/
    - __init__.py
    - feature_exploration.py -- 将来リターン、IC、ファクター統計サマリ
    - factor_research.py     -- Momentum / Volatility / Value の計算
  - strategy/
    - __init__.py            -- （戦略実装用パッケージ）
  - execution/
    - __init__.py            -- （発注実装用パッケージ）
  - monitoring/
    - __init__.py            -- （監視・メトリクス用パッケージ）
- src/...
  - （パッケージ化構成、pyproject.toml など）

---

## よくある質問（FAQ）

Q: .env の自動読み込みを止めたい  
A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

Q: DuckDB を別場所に置きたい  
A: 環境変数 `DUCKDB_PATH` を設定するか、schema.init_schema にパスを指定して DB を初期化してください。

Q: J-Quants のトークンをどのように渡す？  
A: `JQUANTS_REFRESH_TOKEN` を環境変数に設定します。jquants_client は settings.jquants_refresh_token を使用します。

Q: 研究コードは pandas 等に依存しますか？  
A: 研究モジュール（calc_* や zscore_normalize 等）は標準ライブラリのみで実装されており、外部依存を避ける設計です。DuckDB の接続は必要です。

---

## 今後の拡張案（参考）

- strategy / execution パッケージに戦略定義・ポートフォリオ最適化・ブローカラッパー実装
- Slack 通知やモニタリングダッシュボード統合（settings の Slack 設定を利用）
- ユニットテスト、CI の追加と Docker イメージ化

---

README では主要な使い方と注意点をまとめました。実際の運用では API キーやシークレット管理に細心の注意を払い、ペーパートレーディング環境で十分に検証してから live 環境に移行してください。質問や追加したいドキュメント項目があれば教えてください。