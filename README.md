# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォームのコアライブラリです。  
J-Quants からの市場データ取得（ETL）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどの機能を提供します。

## 主な目的
- 日次データ ETL（株価・財務・市場カレンダー）
- ニュース収集と LLM による銘柄レベルのセンチメントスコア作成
- 市場レジーム（bull/neutral/bear）判定の自動化
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- データ品質チェックと監査ログ（発注／約定のトレーサビリティ）
- DuckDB を用いたローカル DB 保存（冪等保存・トランザクション管理）

---

## 機能一覧（抜粋）
- 環境設定管理（.env 自動ロード・保護）
- J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース収集（RSS -> raw_news、SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI を利用し銘柄ごとの ai_score を生成：score_news）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM 結果を合成：score_regime）
- 研究ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- カレンダー管理（営業日判定・次/前営業日取得・カレンダー更新ジョブ）

---

## 前提 / 必要条件
- Python 3.10+（ファイル内での型記法（|）を使用）
- 外部サービス:
  - J-Quants API（データ取得）
  - OpenAI（news_nlp / regime_detector）
  - kabuステーション API（発注・口座連携、設定参照のみの箇所あり）
  - Slack（通知用トークンを環境変数で参照する実装あり）
- 主な Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリの urllib 等を広く使用）
- ローカル DB ファイル（DuckDB、SQLite）への書き込み権限

---

## セットアップ手順（開発用）
1. リポジトリをクローン／チェックアウト（またはパッケージを配置）
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール（プロジェクトに requirements.txt や pyproject.toml がある想定）
   - pip install -e .           # ソース配布でインストール可能な場合
   - または個別に: pip install duckdb openai defusedxml
4. 環境変数を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config.py の自動ロード）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例：.env（最低限必要なキー）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL_ID=your_slack_channel_id

# オプション
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABU_API_BASE_URL=http://localhost:18080/kabusapi
```

---

## 使い方（基本例）

以下はライブラリの主要な利用例です。実際の運用スクリプトは用途に合わせて作成してください。

- DuckDB に接続して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアを作成する（OpenAI API キーは環境変数 OPENAI_API_KEY か引数で指定）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数を返す
print("ai_scores written:", written)
```

- 市場レジームスコアを計算して保存する:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # 1 を返すと成功
```

- 監査ログ DB を初期化する:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 返された conn で以降監査用テーブルにアクセスできます
```

- カレンダー関連ユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## 環境変数一覧（主要）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI features) — OpenAI API キー
- KABU_API_PASSWORD (必須 if kabu API を使用) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (任意) — Slack 通知設定
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視など用途）
- KABUSYS_ENV (任意) — "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL (任意) — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

注意: config.Settings は自動的にプロジェクトルートの .env / .env.local を読み込みます。自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## テスト／開発時のポイント
- OpenAI API コールは内部でリトライ・フォールバック処理を行います。テストでは各モジュールの _call_openai_api をモックして外部呼び出しを回避できます（例: unittest.mock.patch）。
- J-Quants クライアントは内部で固定間隔レートリミッタとリトライを実装しています。get_id_token は自動更新しますが、テストでは settings.jquants_refresh_token を差し替えるか _request をモックしてください。
- DuckDB executemany の制約などに注意（空リストバインドの扱いなど、コメント参照）。
- ルックアヘッドバイアスを避ける設計（target_date を明示的に渡し、date.today()/datetime.today() を直接参照しない箇所が多い）なので、バックテストや再現性のある実行に適しています。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動ロード、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - RSS 由来 raw_news を集約して OpenAI に渡し `ai_scores` を書き込む機能（score_news）
    - regime_detector.py
      - ETF(1321) の MA200 とマクロ記事の LLM 評価を組み合わせて market_regime を判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API 呼び出し、取得 & DuckDB へ冪等保存（save_*）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
      - ETLResult データクラス
    - etl.py
      - ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py
      - RSS 取得・正規化・raw_news 保存（SSRF 対策・サイズ制限など）
    - calendar_management.py
      - market_calendar 管理、営業日判定、calendar_update_job
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py
      - 監査ログスキーマ定義・初期化（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - research パッケージは research / factor 計算・解析機能を提供

---

## 運用上の注意
- 本ライブラリは「外部 API（証券会社への発注等）」と連携する機能を含むが、研究／開発と本番（ライブトレード）を混同しないよう環境変数で env を分けてください（KABUSYS_ENV）。
- ライブ運用時は監査ログ（audit テーブル）を必ず構築し、order_request_id を冪等キーとして重送対策を行ってください。
- OpenAI・J-Quants の API キーは適切に管理し、コミットしないようにしてください。

---

## 参考（よく使う API）
- ETL 実行: kabusys.data.pipeline.run_daily_etl
- ニューススコア: kabusys.ai.news_nlp.score_news
- レジーム判定: kabusys.ai.regime_detector.score_regime
- 監査初期化: kabusys.data.audit.init_audit_db / init_audit_schema
- カレンダー操作: kabusys.data.calendar_management.{is_trading_day,next_trading_day,prev_trading_day,get_trading_days}
- ファクター計算: kabusys.research.{calc_momentum, calc_value, calc_volatility}

---

必要であれば、README をプロジェクトの実行例（cron / Airflow / Docker などのデプロイ手順）や CI 設定、詳細な .env.example、SQL スキーマ（DDL）抜粋などで拡張できます。どの部分を詳しく書くか指定してください。