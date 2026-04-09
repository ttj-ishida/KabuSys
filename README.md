# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、研究用ファクター計算、ニュースのNLPによるAIスコアリング、監査ログ（トレーサビリティ）、マーケットカレンダー管理などを含みます。

主な設計方針：
- ルックアヘッドバイアス対策（内部で datetime.today()/date.today() を無秩序に参照しない）
- DuckDBを中心としたローカルDB保存（冪等性を重視）
- 外部API呼び出しに対してリトライ・バックオフ・レート制御を実装
- ETL・品質チェックはフェイルセーフ（1ステップ失敗でも他は継続）

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価（日次OHLCV）、財務データ、マーケットカレンダーを差分取得（ページネーション対応）
  - ETL 結果を ETLResult オブジェクトで取得
  - データ保存は冪等（ON CONFLICT DO UPDATE）で実施

- データ品質チェック
  - 欠損（OHLC）検出、前日比スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトで報告

- マーケットカレンダー管理
  - market_calendar テーブルの更新・営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - カレンダーが無い場合は曜日ベースでフォールバック

- ニュース収集
  - RSS 取得・前処理・SSRF対策・トラッキングパラメータ除去・raw_news 登録
  - 記事IDは正規化URLのSHA-256先頭を使用（冪等性）

- ニュースNLP（AI）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコアリング（score_news）
  - マクロニュースとETF 1321 の200日MA乖離を組み合わせた市場レジーム判定（score_regime）
  - API呼び出しはリトライ・タイムアウト・レスポンス検証を実装

- 研究（research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（prices_daily / raw_financials を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター要約、Zスコア正規化ユーティリティ

- 監査ログ（audit）
  - シグナル → 発注 → 約定までの監査テーブルを提供（冪等・完全トレーサビリティ）
  - init_audit_db / init_audit_schema で初期化

---

## 必要な依存パッケージ（代表例）

コード内で利用している主な外部依存：
- duckdb
- openai
- defusedxml

（プロジェクトの requirements.txt や pyproject.toml があればそれに従ってください）

---

## セットアップ手順（ローカル）

例: 仮想環境を作成してパッケージを開発インストールする手順

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （setup.py / pyproject.toml がある場合）
     - pip install -e .

3. 環境変数 / .env の準備
   - プロジェクトルート（.git や pyproject.toml のある場所）に `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

代表的な環境変数（最低限必要なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を使う場合は必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能等で使用）
- KABUSYS_ENV: environment モード（development / paper_trading / live）。デフォルトは development
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- PAPER_FILL_MODE: paper trading のフィルモード（instant / partial / never / reject）

簡易的な .env.example:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=yourpassword
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（代表的なコード例）

以下は Python REPL やスクリプトから利用する際の最小使用例です。事前に必要な環境変数を設定し、DuckDB に接続できることを確認してください。

- DuckDB 接続と日次ETL実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は .env で上書き可能（デフォルト: data/kabusys.duckdb）
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのAIスコアリング（score_news）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数または api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", count)
```

- 市場レジーム判定（score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査DB 初期化
```python
from kabusys.data.audit import init_audit_db

# ":memory:" でインメモリ DB も可
conn = init_audit_db("data/monitoring.duckdb")
# または既存の接続に対してスキーマだけ作成する:
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn, transactional=True)
```

- 市場カレンダー更新ジョブの実行
```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("calendar saved:", saved)
```

注意:
- OpenAI 呼び出しはネットワーク・料金・API制限に依存します。APIキーは厳重に管理してください。
- J-Quants API はレート制御・トークン管理を内部で行います。JQUANTS_REFRESH_TOKEN を用意してください。

---

## よく使う API の説明（短め）

- kabusys.config.settings
  - 環境変数を取得するアクセサ（例: settings.jquants_refresh_token, settings.duckdb_path, settings.env）
  - .env 自動ロード機能あり（プロジェクトルート検出）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, id_token=None, ...)
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult 型で結果を返す（品質問題・エラー一覧を含む）

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token(refresh_token=None)

- kabusys.ai.news_nlp.score_news
  - raw_news / news_symbols を元に銘柄ごとAIスコアを ai_scores に保存

- kabusys.ai.regime_detector.score_regime
  - ETF 1321 の MA 乖離 + マクロニュースセンチメント から market_regime テーブルにレジームを書き込む

- kabusys.data.quality
  - run_all_checks(conn, target_date, reference_date) で品質チェック群を実行

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成（主要ファイルの役割）

src/kabusys/
- __init__.py — パッケージ初期化（公開モジュール定義）
- config.py — 環境変数 / 設定管理（.env 自動ロード・Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースのAIスコアリング（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
  - quality.py — データ品質チェック（QualityIssue）
  - calendar_management.py — マーケットカレンダー処理（営業日計算・更新ジョブ）
  - news_collector.py — RSS 取得・記事前処理・raw_news 保存
  - audit.py — 監査ログ（監査テーブル定義・初期化）
  - etl.py — ETLResult の再エクスポート
  - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility ファクター計算
  - feature_exploration.py — 将来リターン・IC・サマリー等
- ai, research, data はさらに細かいモジュールを含む（上記は代表）

その他:
- data/ (デフォルトDB保存先の例)
  - kabusys.duckdb（デフォルト）
  - monitoring.db（監視/監査用の sqlite / duckdb 等）

---

## 注意点 / ベストプラクティス

- .env に機密情報（APIキー）を置く場合は git 管理から除外してください（.gitignore に追加）。
- OpenAI / J-Quants の API キーには利用料金・レート制限があるため、本番実行前にローカルテスト・モックを推奨します。news_nlp/regime_detector 内の API 呼び出し関数はテストしやすいように差し替え可能です（ユニットテストでは patch してモック化できます）。
- DuckDB のバージョン差異により executemany の挙動が異なる点があるため、空パラメータの扱い等に注意しています（pipeline, news_nlp 参照）。
- ETL 実行時はログ出力（LOG_LEVEL）を適切に設定し、品質チェック結果を監視することを推奨します。

---

必要に応じて README に追加したい「実行スクリプト例」「CI / デプロイ手順」「スキーマ定義（DDL）」「テストの書き方」などがあれば教えてください。README をそれに合わせて拡張します。