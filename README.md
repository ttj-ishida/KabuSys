# KabuSys

日本株向けの自動売買・データ基盤ライブラリ (KabuSys)。  
J-Quants / DuckDB を用いたデータ ETL、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ管理などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ基盤と自動売買に必要なユーティリティ群を提供する Python パッケージです。主なコンポーネントは次のとおりです。

- J-Quants API からの差分 ETL と DuckDB への保存
- RSS ベースのニュース収集と OpenAI を使ったニュースセンチメント分析
- マーケットレジーム（bull / neutral / bear）判定（ETF + LLM 合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ生成

設計上の方針として、バックテストやモデル開発におけるルックアヘッドバイアス回避、API 呼び出しの堅牢なリトライ、DuckDB を用いた効率的な集計・保存、外部依存の最小化（研究モジュールは pandas 等に依存しない）を重視しています。

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得と保存）
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）
- ニュース & NLP
  - RSS 取得（SSRF 対策・トラッキングパラメータ除去）
  - OpenAI を用いたニュースセンチメント（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
- 研究用
  - モメンタム / ボラティリティ / バリュー算出（research.factor_research）
  - 将来リターン / IC / 統計サマリ（research.feature_exploration）
  - 正規化ユーティリティ（data.stats.zscore_normalize）
- データ品質
  - 欠損 / スパイク / 重複 / 日付不整合チェック（data.quality）
- カレンダー
  - market_calendar の取得・判定、next/prev_trading_day 等（data.calendar_management）
- 監査ログ
  - 監査用スキーマ初期化（data.audit.init_audit_schema / init_audit_db）

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ外の小さな依存

（実際の依存はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## 環境変数 / .env

config.Settings で参照される主な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- OpenAI / NLP
  - OPENAI_API_KEY (ニュース分析 / レジーム判定時に使用)
- Slack（通知などを行う場合）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース / パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
- 監視閾値（任意）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- 実行環境
  - KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

自動で .env/.env.local をプロジェクトルートから読み込みます（プロジェクトルートは .git または pyproject.toml を起点に探索）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install -e .    （プロジェクトに pyproject.toml / setup.cfg がある場合）
   - または requirements.txt があれば pip install -r requirements.txt

4. .env を作成して必要な環境変数を設定
   - .env.example を参考に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等を設定してください

5. DuckDB ファイルのディレクトリ作成（必要なら）
   - mkdir -p data

---

## データベース初期化（監査ログ例）

監査ログ用の DuckDB を初期化する簡単な例:

```python
import duckdb
from kabusys.data import audit
from kabusys.config import settings

# ファイルを指定する場合
conn = audit.init_audit_db(settings.duckdb_path)
# または別 DB に初期化
# conn = audit.init_audit_db("data/audit.duckdb")
```

init_audit_db はスキーマ作成後の接続を返します（トランザクション内で安全に作成）。

---

## 使い方（代表的な呼び出し例）

- 日次 ETL（株価 / 財務 / カレンダーの差分取得・保存・品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI を使用）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"書込銘柄数: {n_written}")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究用ファクター / forward returns / IC

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
forward = calc_forward_returns(conn, target_date=date(2026, 3, 20))
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
```

- RSS の取得（ニュース収集の低レベル関数）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意: 上記はライブラリ層の呼び出し例です。運用環境では適切な例外ハンドリングやロギング、API キー管理を行ってください。

---

## 開発 / テスト

- 自動環境変数自動ロードが邪魔なテストでは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- OpenAI 呼び出し等外部 API はユニットテスト時にモックしてテストする設計になっています（モジュール内の _call_openai_api をパッチ等で差し替えられます）。
- DuckDB のインメモリ接続は `duckdb.connect(":memory:")` で可能です。

---

## ディレクトリ構成

主要なモジュールと役割を示します（省略ファイルあり、参照用）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数／設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py           : ニュースを OpenAI でスコアリングし ai_scores に書き込む
    - regime_detector.py    : ETF MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     : J-Quants API クライアント（fetch / save）
    - pipeline.py           : ETL パイプライン（run_daily_etl 等）
    - etl.py                : ETL インターフェース再エクスポート
    - news_collector.py     : RSS 収集・前処理
    - calendar_management.py: マーケットカレンダー管理（営業日判定等）
    - quality.py            : データ品質チェック
    - stats.py              : 統計ユーティリティ（zscore_normalize）
    - audit.py              : 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py    : モメンタム／バリュー／ボラティリティ計算
    - feature_exploration.py: 将来リターン / IC / 統計サマリ
  - （その他、strategy / execution / monitoring 等のサブパッケージが __all__ に想定されています）

---

## 運用上の注意

- OpenAI API や J-Quants API 等の呼び出しにはレート制限・コストが伴います。実行頻度やバッチサイズは運用に合わせて調整してください。
- run_daily_etl は各ステップでエラーを捕捉し継続する設計です。戻り値 ETLResult にエラーや品質問題の情報が含まれるため、呼び出し側で対応を行ってください。
- 監査ログは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。データ永続性とトレーサビリティを重視してください。
- DuckDB のバージョン差で動作が変わる SQL バインド挙動があるため、CI と本番で同じ DuckDB バージョンを揃えることを推奨します。

---

この README はコードベースの主要機能と使用方法の概要を示すものです。詳細な関数仕様や追加ユーティリティ、コマンドラインツールがある場合は個々のモジュールの docstring やプロジェクトのドキュメント（README 内リンクや doc/ ディレクトリ）を参照してください。