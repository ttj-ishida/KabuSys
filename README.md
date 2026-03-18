# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ README

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要 API の利用例）
- 環境変数（.env）について
- ディレクトリ構成（主要ファイル説明）
- 開発・テスト時の注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買システムとデータパイプラインを組み合わせたライブラリ群です。  
DuckDB をデータレイク/分析 DB として利用し、J-Quants API から市場データ／財務データ／マーケットカレンダーを取得して保存、特徴量計算・品質チェック・ニュース収集・監査ログなどを提供します。  
設計上、本番発注 API へ直接アクセスする処理は分離され、ETL／リサーチ／監査／ニュース収集の各機能は本番口座に直接影響しないように作られています。

主な設計方針（抜粋）
- DuckDB ベースの冪等（idempotent）な保存処理（ON CONFLICT）
- J-Quants API 呼び出しのレート制御・リトライ・トークン自動リフレッシュ
- RSS ニュース収集における SSRF 対策・サイズ制限・トラッキング除去
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order → execution のトレース）機能

---

## 主な機能（機能一覧）

- data
  - jquants_client: J-Quants API クライアント（ページネーション・トークン刷新・保存ユーティリティ）
  - pipeline: 日次 ETL（market calendar / prices / financials）の差分取得・保存
  - schema: DuckDB スキーマ作成・初期化
  - news_collector: RSS からニュース収集・前処理・DB 保存・銘柄抽出
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - etl / audit / features / stats: 補助ユーティリティ
- research
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計
- strategy / execution / monitoring
  - 基盤用のパッケージプレースホルダ（戦略・発注・監視ロジックを配置する想定）

---

## セットアップ手順

前提
- Python 3.9+（typing 機能等を利用）
- システムに DuckDB をインストール可能であること（pip 経由で duckdb パッケージを使います）

1. リポジトリをクローン／取得
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 代表的な依存（プロジェクト全体で使われている主なライブラリ）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （パッケージ管理ファイルが無い場合、プロジェクトに合わせて requirements.txt / pyproject.toml を作成してください）
4. 環境変数 / .env 準備
   - 後述の必須環境変数を .env に定義してください（.env.example を参考に）。
   - 自動 .env ロード機能が有効（プロジェクトルートの .env/.env.local を自動で読み込む）。テスト時に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで schema.init_schema を呼んで DB を作成します（親ディレクトリは自動生成されます）。
   - 例:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")

6. 監査ログ用スキーマ（必要なら）
   - from kabusys.data import audit
   - conn = duckdb.connect("data/kabusys.duckdb")
   - audit.init_audit_schema(conn, transactional=True)

---

## 環境変数（.env）について

自動読み込みされる環境変数（足りないと例外を投げる必須設定など）

必須（コード内で _require を使っているため未設定だと ValueError が発生します）
- JQUANTS_REFRESH_TOKEN = <J-Quants のリフレッシュトークン>
- KABU_API_PASSWORD = <kabuステーション API パスワード（発注等を有効にする場合）>
- SLACK_BOT_TOKEN = <Slack Bot トークン（通知用）>
- SLACK_CHANNEL_ID = <Slack チャンネル ID（通知先）>

オプション（デフォルト値あり）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト: INFO

注意
- プロジェクトルート判定は .git または pyproject.toml を上位ディレクトリから探索します。配置によっては .env 自動ロードが行われない場合があります。
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例（.env）
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要 API の例）

以下は代表的な利用例です。実際はスクリプトやジョブランナーに組み込んでください。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection オブジェクト
```

2) 日次 ETL（J-Quants から calendar / prices / financials を取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
import duckdb

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（例）
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存数}
```

4) ファクター・リサーチ（例：モメンタム計算・IC）
```python
import datetime
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
target = datetime.date(2025, 1, 10)

factors = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

5) J-Quants データ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
quotes = fetch_daily_quotes(date_from=..., date_to=...)
fins = fetch_financial_statements(date_from=..., date_to=...)
```
jquants_client は内部でトークン自動取得・リトライ・レート制御を行います。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の自動読み込みロジック、Settings クラス（必須環境変数の取得）
- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py : RSS 収集・前処理・DB 保存・銘柄抽出
  - schema.py : DuckDB スキーマ定義・init_schema / get_connection
  - pipeline.py : ETL 実行ロジック（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management.py : 市場カレンダー管理（営業日判定・update ジョブ）
  - audit.py : 監査ログ用スキーマの定義・初期化
  - stats.py : 統計ユーティリティ（z-score 正規化）
  - features.py / etl.py : 公開インターフェースの再エクスポート
- research/
  - __init__.py : 研究用 API の再エクスポート
  - factor_research.py : ファクター計算（momentum, volatility, value）
  - feature_exploration.py : 将来リターン・IC・統計サマリー
- strategy/ (プレースホルダ)
- execution/ (プレースホルダ)
- monitoring/ (プレースホルダ)

各ファイルには docstring に設計方針や注意点が詳述されています。実装部分は基本的に DuckDB 接続を受け取り DB のみを操作する設計です（外部発注 API への直接操作は別モジュールへ分離する想定）。

---

## 開発・運用上の注意点

- 環境変数が足りない状態で実行すると Settings のプロパティが ValueError を投げます（必須トークン等の漏れに気をつけてください）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードしたくない／CI で差し替えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- jquants_client は API レート制限を守るために内部でスロットリングを行います（120 req/min）。大量データ収集は時間を要する点に注意してください。
- DuckDB のバージョン差異により一部の制約や挙動（例えば FK の ON DELETE オプションなど）に違いが出る可能性があるため、運用環境の duckdb バージョンを固定することを推奨します。
- news_collector は外部 URL を解析します。SSRF や XML Bomb 等に対する防御を実装していますが、追加の運用ルール（プロキシやアウトバウンド制限）を検討してください。
- audit.init_audit_schema は UTC タイムゾーンを強制するため、DB 接続のタイムゾーン扱いに注意してください。

---

疑問点や README に追加したい情報（CI/CD、テスト、lint、依存リストの明示など）があれば教えてください。必要に応じて README を拡張します。