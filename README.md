# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。本リポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLPスコアリング、リサーチ用ファクター計算、監査ログ（オーダー追跡）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を備えた Python ライブラリです。

- J-Quants API 経由でマーケットデータ（株価・財務・カレンダー）を差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と記事前処理／銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- マーケットレジーム判定（ETF とマクロセンチメントを合成）
- 研究用のファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー、将来リターン、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注から約定までをトレースする監査ログ（DuckDB スキーマ／初期化ユーティリティ）
- 環境変数 / .env の自動読み込みと設定管理

設計上の共通点として、バックテスト等でのルックアヘッドバイアスを避けるため、日付取得や DB クエリは「対象日」を明示して実行する方針が取られています。

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（認証・取得・保存・レート制御・リトライ）
  - カレンダー管理（営業日判定 / next/prev / calendar_update_job）
  - ニュース収集（RSS -> raw_news、SSRF対策・トラッキング除去）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化など）
- ai
  - news_nlp.score_news: 銘柄別ニュースを LLM でスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）200日 MA 乖離とマクロニュースセンチメントを合成して market_regime を更新
- research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理: kabusys.config.Settings により環境変数をラップ、.env 自動読み込み（プロジェクトルート基準）

---

## 動作環境と依存

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

（パッケージ化されている場合は requirements.txt / pyproject.toml を参照してください。手動インストール例は下記）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## 環境設定 (.env / 環境変数)

プロジェクトはルートにある `.env` / `.env.local`（存在する場合）を自動で読み込みます（CWD ではなくパッケージの場所を基準にプロジェクトルートを自動探索）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（必須）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注等で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

任意（デフォルト値あり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

サンプル .env（例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. Python 3.10+ を用意して仮想環境を作る
2. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml
3. .env をプロジェクトルートに作成し必須変数を設定
4. データストア（DuckDB）ファイルを用意（初回は ETL 実行などで自動生成されます）
5. （オプション）監査ログ専用 DB を初期化

---

## 使い方（API 例）

以下は主要なユースケースの最小例です。実運用ではログ設定・例外処理を行ってください。

- DuckDB 接続の取得例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（市場カレンダー・株価・財務・品質チェックを一括実行）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は duckdb connection
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP によるスコア計算（ai_scores テーブルへ書き込み）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# APIキーを明示したい場合は api_key="sk-..." を渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- マーケットレジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

res = score_regime(conn, target_date=date(2026, 3, 20))
print("score_regime result:", res)
```

- 監査ログ DB 初期化（監査専用ファイルを作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- 市場カレンダー更新ジョブ
```python
from datetime import date
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn, lookahead_days=90)
print(f"保存レコード数: {saved}")
```

---

## ディレクトリ構成

主なファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    : 環境変数/.env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                : 銘柄別ニュースセンチメント計算（score_news）
    - regime_detector.py         : マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          : J-Quants API クライアント（取得・保存）
    - pipeline.py                : ETL パイプライン（run_daily_etl 等）
    - etl.py                     : ETL インターフェース（ETLResult 再エクスポート）
    - calendar_management.py     : 市場カレンダー管理（is_trading_day 等）
    - news_collector.py          : RSS 収集・前処理
    - quality.py                 : データ品質チェック
    - audit.py                   : 監査ログスキーマ初期化 / init_audit_db
    - stats.py                   : 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py         : ファクター計算（momentum/value/volatility）
    - feature_exploration.py     : 将来リターン・IC・統計サマリー等
  - ai、research、data のほか strategy / execution / monitoring などのパッケージが想定されます（README の範囲外のモジュールも連携可能）。

---

## 注意事項・設計上の留意点

- 日付・時間:
  - 多くの処理はルックアヘッドバイアスを避けるため、内部で date.today() を直接参照せず「対象日」を明示して実行する設計です。バックテスト用途ではこの取り扱いを遵守してください。
- OpenAI 呼び出し:
  - LLM 呼び出しはリトライやフォールバックを備えていますが API コストやレート制限を考慮してください。テスト時は _call_openai_api をモックすることを推奨します。
- J-Quants:
  - get_id_token / fetch_* 系は認証やページネーション、リトライを内包しています。API レート制御（120 req/min）を実装していますが、実行環境の負荷に注意してください。
- セキュリティ:
  - news_collector では SSRF 対策や XML インジェクション対策（defusedxml）を導入しています。外部 URL 取り扱いには注意してください。
- DuckDB の executemany の挙動:
  - 一部コードは DuckDB のバージョン依存の挙動（executemany の空リスト不可など）に配慮しています。DuckDB のバージョン差には注意してください。

---

## 貢献・開発のヒント

- テスト:
  - OpenAI / ネットワーク呼び出し部分はユニットテストでモックしてテストを作成してください（例: unittest.mock.patch）。
- ロギング:
  - 各モジュールは logging.getLogger(__name__) を使用しています。運用では適切なログハンドラとレベルを設定してください。
- 拡張:
  - strategy / execution / monitoring 層は本 README のコードベース外に想定される実装箇所です。発注フローやポジション管理は監査ログスキーマに基づいて実装してください。

---

必要であれば README にサンプルの .env.example、requirements.txt、あるいはよく使う運用スクリプト（cron / systemd で ETL を定期実行する例）を追加します。追加したい項目があれば教えてください。