# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、マーケットカレンダー等のユーティリティを提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ取得から特徴量生成、ニュースの自然言語処理、マーケットレジーム判定、監査ログ管理までをカバーする内部ライブラリ群です。主要な設計方針として次が挙げられます。

- Look-ahead バイアスを避ける（target_date 指向、datetime.today()/date.today() を不用意に参照しない）
- DuckDB を用いたローカル分析基盤（冪等な保存・ON CONFLICT ロジック）
- OpenAI（gpt-4o-mini）によるニュースセンチメント判定（JSON Mode を利用）
- J-Quants API クライアント（レート制限・リトライ・トークン自動更新）
- ニュース収集時の SSRF / XML 攻撃対策（URL 検証・defusedxml）
- 監査ログ（signal → order_request → executions）のテーブル定義と初期化ユーティリティ

パッケージバージョン: 0.1.0

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー、上場銘柄情報）
  - 差分 ETL 実行（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS 取得、URL 正規化、記事の冪等保存、銘柄紐付け
  - SSRF / サイズ / XML パース対策
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントスコアを ai_scores に書き込む（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC 計算・統計サマリー
- データユーティリティ
  - カレンダー管理（is_trading_day / next_trading_day / get_trading_days）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計：Z スコア正規化
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出、環境変数優先）

---

## 前提（依存関係・動作確認）

最低限想定される Python パッケージ（例）:

- python >= 3.10
- duckdb
- openai
- defusedxml

推奨の requirements.txt（一例）:
```
duckdb
openai
defusedxml
```

※ 実行環境に合わせて必要なパッケージを追加してください（例: テスト用に pytest 等）。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または個別に pip install duckdb openai defusedxml
4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基に自動で `.env` / `.env.local` を読み込みます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
5. 必須の環境変数を設定（詳しくは次節）

---

## 環境変数（主なもの）

settings モジュールは .env または環境変数から設定を取得します。主なキー：

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。
- OPENAI_API_KEY (必須 for AI 機能)
  - news_nlp / regime_detector の OpenAI 呼び出しで使われます。関数呼び出し時に api_key を直接渡すことも可能。
- KABU_API_PASSWORD
  - kabuステーション API 用（本リポジトリの一部が参照）。
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live（必須ではないが有効値は上記3つ）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

.env の自動ロード順序:
- OS 環境変数 > .env.local > .env
- プロジェクトルートはパッケージ内部の _find_project_root() により .git または pyproject.toml を基に探索されます。

---

## 使い方（コード例）

以下は代表的なユースケースのサンプルです。すべて Python スクリプトから呼び出します。

1) DuckDB 接続と ETL の実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントスコア（OpenAI API キーは OPENAI_API_KEY または api_key 引数で指定）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用する場合
print("書き込み銘柄数:", n_written)
```

3) 市場レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査DB 初期化（監査用 DuckDB を初期化）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリがなければ自動作成
```

5) ファクター計算・研究用ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

注意点:
- score_news / score_regime は OpenAI を呼びます。API レスポンス不備やネットワークエラー時はフォールバックロジック（0.0）で続行する設計です。
- テスト時は各モジュールの内部関数（例: kabusys.ai.news_nlp._call_openai_api）をモックして外部呼び出しを置き換えられます。

---

## よくある操作／トラブルシュート

- .env を自動で読み込ませたくない／テストで環境変数を制御したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化します。
- OpenAI の JSON レスポンスが不正な場合、関数は例外を投げずログに警告を出します（fail-safe 動作）。
- J-Quants API の 401 発生時はライブラリがトークン自動更新を試みます（get_id_token を内部で利用）。
- DuckDB executemany の互換性に関する注意: 一部実装で空の executemany がエラーになるため、書き込み前に空チェックを行っています。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env ロード / Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py         : ニュース記事の OpenAI によるスコアリング（score_news）
    - regime_detector.py  : マクロ + ETF MA200 を合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   : J-Quants API クライアント（取得・保存ロジック・リトライ・レート制御）
    - pipeline.py         : ETL パイプライン（run_daily_etl 等）
    - etl.py              : ETLResult の再エクスポート
    - news_collector.py   : RSS 取得・前処理・raw_news 保存
    - calendar_management.py : マーケットカレンダー管理（is_trading_day / next_trading_day 等）
    - quality.py          : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py            : zscore_normalize 等の統計ユーティリティ
    - audit.py            : 監査ログスキーマ定義 / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  : Momentum / Volatility / Value の計算
    - feature_exploration.py : 将来リターン / IC / 統計サマリー 等
  - ai・data・research 以下の各モジュールは DuckDB 接続を受け取り、データ参照・書き込みを行います。

---

## 開発・テストに関するメモ

- OpenAI 呼び出し部分はモック可能（関数単位で差し替えを想定）。
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")
- .env パースはシェル風の記法（export KEY=val、シングル/ダブルクォート、コメント）に対応しています。
- ニュース収集（RSS）では SSRF 対策が組み込まれているため、ローカルアドレスへのアクセスは拒否されます。
- DuckDB に格納する際のタイムスタンプは UTC を原則とします（監査DB 初期化で TimeZone='UTC' を設定）。

---

## ライセンス・貢献

本 README はコードベースの説明目的で生成しています。実際のライセンス表記や貢献手順（CONTRIBUTING.md）はリポジトリのポリシーに従ってください。

---

必要であれば README に含めるサンプル .env.example、より詳細な API 使用例、ユニットテストのモック例（OpenAI / J-Quants の Mocking）などを追記します。どの情報を追加しますか？