# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（約定トレース）など、研究・運用に必要な機能群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は DuckDB をデータ層に用い、J-Quants API や RSS からデータを収集・永続化し、AI（OpenAI）によるニュースセンチメント評価や市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（signal → order → execution のトレース）などを提供する Python モジュール群です。

設計上のポイント:
- ルックアヘッドバイアス回避（target_date を明示し、内部で date.today() に依存しない実装）
- DuckDB による高速な SQL 集約・ウィンドウ集計
- OpenAI（gpt-4o-mini）を用いた JSON Mode 呼び出しと堅牢なリトライ/バリデーション
- J-Quants API に対するレート制御・リトライ・トークン自動リフレッシュ
- 冪等性（ON CONFLICT / DELETE→INSERT 等）を意識した保存処理

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
  - データ品質チェック（欠損・重複・スパイク・日付不整合の検出）
  - ニュース収集（RSS→raw_news、SSRF 対策、URL 正規化）
  - 監査ログ（signal_events / order_requests / executions テーブルの初期化・管理）
  - 汎用統計ユーティリティ（zscore_normalize など）
- ai
  - ニュース NLP（score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込み）
  - レジーム判定（score_regime: ETF 1321 の MA200 とマクロセンチメントを合成して market_regime に保存）
- research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns, IC, summary, rank）
- config
  - 環境変数 / .env 読み込みと Settings オブジェクト（自動 .env 読込、必須キーチェック）

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈に Union | を使用）
- DuckDB, OpenAI SDK 等の依存パッケージ

1. リポジトリをクローン / ダウンロード
2. 仮想環境を作成 & 有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - 追加でロギングやテスト用のパッケージを任意で導入

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くことで自動ロードされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（最低限）環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（注文機能を使う場合）

任意（機能により必須）環境変数:
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH 等（監視関連設定）
- LOG_LEVEL / KABUSYS_ENV（development / paper_trading / live）

例 `.env`（最小）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主な API と例）

以下は Python から直接呼び出す想定の例です。各関数は DuckDB 接続（duckdb.connect(...)）を引数に取ります。

- DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants からデータ取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が対象（内部で調整あり）
result = run_daily_etl(conn)
print(result.to_dict())
```

- 個別 ETL（価格データのみ）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
```

- ニュースのスコア付け（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（OpenAI 必須）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ (audit) スキーマ初期化 & 専用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions 等のテーブルが作成されます
```

- カレンダー管理ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env, settings.log_level)
```

注意点:
- OpenAI 呼び出しは JSON mode を使用し、レスポンス検証およびリトライロジックを行います。API キー未設定時は ValueError が発生します。
- ETL / 保存処理は可能な限り冪等になるよう実装されています（ON CONFLICT 等）。

---

## ディレクトリ構成

主要なファイル / モジュールのツリー（概要）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult 再エクスポート
    - calendar_management.py        — マーケットカレンダー管理
    - news_collector.py             — RSS ニュース収集
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログの DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum / value / volatility）
    - feature_exploration.py        — 将来リターン、IC、統計サマリー
  - research/... (他のヘルパーモジュール)
  - ai/... (上記)
  - その他: execution/ monitoring/strategy などが __all__ に想定されています

---

## 補足 / 運用メモ

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から行われ、優先順位は OS 環境 > .env.local > .env です。テスト等で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- DuckDB ファイルパスのデフォルトは `data/kabusys.duckdb`。運用時は永続ディレクトリを確保してください。
- J-Quants API にはレート制限（デフォルト 120 req/min）やトークンリフレッシュのロジックが組み込まれています。ID トークンは内部でキャッシュされ、必要に応じ自動更新されます。
- ニュース収集モジュールは SSRF 対策・XML 防御（defusedxml）・トラッキングパラメータ除去などを実装しています。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT 等）。

---

必要であれば、README に「実行スクリプト例（cron / systemd）」や「データベーススキーマ定義（DDL）」、より詳しい .env.example、テスト実行方法、CI 設定例などを追加できます。どの情報を優先的に追記しますか？