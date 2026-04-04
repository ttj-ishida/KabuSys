# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。本リポジトリはデータ収集（J-Quants）、品質チェック、ETL、ニュースの NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどの機能をモジュール化して提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するためのライブラリ群です。主な目的は以下の通りです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への差分保存（ETL）
- ニュース収集（RSS）と OpenAI を用いた銘柄別センチメント評価（AI スコア）
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック
- 監査ログ（signal → order → execution のトレースを担保する監査 DB スキーマ）
- 実行監視／設定管理

設計上の重要点：
- ルックアヘッドバイアスを避ける（date / datetime を直接参照しない実装方針）
- DuckDB を中心としたローカルデータストア
- OpenAI（gpt-4o-mini）による JSON モードでの安全なレスポンス期待
- 冪等性（ON CONFLICT や UUID を使った idempotent な設計）
- ネットワーク・API 呼び出しはリトライやレート制御を備える

---

## 機能一覧

- 環境変数/設定管理（kabusys.config）
  - 自動 .env 読み込み（プロジェクトルート基準）、必要変数の検査
- データ ETL（kabusys.data.pipeline, jquants_client）
  - 日次 ETL（株価 / 財務 / 市場カレンダー取得、差分保存）
  - J-Quants API クライアント（ページネーション、トークンリフレッシュ、レート制御）
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / next/prev_trading_day / calendar 更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、安全対策（SSRF/リダイレクト検査）、前処理、冪等保存
- AI / NLP（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを算出して ai_scores に格納
  - regime_detector.score_regime: ETF の MA とマクロニュースで市場レジーム判定
- 研究用モジュール（kabusys.research）
  - calc_momentum, calc_value, calc_volatility（ファクター群）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索・評価）
- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブルの初期化ユーティリティ

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型ヒントに union | を使用）
- duckdb, openai, defusedxml 等の依存が必要

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (PowerShell)
   ```

3. 必要パッケージのインストール
   ※プロジェクトに pyproject.toml / setup.cfg がある場合は `pip install -e .` を使えます。
   最低限の例:
   ```
   pip install duckdb openai defusedxml
   ```
   他に標準ライブラリでカバーしているが、環境によっては追加パッケージが必要になる場合があります。

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（読み込みはプロジェクトルートの検出に依存）。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必須となる主な環境変数（kabusys.config.Settings）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
- (任意) KABU_API_BASE_URL
- (任意) LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- (任意) DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- (任意) SQLITE_PATH（監視用 DB）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易サンプル）

以下の例はライブラリの主な API の呼び出し方を示します。実運用ではロギングや例外処理、設定などを適切に追加してください。

1. DuckDB 接続を作って ETL を実行する（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュースの AI スコアを付与（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数に設定済みであること
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

3. 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数 OPENAI_API_KEY
```

4. 研究用ファクター計算（例: momentum）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records), "銘柄計算完了")
```

5. 監査 DB スキーマの初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
# これで signal_events / order_requests / executions テーブルが作成されます
```

注意点:
- OpenAI を呼ぶ関数（news_nlp, regime_detector）は環境変数 OPENAI_API_KEY を参照します。テストでは API 呼び出し関数を mock できます（ファイル内で _call_openai_api が分離されているため差し替えが容易です）。
- J-Quants の API トークンは settings.jquants_refresh_token から取得されます。get_id_token / fetch_* を呼ぶ際に内部でリフレッシュが行われます。

---

## よく使う API の場所（要約）

- 設定: kabusys.config.settings
- ETL: kabusys.data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- J-Quants クライアント: kabusys.data.jquants_client (fetch_*/save_*)
- ニュース収集: kabusys.data.news_collector.fetch_rss / 前処理関数
- ニュース NLP: kabusys.ai.news_nlp.score_news
- レジーム判定: kabusys.ai.regime_detector.score_regime
- データ品質チェック: kabusys.data.quality.run_all_checks
- ファクター計算: kabusys.research.factor_research (calc_momentum, calc_value, calc_volatility)
- 監査ログ初期化: kabusys.data.audit.init_audit_db

---

## ディレクトリ構成

リポジトリの主要なファイル/モジュール構成（src 配下）:

- src/kabusys/
  - __init__.py  (パッケージ初期化、__version__)
  - config.py  (環境変数・設定管理、.env 自動読み込み)
  - ai/
    - __init__.py
    - news_nlp.py  (ニュースのセンチメント付与 / score_news)
    - regime_detector.py  (市場レジーム判定 / score_regime)
  - data/
    - __init__.py
    - jquants_client.py  (J-Quants API クライアント / save_* / fetch_*)
    - pipeline.py  (ETL パイプライン、run_daily_etl 他)
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py  (RSS 収集、安全対策、前処理)
    - quality.py  (データ品質チェック)
    - stats.py  (zscore_normalize 等)
    - calendar_management.py  (市場カレンダー管理 / calendar_update_job)
    - audit.py  (監査ログスキーマ / init_audit_schema / init_audit_db)
  - research/
    - __init__.py
    - factor_research.py  (モメンタム / ボラティリティ / バリュー)
    - feature_exploration.py  (将来リターン / IC / 統計サマリー)

---

## 運用上の注意 / ベストプラクティス

- 環境変数や API キーは安全に管理する（.env を適切な権限で管理、CI/CD ではシークレット管理を使用）。
- OpenAI の呼び出しは発生コストがあるため、開発時はモックで代替することを推奨します（モジュール内の _call_openai_api を patch することで容易にテスト可能）。
- DuckDB のファイルパスは設定（DUCKDB_PATH）で制御します。バックアップや排他管理に注意してください。
- ETL は idempotent に設計されていますが、外部要因（API 変更・スキーマ変更）で問題が発生した場合は logs を確認の上リカバリしてください。
- run_daily_etl は内部で calendar の先読み等を行い、target_date の調整（営業日に合せる）を行います。バックテスト用途で使う際は look-ahead に注意してください（データの入手タイミングを適切に扱うこと）。

---

問題や機能追加、テストケースの整備については Issues を立ててください。README の他に詳細な設計ドキュメント（DataPlatform.md / StrategyModel.md 等）がある想定です。必要であればそれらの抜粋や使い方サンプルを追加で作成します。