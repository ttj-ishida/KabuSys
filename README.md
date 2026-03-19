# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群。データ取得（J‑Quants）、ETL、特徴量計算、ニュース収集、監査ログ、スキーマ定義など、戦略実行に必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は DuckDB を中心としたローカルデータプラットフォームと、J‑Quants API からのデータ取得、ニュース収集、データ品質チェック、特徴量生成、監査ログ管理などを備えたユーティリティ群です。実際の発注や本番運用のための仕組み（kabuステーション連携・Slack 通知など）と研究（research）向けの解析機能を分離して実装しています。

設計上のポイント:
- DuckDB をデータストアとして使用（冪等な保存・ON CONFLICT を利用）
- J‑Quants API はレート制限／リトライ／トークン自動リフレッシュ対応
- RSS ベースのニュース収集は SSRF/サイズ/Gzip/XML 攻撃対策を実装
- データ品質チェック（欠損・スパイク・重複・日付不整合）を提供
- 研究用モジュールは外部ライブラリに依存しない実装を目指す

---

## 主な機能一覧

- data
  - jquants_client: J‑Quants からの株価・財務・カレンダー取得、DuckDB への保存ユーティリティ
  - pipeline: 日次 ETL（差分取得、バックフィル、品質チェック）
  - news_collector: RSS 収集、前処理、DuckDB 保存、銘柄抽出
  - schema / audit: DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution / Audit）
  - quality: データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - stats: Z スコア正規化などの統計ユーティリティ
  - calendar_management: 市場カレンダー管理・営業日判定 API
- research
  - feature_exploration: 将来リターン計算、IC（情報係数）、ファクター統計
  - factor_research: momentum / volatility / value ファクター計算
- config: .env / 環境変数読み込み、Settings オブジェクト
- monitoring / execution / strategy: パッケージ構成（将来的な拡張・実装箇所）

---

## 前提・依存関係

- Python 3.10+
- 必須ライブラリ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリで十分な部分も多いですが、実運用では下記を推奨します:
  - requests 等（任意。現在の実装は urllib を使用）
  - kabu ステーション連携ライブラリ（実装次第）
- 環境変数による設定管理（.env ファイルをプロジェクトルートに置くと自動で読み込み）

インストール例（venv を想定）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発時はプロジェクトルートで editable install を行う場合:
# pip install -e .
```

---

## 環境変数 / 設定

パッケージは .env（および .env.local）からプロジェクトルート基準で自動的に読み込みます（CWD ではなくソース位置から検索）。自動読み込みを無効化する場合は以下を設定します:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な設定キー（Settings API と対応）:
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須：発注機能使用時）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須：通知機能使用時）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須：通知機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

Settings は Python から以下のように取得できます:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
db = settings.duckdb_path
```

.env.example を参考に .env を作成してください（リポジトリに含めることは避ける）。

---

## セットアップ手順

1. Python 環境を用意
2. 必要ライブラリをインストール
   - pip install duckdb defusedxml
3. プロジェクトルートに .env を作成し、必要な環境変数を設定
4. DuckDB スキーマを初期化
   - Python から初期化する方法（例）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```
5. 監査ログ用 DB を初期化（任意）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
audit_conn.close()
```

---

## 使用例（よく使う操作）

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- ニュース収集ジョブ（RSS 収集 -> raw_news 保存 -> 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードセット（抽出精度向上のため）
known_codes = {"7203", "6758", "9432"}
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # { source_name: saved_count, ... }
conn.close()
```

- 研究用: ファクター計算・IC 計算
```python
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 12)
factors = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(factors, ["mom_1m","mom_3m","ma200_dev"])
conn.close()
print("IC:", ic)
print("summary:", summary)
```

- 市場カレンダー関連:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
print(is_trading_day(conn, date.today()))
print(next_trading_day(conn, date.today()))
conn.close()
```

---

## よくある運用フロー

1. スケジューラ（cron / Airflow 等）で nightly ETL を実行する（run_daily_etl）。
2. ETL 後に特徴量生成スクリプトを実行し features テーブルを更新する（独自実装）。
3. 戦略がシグナルを生成 → signal_queue / orders / executions による監査記録を残す。
4. ニュース収集を定期的に行い、raw_news / news_symbols を更新する。
5. 品質チェックの結果を Slack 等で通知し、手動介入の判断に利用する。

---

## ディレクトリ構成

（リポジトリ内の主要ファイル・モジュール一覧）

- src/kabusys/
  - __init__.py
  - config.py                     : 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py            : J‑Quants API クライアント・保存ロジック
    - news_collector.py            : RSS 収集・前処理・保存
    - schema.py                    : DuckDB スキーマ定義・init_schema
    - stats.py                     : 統計ユーティリティ（zscore_normalize）
    - pipeline.py                  : ETL パイプライン（run_daily_etl 等）
    - features.py                  : 特徴量ユーティリティ公開インターフェース
    - calendar_management.py       : マーケットカレンダー管理
    - audit.py                     : 監査ログ用スキーマ初期化
    - etl.py                       : ETL 用型再公開
    - quality.py                   : データ品質チェック
  - research/
    - __init__.py                  : 研究用 API エクスポート
    - feature_exploration.py       : 将来リターン・IC・サマリー
    - factor_research.py           : momentum/value/volatility ファクター
  - strategy/                       : 戦略実装用パッケージ（拡張用）
  - execution/                      : 発注・実行管理（拡張用）
  - monitoring/                     : 監視用パッケージ（拡張用）

---

## 注意点 / 運用上のヒント

- .env ファイル読み込み
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env / .env.local を自動読込します。
  - OS 環境変数 > .env.local > .env の優先順位です。
  - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルパスは Settings.duckdb_path で取得できます。":memory:" を使うとインメモリ DB。
- J‑Quants API 利用時はレート制限やトークン管理に注意。jquants_client は自動リトライ・レート制御を実装していますが、運用側でも適切に制御してください。
- ニュース収集では外部 HTTP の安全性対策（SSRF・サイズ制限・gzip・XML）を行っていますが、未知のフィードに対しては注意深く監視してください。
- 実際の発注や live 環境での稼働時は settings.is_live / is_paper フラグやログレベル等を適切に設定してください。

---

## 貢献 / ライセンス

（リポジトリに LICENSE がある場合はそちらを参照してください。ローカル開発用に変更・拡張していただいて構いません。）

---

README は以上です。必要であれば、README に追加するコマンド例（systemd Unit / cron サンプル / Airflow DAG の骨子）、あるいは各モジュールの API リファレンス（関数一覧と引数説明）を作成できます。どれを優先しますか？