# KabuSys

KabuSys は日本株自動売買・リサーチ向けのライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算、監査ログ（発注から約定までのトレース）、およびマーケットカレンダー管理などの機能を提供します。

バージョン: 0.1.0

---

## 概要

本プロジェクトは以下の用途を想定しています。

- J-Quants API からの日次株価・財務・カレンダーなどの差分 ETL（DuckDB へ保存）
- RSS を用いたニュース収集と記事の前処理・保存
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（銘柄別 ai_scores、マクロセンチメント）
- ETF（1321）200日移動平均乖離とマクロセンチメントを合成した市場レジーム判定
- ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution のトレース）用スキーマ初期化ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）

設計上の特徴：
- ルックアヘッドバイアスを避けるため、内部で date.today() 等を直接参照せず、呼び出し側から target_date を明示的に渡す設計
- DuckDB を中心に SQL を活用した高速処理
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを備える

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ユーティリティ

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（kabusys.data.jquants_client）: fetch / save 関数
  - 市場カレンダー管理（kabusys.data.calendar_management）
  - ニュース収集（kabusys.data.news_collector）
  - データ品質チェック（kabusys.data.quality）
  - 統計ユーティリティ（kabusys.data.stats）
  - 監査ログ初期化（kabusys.data.audit）

- AI (OpenAI) 関連（kabusys.ai）
  - ニュースセンチメント: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定: score_regime(conn, target_date, api_key=None)

- リサーチ（kabusys.research）
  - ファクター計算: calc_momentum / calc_volatility / calc_value
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats より）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（PEP 604 の型記法（|）を使用）
- DuckDB、OpenAI SDK、defusedxml などが必要

推奨インストール例（最低限の依存をインストール）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 必要に応じて他の依存パッケージを追加
```

パッケージをソースから開発インストールする場合（プロジェクトルートに pyproject.toml がある前提）:

```bash
pip install -e .
```

環境変数（.env）
- プロジェクトルートの .env / .env.local を自動で読み込みます（CWD ではなくパッケージ位置からプロジェクトルートを探索）。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（.env に設定する例）:

- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト）
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb  # デフォルト
- SQLITE_PATH=data/monitoring.db    # デフォルト
- KABUSYS_ENV=development|paper_trading|live  # default=development
- LOG_LEVEL=INFO|DEBUG|...  # default=INFO

注意:
- .env.local は .env を上書きします（.env.local の方が優先）。
- 自動ロード時、OS 環境変数が保護されます（.env に同名キーがあっても上書きされません）。

---

## 使い方（主要ユースケース）

以下は簡単なコード例です。実行する環境では OpenAI と J-Quants の認証情報が必要です。

1) DuckDB 接続を作成して日次 ETL を実行する

```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は .env から読み込まれるかデフォルトを返します
conn = duckdb.connect(str(settings.duckdb_path))

result = run_daily_etl(conn)
print(result.to_dict())
```

2) ニュースの AI スコアを取得して ai_scores に保存する

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# target_date は評価対象の「ビジネス日」を指定（例: 2026-03-20）
written = score_news(conn, target_date=date(2026,3,20))
print(f"written scores: {written}")
```

- score_news は引数 api_key=None の場合、環境変数 OPENAI_API_KEY を参照します。直接渡すことも可能です。

3) 市場レジームを判定して market_regime に書き込む

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

4) 監査ログ（audit）用 DB を初期化する

```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn は初期化済み DuckDB 接続
```

5) 研究用ファクター計算の実行例

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
vol = calc_volatility(conn, date0)
val = calc_value(conn, date0)
```

テスト・デバッグのためのヒント
- OpenAI 呼び出しは内部で _call_openai_api を使用しています。ユニットテストでは monkeypatch / unittest.mock.patch で差し替えて応答を模擬できます（例: kabusys.ai.news_nlp._call_openai_api）。
- 自動.env読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要モジュールの概観です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                        # 環境変数・.env 読み込み
  - ai/
    - __init__.py
    - news_nlp.py                     # ニュースセンチメント（score_news）
    - regime_detector.py              # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               # J-Quants API クライアント（fetch/save）
    - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
    - etl.py                          # ETLResult 再エクスポート
    - news_collector.py               # RSS 収集と保存
    - calendar_management.py          # マーケットカレンダー管理
    - quality.py                      # データ品質チェック
    - stats.py                        # 統計ユーティリティ（zscore_normalize 等）
    - audit.py                        # 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py              # ファクター計算
    - feature_exploration.py          # 将来リターン・IC 等
  - (その他: strategy / execution / monitoring 等は将来的な拡張想定)

---

## 実運用での注意点

- 本ライブラリは実際の発注（マネーを動かす）機能部分は分離されています。実際にブローカーへ発注する場合は安全性・冪等性・リスク管理の追加実装が必要です。
- OpenAI 呼び出しはコストが発生します。バッチサイズや呼び出し頻度に注意してください。
- J-Quants API はレート制限があります（実装内で固定間隔スロットリングを行っていますが、運用上の制約に注意してください）。
- DuckDBのスキーマやテーブルは初期化処理が必要です（schema 定義は別途用意されている前提）。audit.init_audit_db は監査テーブルの初期化を行いますが、それ以外のテーブル（raw_prices 等）はプロジェクトのスキーマ初期化手順に従って作成してください。

---

## テストとデバッグ

- OpenAI / J-Quants のネットワーク依存部分はモック可能な設計です。テストでは _call_openai_api や kabusys.data.jquants_client._request などをパッチしてレスポンスを固定できます。
- 自動で .env を読み込みますが、単体テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定して環境を固定化することが推奨されます。

---

README に記載のない詳細な API やテーブル定義・スキーマはソースコード（kabusys.data.*）を参照してください。質問や README の追加整備（例: CLI 実行例、pyproject/requirements ファイルの整備等）が必要であれば教えてください。