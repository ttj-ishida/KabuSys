# KabuSys

日本株向け自動売買・データ基盤ライブラリ (バージョン 0.1.0)

概要:
KabuSys は日本株のデータ取得・品質管理・特徴量計算・ニュースセンチメント解析・市場レジーム判定・監査ログ等をまとめて提供するライブラリです。J-Quants API を用いた ETL、DuckDB によるデータ保存、OpenAI を用いたニュース NLP（gpt-4o-mini想定）などを含み、研究（research）と運用（execution/monitoring）を分離して実装しています。

主な目的:
- データ取得と品質管理（J-Quants）
- ニュース収集と LLM による銘柄センチメント算出
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- ETL のバッチ実行支援

バージョン:
- __version__: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env/.env.local をプロジェクトルートから自動読込（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト経由で設定値を取得

- データ取得 / ETL
  - J-Quants API クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar 等）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データ品質チェック
  - 欠損・重複・日付不整合・スパイク検出
  - run_all_checks によりまとめて実行

- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間更新

- ニュース収集・NLP
  - RSS 収集・前処理（SSRF対策、トラッキングパラメータ除去、サイズ上限等）
  - OpenAI を用いた銘柄ごとのセンチメントスコア算出（score_news）
  - マクロニュースを使った市場レジーム判定（score_regime）

- 研究（Research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - z-score 正規化ユーティリティ

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルの DDL と初期化関数
  - init_audit_schema / init_audit_db による初期化

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | 演算子、型ヒントに基づく）
- DuckDB、openai、defusedxml 等のパッケージが必要

1) 仮想環境作成（推奨）
- python -m venv .venv
- source .venv/bin/activate (Linux/macOS)
- .venv\Scripts\activate (Windows)

2) 必要パッケージをインストール
- 例（pip）:
  - pip install duckdb openai defusedxml

（プロジェクトに requirements.txt がある場合はそれを使用してください）

3) 環境変数の設定
- プロジェクトルートに .env を作成（自動ロードされます）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携などで使用）
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack チャンネル ID
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
- 任意:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- 自動読み込みを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定

注意: config.Settings は自動的に .env / .env.local をロードします（プロジェクトルートの検出は .git または pyproject.toml に依存）。.env.local は .env の上書き（優先）として扱われます。

---

## 使い方（基本例）

以下は代表的な利用例です。実行スクリプトやジョブからインポートして利用します。

- DuckDB 接続を用意する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.audit import init_audit_db

# DuckDB ファイルへの接続
conn = duckdb.connect("data/kabusys.duckdb")

# ETL を今日分で実行（settings.jquants_refresh_token が必要）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

# 監査用 DB 初期化（別ファイル推奨）
audit_conn = init_audit_db("data/audit.duckdb")
```

- ニュースセンチメントを算出（OpenAI API が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written} codes")
```

- 市場レジーム判定（ETF 1321、OpenAI API が必要）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用にファクター計算・IC 計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- 監査テーブル初期化（例）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# この conn により signal_events / order_requests / executions が作成されます
```

注意点:
- OpenAI 呼び出し部は API エラー時にフォールバックやリトライ実装がありますが、API キーが未設定だと ValueError を送出します。
- run_daily_etl 等は内部で date.today() を利用する箇所がありますが、各スコープではルックアヘッドバイアスを避ける設計が施されています。テストやバックテスト時は target_date を明示的に与えてください。

---

## ディレクトリ構成

主要ファイルとモジュール（抜粋）:
- src/kabusys/
  - __init__.py
  - config.py             -- 環境設定・.env ロード
  - ai/
    - __init__.py
    - news_nlp.py         -- ニュースセンチメント解析（score_news）
    - regime_detector.py  -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   -- J-Quants API クライアント & DuckDB 保存
    - pipeline.py         -- ETL パイプライン（run_daily_etl 等）
    - etl.py              -- ETLResult の再エクスポート
    - news_collector.py   -- RSS 収集、前処理
    - calendar_management.py -- 市場カレンダー管理
    - quality.py          -- 品質チェック
    - stats.py            -- 汎用統計（zscore_normalize）
    - audit.py            -- 監査ログ DDL と初期化
  - research/
    - __init__.py
    - factor_research.py  -- ファクター計算 (momentum/value/volatility)
    - feature_exploration.py -- 将来リターン / IC / summary / rank
  - ai/、research/、data/ の他、strategy/ execution/ monitoring などをパッケージ公開（一部実装は別途）
- pyproject.toml (想定)
- .env.example (想定)

（リポジトリ全体は src 配下でパッケージ化されています）

---

## 注意事項・運用上の留意点

- 機密情報（API トークン等）は .env に保存し、ソース管理には含めないでください。
- OpenAI の呼び出しは API コストとレイテンシが発生します。バッチや throttling を考慮して実行してください。
- J-Quants API にはレート制限があります（モジュール内で固定間隔スロットリング実装あり）。並列大量リクエストを行う場合は注意してください。
- DuckDB のバージョン差異で一部の executemany / 型バインド挙動が異なることがあるため、テスト環境での確認を推奨します。
- 監査ログは削除しない設計のため、ディスク使用量に留意してください。

---

もし README に追加したい項目（例: 開発フロー、CI テスト方法、詳細な環境変数テンプレート、実運用での推奨設定等）があれば教えてください。必要に応じてサンプル .env.example も作成します。