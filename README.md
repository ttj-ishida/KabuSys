# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL、ニュースNLP、ファクター計算、監査ログ、J-Quants および kabu ステーション連携などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを構築するための内部ライブラリ群です。主な目的は次の通りです。

- J-Quants API からのデータ取得（株価日足、財務、上場情報、カレンダー）
- DuckDB を用いたデータ保存・ETL パイプライン
- ニュース記事の収集・前処理と OpenAI によるニュースセンチメント解析（AI スコア）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量探索（リサーチ用）
- 監査ログ（signal → order → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント:
- ルックアヘッドバイアスを避けるため、内部処理は明示的な target_date を受け取り、date.today()/datetime.today() を直接参照しない箇所が多くあります。
- 各種 API 呼び出しはリトライ・バックオフ・フェイルセーフを備えています。
- DuckDB を中心に SQL と Python の組合せで効率的に処理します。

---

## 主な機能一覧

- ETL（kabusys.data.pipeline）
  - run_daily_etl: 市場カレンダー / 株価 / 財務 を差分取得して保存、品質チェックまで実行
  - 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl

- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_* / save_* の一貫した取得・保存ロジック（ページネーション、リトライ、レート制限、冪等保存）

- ニュース収集・NLP（kabusys.data.news_collector, kabusys.ai.news_nlp）
  - RSS 取得・前処理・raw_news 保存
  - OpenAI を使った銘柄別ニュースセンチメント解析（ai_scores へ保存）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントの合成で日次レジーム判定を実施

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ等

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を含む監査用スキーマの初期化（冪等）

- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合を検出し QualityIssue のリストを返す

---

## 依存関係（主なもの）

最低限の依存（抜粋）:

- Python 3.9+
- duckdb
- openai (OpenAI SDK)
- defusedxml

（実行環境により追加パッケージが必要になる場合があります。プロジェクトに requirements.txt / pyproject.toml がある想定でセットアップしてください。）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出します。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（主要なもの）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（ETL で使用）

- KABU_API_PASSWORD (必須)  
  kabu ステーション API のパスワード

- OPENAI_API_KEY (推奨)  
  OpenAI 呼び出し用の API キー。関数に api_key を渡すことも可。

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)  
  通知等で利用する場合の LINE トークン

- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)  
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)  
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視用設定

- KABUSYS_ENV (任意, default: development) 有効値: development, paper_trading, live  
- LOG_LEVEL (任意, default: INFO) 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

例: `.env`（一部）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

注意: config モジュールは `.env` → `.env.local` の順でロードし、既存 OS 環境変数は上書きされません（ただし `.env.local` は `.env` を上書き可）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、プロジェクトルートに移動します（.git または pyproject.toml があることを想定）。

2. 仮想環境作成（推奨）
```
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows
```

3. 必要パッケージをインストール（例）
```
pip install duckdb openai defusedxml
```
（実際は pyproject.toml / requirements.txt があればそれを使用してください）

4. 環境変数を設定（`.env` を作成）
- 少なくとも `JQUANTS_REFRESH_TOKEN` と `KABU_API_PASSWORD` を設定してください。
- OpenAI を使う場合は `OPENAI_API_KEY` も設定します。

5. DuckDB 用ディレクトリ作成（デフォルトパス使用時）
```
mkdir -p data
```

---

## 使い方（主要な関数例）

以下は Python REPL / スクリプトから呼ぶ想定の例です。import 先はパッケージ名 `kabusys`。

- DuckDB 接続の作成例
```py
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（全 ETL + 品質チェック）
```py
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を None にすると今日が使用されます（内部では trading_day に調整）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（AI）を実行
```py
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示するか、環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written {n_written} codes")
```

- 市場レジーム判定
```py
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB の初期化（別 DB を使用する場合）
```py
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 必要に応じて audit_conn を利用して発注ログ等を記録
```

- ファクター計算（リサーチ）
```py
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

ログレベルを調整して詳細を出力する場合は `LOG_LEVEL` を設定してください。

---

## テスト・開発時の注意点

- OpenAI / J-Quants 等の外部 API 呼び出しは、ユニットテストではモック（patch）して差し替えることを想定しています。モジュール内の API 呼び出し関数（例: `_call_openai_api`）はテスト用に差し替え可能です。
- 自動的に `.env` を読み込むため、テストで環境を固定したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany は空リストを受け付けないバージョンの互換性対応がコード内にあります。テスト時も入出力のパラメータが空でないことを確認してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル / モジュール構成（src/kabusys 配下）:

- __init__.py
  - パッケージ初期化。公開サブパッケージを定義。

- config.py
  - 環境変数の自動ロード・Settings クラス（各種設定の取得）

- ai/
  - __init__.py
  - news_nlp.py: ニュースセンチメント解析（OpenAI 呼び出し、ai_scores への保存）
  - regime_detector.py: 市場レジーム判定ロジック（ETF + マクロニュース）

- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（fetch / save）
  - pipeline.py: ETL パイプラインと run_daily_etl
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS 収集と raw_news への保存
  - calendar_management.py: 市場カレンダー管理（営業日判定等）
  - quality.py: データ品質チェック
  - stats.py: 汎用統計（zscore 正規化）
  - audit.py: 監査ログ（テーブル定義・初期化）

- research/
  - __init__.py
  - factor_research.py: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration.py: 将来リターン、IC、統計サマリ、rank 等

（上記は主要モジュールの抜粋です。詳細は各ソースを参照してください。）

---

## 付記 / 設計上の注意

- ルックアヘッドバイアス回避のため、多くの関数は target_date を明示的に受け取り、DB クエリで date < target_date や date = target_date のように厳密に扱います。
- 外部 API 呼び出しは適切なリトライ / バックオフを実装しています。APIキーやレート制限に注意して運用してください。
- 監査ログは削除されない前提で設計されており、order_request_id は冪等キーとして扱われます。

---

もし README に追加したい具体的な実行スクリプトや CI / デプロイの手順があれば、その情報を教えてください。README をそれに合わせて更新します。