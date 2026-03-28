# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリセットです。J-Quants や RSS を取り込み、DuckDB 上で ETL／データ品質チェック／特徴量計算を行い、LLM を使ったニュースセンチメント・市場レジーム判定や発注監査ログをサポートします。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を提供します。

- J-Quants API からの株価・財務・上場情報・マーケットカレンダー取得（レート制御・リトライ・トークン自動更新対応）
- RSS ニュース収集・正規化・保存（SSRF 対策・トラッキング除去・重複防止）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別）およびマクロセンチメント合成による市場レジーム判定
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化等）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）向けのスキーマ初期化・DB ユーティリティ
- マーケットカレンダー管理（営業日判定、next/prev_trading_day、夜間バッチ更新）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API 接続、取得・保存関数（raw_prices, raw_financials, market_calendar, stocks 等）
  - news_collector: RSS 取得、記事正規化、raw_news への保存
  - pipeline: 日次 ETL (run_daily_etl)、個別 ETL ジョブ
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査ログ（signal_events, order_requests, executions）スキーマ初期化 / DB 初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースをまとめて LLM に送り銘柄別スコアを ai_scores へ保存
  - regime_detector.score_regime: 1321 の MA とマクロニュースの LLM センチメントを合成して market_regime へ保存
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config: 環境変数自動読み込み（.env/.env.local）と Settings API

---

## 前提条件

- Python 3.9+
- 依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （お使いの環境に合わせて urllib, json, 標準ライブラリのみで動作する部分もあります）

インストールする具体的なバージョンはプロジェクト側の pyproject.toml / requirements を参照してください。

---

## インストール（ローカルで利用する場合の例）

1. リポジトリをクローンし、パッケージをインストール
   ```
   git clone <repo>
   cd <repo>
   pip install -e .
   ```
2. 必要な追加パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

---

## 環境変数と設定

config モジュールはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、次の順で .env を自動読み込みします:

OS 環境変数 > .env.local > .env

自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

必須環境変数（少なくとも本機能を動かす際に設定が必要）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN: Slack 通知を使う場合
- SLACK_CHANNEL_ID: Slack チャンネル
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合）

例 .env（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

Settings API の使い方例:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

---

## データベース初期化

監査ログ用 DuckDB を初期化するユーティリティがあります。

例: 監査 DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

既存接続にスキーマのみ適用する場合:
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 使い方（代表的な呼び出し例）

以下は簡単な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- 日次 ETL を実行する（市場カレンダー更新 → 株価・財務取得 → 品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {n_written}")
```

- 市場レジーム判定を実行
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

- RSS を取得して raw_news に保存するフローは news_collector モジュールを参照してください（RSS のフェッチは SSFR 対策・サイズチェック付き）。

---

## 注意点・設計上の方針

- ルックアヘッドバイアス防止: 多くの関数は datetime.today() / date.today() を内部で参照しない設計です（target_date を明示して使います）。
- LLM 呼び出しはリトライとフェイルセーフ扱い（API 失敗時のフォールバック）を備えています。OpenAI 呼び出しは api_key を引数で明示的に渡すか、環境変数 OPENAI_API_KEY を利用してください。
- J-Quants API はレート制御（120 req/min）とトークン自動更新を実装しています。
- DuckDB に対する保存は基本的に冪等（ON CONFLICT DO UPDATE）で行われます。
- RSS の取得は SSRF、gzip bomb、XML bomb 対策済み（defusedxml、ホストチェック、サイズ制限など）。
- DuckDB の executemany に対する互換性（空リスト不可）を考慮した実装になっています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / .env 自動読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュースセンチメント解析（LLM）
    - regime_detector.py             -- マクロ + MA 合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（取得・保存）
    - pipeline.py                    -- ETL パイプライン（run_daily_etl など）
    - etl.py                         -- ETL インターフェース再エクスポート
    - news_collector.py              -- RSS 収集・正規化
    - calendar_management.py         -- 市場カレンダ管理、営業日判定、calendar_update_job
    - quality.py                     -- データ品質チェック
    - stats.py                       -- zscore_normalize 等の統計ユーティリティ
    - audit.py                       -- 監査ログ用スキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py             -- momentum/value/volatility ファクター計算
    - feature_exploration.py         -- forward returns, IC, summary, rank

---

## 開発・テスト関連

- config の自動環境読み込みはテスト時に邪魔になることがあるため、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- OpenAI / J-Quants など外部 API 呼び出しはユニットテストでモック（patch）することを前提に実装されています（各モジュール内で _call_openai_api などを差し替え可能）。

---

## 参考・補足

- 詳細な仕様（DataPlatform.md, StrategyModel.md 等）に基づいて各モジュールは実装されています。実運用の前に .env 設定、DuckDB スキーマ整備、API キー、kabu ステーションの設定（発注）を必ず確認してください。
- 本 README では主要な使い方と構成をまとめています。個々の関数の詳細な引数仕様や副作用は各モジュールの docstring を参照してください。

---

問題や追加してほしいサンプル（例: サンプル ETL スクリプト、Docker 化、CI 設定）などがあれば教えてください。必要に応じて README を拡張します。