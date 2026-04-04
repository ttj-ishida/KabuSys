# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ

---

## プロジェクト概要

KabuSys は日本株の自動売買・データ基盤・リサーチ用ユーティリティを提供する Python パッケージです。  
主に以下を目的としています：

- J-Quants API からの株価・財務・カレンダー等データの ETL（差分取得・保存・品質チェック）
- ニュース収集・NLP による銘柄別センチメント算出（OpenAI 経由）
- 市場レジーム（bull/neutral/bear）判定
- ファクター計算・特徴量探索（リサーチ用途）
- 監査ログ（信号→発注→約定のトレーサビリティ）用スキーマ初期化
- ニュース収集時の SSRF 等の基本対策を実装

パッケージは DuckDB を内部 DB として利用し、OpenAI（gpt-4o-mini 等）をニュース NLP に使用します。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants API クライアント（ページネーション・レート制御・自動トークンリフレッシュ）
  - カレンダー管理・営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS 取得、前処理、冪等保存、SSRF 対策）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: ニュースを銘柄ごとにスコア化）
  - 市場レジーム判定（score_regime: ETF 1321 の MA200 乖離 + マクロニュースセンチメントを合成）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み（.env/.env.local の自動ロード）と Settings クラスによるアクセス

---

## セットアップ手順

推奨: Python 仮想環境を作成してからインストールしてください。

1. リポジトリをクローン / 移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   - 依存ライブラリ（代表例）
     - duckdb
     - openai
     - defusedxml
   - 開発中は editable install を推奨:
     ```
     pip install -e .
     pip install duckdb openai defusedxml
     ```
   - （必要に応じて）requirements.txt を用意している場合は:
     ```
     pip install -r requirements.txt
     ```

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（パッケージインポート時）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
     または Windows PowerShell / CMD の環境変数設定を使用してください。

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 必要な環境変数（主要なもの）

必須（未設定時は例外を投げるもの）
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。
- KABU_API_PASSWORD
  - kabuステーション API を利用する場合のパスワード

任意（デフォルトあり / 空文字可）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live、デフォルト development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO)

OpenAI 関連
- OPENAI_API_KEY
  - ai.score_news / ai.score_regime などは api_key 引数を受け取りますが、デフォルトでは環境変数 `OPENAI_API_KEY` を参照します。

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下は Python REPL やスクリプト内での利用例です。DuckDB 接続は `duckdb.connect()` を使って生成します。

- ETL（日次パイプライン）を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコア化（OpenAI API キーを env に設定している前提）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み件数:", n_written)
```

- 市場レジーム判定（1321 ETF の MA200 とマクロニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

- カレンダー操作
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- リサーチ用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの辞書リスト
```

- RSS を手動取得（ニュースコレクタ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
```

注意点:
- ai モジュールは OpenAI API を利用するため、API キーの設定および料金・利用量の管理が必要です。
- ETL / API 呼び出しではネットワークや API のレート制御・リトライを行いますが、ID トークン等の認証情報は適切に保護してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは `src/kabusys` 以下にモジュール群があります。主なファイルと役割を簡潔に示します：

- src/kabusys/
  - __init__.py
  - config.py
    - Settings: 環境変数の読み取り・検証、自動 .env ロード機構
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの NLP スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save / 認証）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— マーケットカレンダー管理
    - news_collector.py     — RSS 収集・前処理・保存
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログ（テーブル DDL / 初期化）
    - etl.py                — ETLResult の公開
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Value/Volatility 等
    - feature_exploration.py— 将来リターン・IC・統計サマリー
  - research/... (その他のリサーチユーティリティ)
  - (execution/, monitoring/, strategy/ 等の名前は __all__ に含まれるが、今回のコードベースでは data/ ai/ research が主要)

---

## 実運用・注意事項

- Look-ahead バイアス対策:
  - ai モジュールや ETL は内部で date を明示的に与える設計になっており、datetime.today()/date.today() を不用意に参照しないことを設計方針としています。バックテストでは対象日を明示して使用してください。
- 冪等性:
  - J-Quants データ保存やニュース保存、監査ログの初期化などは可能な限り冪等（ON CONFLICT / INSERT DO UPDATE）になるよう実装されています。
- OpenAI 呼び出し:
  - レスポンスのパース・エラー時にはフェイルセーフ（スコア 0.0 など）で継続する設計になっていますが、API 使用料・レート制限に注意してください。
- 自動 .env ロード:
  - import 時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動的に読み込みます。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 貢献・拡張

- 新しい ETL ソースやニュースソースの追加は `kabusys.data.jquants_client` と `kabusys.data.news_collector` の実装を参考に機能追加してください。
- モデル（OpenAI）呼び出し部分はモックしやすいように内部関数を分離しています。ユニットテストはそれらをパッチすることで容易に行えます。

---

必要であれば、README に具体的な .env.example、requirements.txt のテンプレート、またはよくあるトラブルシュート（例: DuckDB ファイルパーミッション、OpenAI エラーへの対処）を追記できます。どの情報を優先して追記しますか？