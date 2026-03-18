# KabuSys

日本株向けの自動売買／データプラットフォーム基盤ライブラリです。  
データ取得（J-Quants）、DuckDB ベースのデータスキーマ、ETL パイプライン、ニュース収集、ファクター計算（リサーチ用）や監査ログなど、戦略開発と運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境設定管理
  - .env（および .env.local）からの自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ヘルパー（settings オブジェクト）
- データ取得（J-Quants API クライアント）
  - 日足（OHLCV）・財務データ・JPX マーケットカレンダーの取得
  - ページネーション対応、レート制限（120 req/min）・リトライ・トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- データ層（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - 監査ログ用スキーマ（signal / order_request / execution 等）
- ETL パイプライン
  - 差分更新（最終取得日を基に差分を取得）
  - 市場カレンダー先読み、バックフィル、品質チェック連携
  - ETL 実行結果を表す ETLResult 型
- データ品質チェック
  - 欠損、重複、スパイク（急騰/急落）、日付不整合の検出
- ニュース収集
  - RSS 取得・前処理（URL除去・正規化）・記事ID生成（SHA-256）・DuckDB 保存
  - SSRF / gzip-bomb / XML攻撃対策（defusedxml＋検証）
  - 記事と銘柄コードの紐付け
- リサーチ（特徴量探索・ファクター）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターンの計算、IC（スピアマン）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ（トレーサビリティ）
  - 戦略→シグナル→オーダー→約定まで UUID 連鎖でトレース可能なスキーマ

---

## 要件

- Python 3.10+
  - （コード中で `X | Y` 型表記を使用しているため 3.10 以上が必要）
- 必須ライブラリ（例）
  - duckdb
  - defusedxml

インストール例:
```
pip install duckdb defusedxml
```

（プロジェクトの配布方法によっては `pip install -e .` や poetry を利用してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
   - プロジェクトルートに `.git` または `pyproject.toml` があることを想定して自動 .env ロードが働きます。

2. 必要パッケージをインストール
   - 例: pip install duckdb defusedxml

3. 環境変数設定
   - ルートに `.env` / `.env.local` を置くと自動でロードされます（モジュール import 時に自動読み込み）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに便利）。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack の投稿先チャンネル ID（必須）
   - KABU_API_PASSWORD: kabu API のパスワード（発注機能を使う場合）
   - （オプション）KABU_API_BASE_URL, DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH

例 .env:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

以下は主要ユースケースのサンプルです。実行前に必要な環境変数を設定してください。

- DuckDB スキーマ初期化（データベース作成）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照します（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())

print(result.to_dict())
```

- ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", ...}  # 事前に有効銘柄コードリストを用意
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

- ファクター / リサーチ系関数の利用例
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)

momentum = calc_momentum(conn, target)
volatility = calc_volatility(conn, target)
value = calc_value(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

# 例: mom_1m と fwd_1d の IC を計算
ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC (mom_1m vs fwd_1d):", ic)
```

- 監査ログスキーマ初期化（監査用 DB を別ファイルで持つ場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 注意点・開発者向けメモ

- .env のパースは独自実装であり、コメント・クォート・export 形式に対応します。プロジェクトルートの検出は .git または pyproject.toml に依存します。
- 自動 .env 読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants クライアントは urllib を使っており、HTTP レスポンスの扱いやリトライ等はライブラリ内で行われます。テストで ID トークンや _urlopen のモック注入が可能です。
- news_collector は SSRF や XML 攻撃、gzip-bomb 等に対する複数の防御策を実装しています。テスト時はネットワークをモックすることを推奨します。
- DuckDB の接続はスレッドセーフ設計ではないため、複数プロセス／スレッドでの運用では接続管理に注意してください。
- 多くの関数は DuckDB 接続を引数で受け取る設計です（テスト容易性のため）。インメモリ DB を使う場合は db_path=":memory:" を使用できます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント + 保存ロジック
    - news_collector.py        — RSS ニュース収集・保存
    - schema.py                — DuckDB スキーマ定義 / init_schema
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - quality.py               — データ品質チェック
    - stats.py                 — 統計ユーティリティ（zscore）
    - features.py              — 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py   — 市場カレンダー管理 / ジョブ
    - audit.py                 — 監査ログスキーマ初期化
    - etl.py                   — ETLResult の公開インターフェース
  - research/
    - __init__.py
    - feature_exploration.py   — 将来リターン / IC / サマリー等
    - factor_research.py       — Momentum / Volatility / Value 等
  - strategy/                   — 戦略層のプレースホルダ（拡張箇所）
  - execution/                  — 発注 / ブローカ連携のプレースホルダ
  - monitoring/                 — 監視系のプレースホルダ

---

## テスト・デバッグのヒント

- 環境変数の自動ロードを無効化してユニットテストを制御したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- news_collector のネットワーク呼び出しは _urlopen を介しているため、単体テストではこの関数をモックすると HTTP レスポンスを簡単に差し替えられます。
- J-Quants API 呼び出しのテストでは id_token を外部から注入可能（関数引数）なので、実 API を叩かないモックレス構成にできます。
- DuckDB を使ったテストは ":memory:" を db_path に指定するとインメモリ DB が利用できます。

---

必要であれば、README に含めるサンプル .env.example、CI 実行手順（ETL の定期実行例、systemd / cron / GitHub Actions など）、および API 使用例（kabuステーション連携）を追加できます。追加希望を教えてください。