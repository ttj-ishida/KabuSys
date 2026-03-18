# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータレイクとして用い、J-Quants API 等からのデータ取得、ETL、品質チェック、特徴量計算、ニュース収集、監査ログなどのユーティリティを提供します。

## 概要
- データ取得（J-Quants）
- DuckDB スキーマ定義と初期化
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- ニュース（RSS）収集と銘柄紐付け
- ファクター / 研究用ユーティリティ（モメンタム・ボラティリティ・バリュー等）
- 監査ログ（発注→約定のトレース）スキーマ

このリポジトリは「データプラットフォーム層」「リサーチ層」「実行（Execution）層」を包含するユーティリティ群を提供します。  
本コードは本番口座への直接発注を行う部分（execution や監視ロジック）は別モジュール／上位アプリケーションから呼び出して使う想定です。

## 主な機能一覧
- 環境変数読み込み・管理（.env / .env.local、自動ロード）
- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レート制限、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等的保存（ON CONFLICT 対応）
- DuckDB スキーマと初期化（raw / processed / feature / execution / audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）、テキスト前処理、銘柄コード抽出、DB保存（冪等）
- 研究モジュール：将来リターン計算、IC（スピアマン）、ファクター計算（momentum/volatility/value）、Zスコア正規化
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal / order_request / executions 等）のスキーマ初期化

## 必要要件
- Python 3.10+
- パッケージ（代表例）
  - duckdb
  - defusedxml
（必要に応じて requests 等を追加してください。README のサンプルは最小限の依存で動くことを想定しています。）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージ配布がある場合は `pip install -e .` など
```

## 環境変数（必須 / 推奨）
重要な環境変数（最低限設定が必要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意 / デフォルト値あり:
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — sqlite (monitoring 用)（デフォルト: data/monitoring.db）

自動 .env 読み込み:
- ルートに `.env` / `.env.local` があれば自動で読み込みます（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。
- 自動読み込みを無効化する場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=YOUR_REFRESH_TOKEN
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

## セットアップ手順（開発環境向け）
1. リポジトリをクローンし仮想環境を作成
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# もしパッケージ化されていれば:
# pip install -e .
```

2. 必要な環境変数を設定（.env を作成）
3. DuckDB スキーマを初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH のデフォルトを読む
conn = init_schema(settings.duckdb_path)
# :memory: を使いたい場合:
# conn = init_schema(":memory:")
```

## 使い方（代表的な操作例）

- 日次 ETL を実行する（市場カレンダー取得 → 株価差分取得 → 財務取得 → 品質チェック）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import datetime

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=datetime.date.today())
print(result.to_dict())
```

- 単体の prices ETL（差分）を実行する:
```python
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import get_connection
from kabusys.config import settings
import datetime

conn = get_connection(settings.duckdb_path)
fetched, saved = run_prices_etl(conn, target_date=datetime.date.today())
print(f"fetched={fetched}, saved={saved}")
```

- ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes は銘柄抽出に使う有効な4桁コードの集合を渡す（None なら紐付けスキップ）
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)
```

- 研究 / ファクター計算
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.schema import get_connection
import datetime

conn = get_connection("data/kabusys.duckdb")
d = datetime.date(2024, 1, 10)

mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])

print("IC:", ic)
print("summary:", summary)
```

- J-Quants からのデータ取得（低レベル API）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings による自動リフレッシュあり
records = fetch_daily_quotes(id_token=token, date_from=datetime.date(2024,1,1), date_to=datetime.date(2024,1,31))
```

## 注意事項 / 運用上のポイント
- J-Quants API のレート制限（120 req/min）に従うよう実装されていますが、上位で短時間に多量の呼び出しを行う場合は注意してください。
- ETL は差分取得（最終取得日 → target_date）を行う仕様です。初回ロードや大きなバックフィル時は対象範囲を明示的に指定してください。
- ニュース収集では SSRF 対策、受信サイズ制限、XML パースの安全対策を実装していますが、外部ソースの扱いには留意してください。
- 本番（live）環境では特に env 設定やログレベルの管理、監査ログ（audit）の初期化とバックアップ方針を検討してください。

## ディレクトリ構成（主要ファイル）
（リポジトリルートの src/kabusys を基準）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py     — RSS 取得、前処理、DB 保存、銘柄抽出
    - schema.py             — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - quality.py            — データ品質チェック（missing/spike/duplicates/etc）
    - features.py           — 公開インターフェース（zscore 再エクスポート）
    - calendar_management.py— 市場カレンダー更新・営業日判定・ユーティリティ
    - audit.py              — 監査ログ（signal/order_request/executions）スキーマ初期化
    - etl.py                — ETLResult の再エクスポート
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン、IC、統計サマリー、rank
    - factor_research.py     — momentum / volatility / value 等のファクター計算
  - strategy/               — 戦略関連（未実装のエントリ）
  - execution/              — 発注実装（未実装のエントリ）
  - monitoring/             — 監視（未実装のエントリ）

各モジュールはドキュメント文字列で設計方針や入力/出力の仕様が明記されています。関数は DuckDB 接続オブジェクトを受け取る設計が多く、テストや運用での接続差し替えが容易です。

## 開発 / テスト
- 単体テストフレームワーク（pytest 等）はこのコードベースには含めていませんが、DuckDB のインメモリ接続（":memory:"）を使えば容易にテスト可能です。
- 環境変数自動ロードをテストで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## ライセンス・貢献
- 本リポジトリのライセンスや貢献ポリシーはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

README に記載した例は、基本的な利用シナリオの説明です。実際の運用ではログ設定、エラーハンドリング、秘密情報の管理（シークレットストアや CI のシークレット機能）を適切に行ってください。必要であれば、この README を用途に合わせて拡張しますので、追記したい項目（例: 実行サービスの systemd 定義、Dockerfile、CI/CD 設定など）があれば教えてください。