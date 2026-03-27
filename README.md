# KabuSys

日本株向けの自動売買・データプラットフォームライブラリ。J-Quants からの市場データ取得（ETL）、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を内包する Python パッケージです。

- J-Quants API を用いたデータ取得（株価 / 財務 / 市場カレンダー）
- DuckDB を用いたデータ保存と ETL パイプライン
- RSS ニュース収集および OpenAI を使ったニュースセンチメント評価（ai モジュール）
- ETF の移動平均などとニュースセンチメントを合成した市場レジーム判定
- リサーチ向けファクター計算（モメンタム／バリュー／ボラティリティなど）
- データ品質チェック（欠損／重複／スパイク／日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用スキーマ初期化ユーティリティ

設計上のポイント:
- ルックアヘッドバイアス回避のため、関数は内部で datetime.today()/date.today() に依存しない（呼び出し側で target_date を渡す設計）。
- DuckDB に対する保存は冪等性（ON CONFLICT）を担保。
- 外部 API 呼び出しはリトライやレート制御、フェイルセーフ処理を備える。

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系関数、認証トークン管理、レート制御）
  - RSS ニュース収集（SSRF 防御、サイズ制限、正規化）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 市場カレンダー管理（営業日判定／next/prev/get_trading_days）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP スコアリング（score_news：OpenAI を用いた銘柄ごとのセンチメント）
  - 市場レジーム判定（score_regime：ETF MA とニュースセンチメントを合成）
- research/
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索・IC 計算・統計サマリー
- config.py
  - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml で探索）
  - 必須環境変数チェック、環境切替（development / paper_trading / live）やログレベル管理

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで `|` を使用しているため）
- システムに DuckDB のバイナリをインストール可能であること

推奨手順（開発用）

1. リポジトリをクローンしてソースルートへ移動
   - git clone ...  
   - cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール（例）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   あるいは requirements.txt がある場合:
   - pip install -r requirements.txt

4. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

環境変数の設定
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を置くと、kabusys.config が自動で読み込みます（優先度: OS 環境 > .env.local > .env）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で利用）。

必要な環境変数（代表例）
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY：OpenAI API キー（score_news / score_regime 呼び出し時に環境変数に設定しておくか、関数呼び出し時に api_key を渡す）
- KABU_API_PASSWORD：kabu ステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN：Slack 通知用トークン
- SLACK_CHANNEL_ID：通知先チャンネル ID
- DUCKDB_PATH：デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV：development / paper_trading / live
- LOG_LEVEL：DEBUG/INFO/WARNING/ERROR/CRITICAL

例 .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパーサについて
- `export KEY=val` 形式に対応
- シングル/ダブルクォートを考慮した値取り扱い（エスケープ処理あり）
- `#` を使ったコメント行や値後のコメントの扱いを実装済み

## 使い方（主要なユースケースの例）

※ 以下は簡易的なコード例です。適切な例外処理やログ設定は必要に応じて追加してください。

1) DuckDB 接続を作成して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())  # target_date を明示するとテストしやすい
print(result.to_dict())
```

2) ニュース NLP（銘柄ごとの AI スコア）を生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数に設定するか、第二引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

3) 市場レジーム（bull / neutral / bear）を判定する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
# conn を使って監査テーブルへ書き込み／クエリ可能
```

5) ファクター計算 / リサーチ用ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。API キーを環境変数に設定するか、api_key 引数で渡してください。
- テスト時は内部の _call_openai_api をモックして呼び出しを置換する設計になっています（unittest.mock.patch などで差し替え可能）。
- J-Quants へのリクエストはレート制限（120 req/min）とリトライを組み込んでいます。get_id_token() は JQUANTS_REFRESH_TOKEN を使用します。

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP スコアリング（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API client（fetch / save / auth）
    - pipeline.py              — ETL パイプライン（run_daily_etl 他）
    - etl.py                   — ETLResult 型再エクスポート
    - news_collector.py        — RSS ニュース収集
    - quality.py               — データ品質チェック
    - calendar_management.py   — 市場カレンダー管理
    - audit.py                 — 監査ログ（スキーマ初期化）
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py       — モメンタム／バリュー／ボラティリティ
    - feature_exploration.py   — 将来リターン，IC，統計サマリー 等

この README はコードベースに含まれる主要な機能と利用方法をまとめたものです。詳細な API 仕様や運用上の注意は各モジュールの docstring を参照してください（例: kabusys/data/jquants_client.py、kabusys/ai/news_nlp.py 等）。もし README に追記してほしい項目（例: デプロイ手順、CI/CD、より詳細なサンプル）や、特定機能のドキュメント化希望があれば教えてください。