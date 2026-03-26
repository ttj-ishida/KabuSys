# KabuSys

日本株向けの自動売買 / データプラットフォーム ライブラリ。  
ETL（J-Quants からのデータ取得）・ニュース収集・LLM ベースのニュースセンチメント評価・市場レジーム判定・リサーチ用ファクター計算・監査ログ管理などを含むモジュール群を提供します。

主な設計思想
- ルックアヘッドバイアス回避（内部で date.today() を使わない等）
- DuckDB をデータプラットフォームの中心に据えた設計
- API 呼び出しはリトライ・レート制御を備えフェイルセーフ
- 冪等性（ETL の ON CONFLICT / DELETE→INSERT 等）を重視

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local / OS 環境変数から設定を読み込み（自動ロード）。  
  - 必須環境変数チェック機能を提供。

- データ ETL（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存。
  - ページネーション対応、レートリミット管理、リトライ／トークン自動更新。
  - ETL の結果格納用 dataclass (ETLResult)。

- データ品質チェック
  - 欠損値、主キー重複、将来日付、価格スパイク、非営業日データなどを検出。

- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 制限、トラッキングパラメータ除去、ID 生成）と raw_news への保存（冪等）。

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを統合して LLM によりセンチメントスコアを算出し、ai_scores に保存（バッチ処理、JSON モード、リトライ）。
  - OpenAI 呼び出しは gpt-4o-mini を想定（設定可能）。

- 市場レジーム判定
  - ETF（1321）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime を算出・保存。

- リサーチ（factor / feature）
  - Momentum / Volatility / Value 等のファクター計算。
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z-score 正規化。

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（DuckDB）。

---

## セットアップ手順

前提
- Python 3.9+（typing の一部構文を使用）
- DuckDB がインストール可能であること

1. リポジトリをクローン（またはソースを配置）
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必須例:
     - pip install duckdb openai defusedxml
   - 実際のプロジェクトでは requirements.txt / pyproject.toml で管理してください。
4. パッケージを editable インストール（ローカル開発用）
   - pip install -e .

環境変数（例）
- 必須（Settings クラスで _require を呼ぶプロパティあり）:
  - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード（使用箇所による）
  - SLACK_BOT_TOKEN — Slack 通知用（使用する場合）
  - SLACK_CHANNEL_ID — Slack 通知対象チャネル ID
- 任意 / デフォルトを持つ:
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト "development"）
  - LOG_LEVEL — "DEBUG","INFO","WARNING","ERROR","CRITICAL"（デフォルト "INFO"）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB など（デフォルト data/monitoring.db）
  - OPENAI_API_KEY — OpenAI API キー（score_news・score_regime のデフォルト参照）

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先度: OS 環境 > .env.local > .env
- 自動読み込みを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

サンプル .env
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（コード例）

以下は基本的な Python 呼び出し例です。各関数は DuckDB の接続オブジェクト（duckdb.connect の戻り値）を受け取ります。

- DuckDB に接続して ETL を実行する
```
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（LLM を用いる）
```
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を None にすると OPENAI_API_KEY を参照
print("scored:", n_written)
```

- 市場レジーム判定
```
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB 初期化
```
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。監査テーブルが作成済み。
```

- リサーチ関数の呼び出し例
```
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{ "date": ..., "code": "...", "mom_1m":..., ... }, ...]
```

注意点
- OpenAI 呼び出しは外部 API のためネットワーク／レート制限／失敗を適切に扱ってください。デフォルトでは gpt-4o-mini を想定。
- テスト時には kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api をモックして API 呼び出しを差し替えることを推奨します（README にある通りテスト向けに差し替え可能）。

---

## 主要な API / モジュール一覧（抜粋）

- kabusys.config
  - settings: Settings インスタンス（環境変数読み込み / バリデーション）
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...) → ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult dataclass
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.news_collector
  - fetch_rss(...) / _normalize_url / preprocess_text 等
- kabusys.data.quality
  - run_all_checks(conn, ...)
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(path)
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research.*
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下の主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - audit.py
    - etl.py
    - ...（その他データ関連モジュール）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
  - ai/
  - etc.

各ファイルの役割（簡易）
- config.py: 環境変数読み込み・設定オブジェクト
- data/jquants_client.py: J-Quants API クライアント + DuckDB 保存用ユーティリティ
- data/pipeline.py: 日次 ETL パイプラインのエントリポイント
- data/news_collector.py: RSS 収集・前処理
- data/quality.py: データ品質チェック
- data/audit.py: 監査（signal/order/execution）スキーマ初期化
- ai/news_nlp.py: ニュースを LLM で銘柄別に集約スコア化
- ai/regime_detector.py: マクロセンチメント＋ETF MA 乖離で市場レジーム判定
- research/*: ファクター計算・リサーチ補助

---

## 運用／開発時の注意事項

- 自動環境読み込み:
  - .env / .env.local はプロジェクトルートに置く。テストや CI で自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しのテスト:
  - 内部で定義されている _call_openai_api を unittest.mock.patch で差し替えることでネットワーク呼び出しを回避できます（news_nlp と regime_detector は別々の実装を持ちます）。
- DuckDB executemany の注意:
  - DuckDB のバージョンによっては executemany に空リストが渡せないため、コード内で空チェックが行われています。開発時はこの挙動に注意してください。
- 時刻・タイムゾーン:
  - 監査ログ等の TIMESTAMP は UTC に統一して保存する設計（init_audit_schema で SET TimeZone='UTC' を実行）。
- KABUSYS_ENV 値:
  - 有効値: "development", "paper_trading", "live"（設定ミスは例外を発生させます）
- ログレベル:
  - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれかに設定してください。

---

質問や README に追加したい使用例（cron/airflow などの運用例、より詳しい .env.example、CI のテスト例など）があれば教えてください。必要に応じて README を拡張します。