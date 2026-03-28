# KabuSys

日本株自動売買システムのライブラリ群（コアモジュール群）のリポジトリ用 README。  
この README はコードベース（src/kabusys 配下）を元に作成しています。

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォーム・リサーチ・AI・監査・ETL・監視・発注補助を提供するライブラリ群です。主に以下用途を想定しています。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー等）
- DuckDB を用いたデータ保存・品質チェック・ETL パイプライン
- ニュースの収集・NLP スコアリング（OpenAI を利用）
- 市場レジーム判定（MA とマクロニュースの合成）
- ファクター計算・特徴量探索・研究（Research 用ユーティリティ）
- 発注・監査用テーブル（監査ログ、発注トレース）
- Slack 等への通知や本番／ペーパーの環境分離に対応する設定管理

設計上の特徴：
- Look-ahead バイアス対策（target_date を明示し、内部で date.today() を不用意に参照しない）
- DuckDB を中心とした SQL + Python の処理
- 冪等性（ON CONFLICT / idempotent 保存）を重視
- OpenAI 呼び出しはリトライ・バリデーションを備えフェイルセーフに設計

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー（settings オブジェクト）
- データ取得 / ETL（kabusys.data.jquants_client, pipeline, etl）
  - J-Quants API クライアント（レートリミット・リトライ・トークンリフレッシュ）
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - 品質チェック（data.quality）
  - カレンダー管理（data.calendar_management）
- ニュース収集 / NLP（kabusys.data.news_collector, kabusys.ai.news_nlp）
  - RSS フィード取得（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント scoring（score_news）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA とマクロニュースセンチメントを合成（score_regime）
- リサーチ（kabusys.research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - z-score 正規化ユーティリティ（kabusys.data.stats.zscore_normalize）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブルを初期化・管理
  - init_audit_db / init_audit_schema を提供

---

## セットアップ手順

前提：Python 3.10+（型注釈に union | を使用）、pip が利用可能であること。

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそちらを利用してください。ここではコードで参照されている主要外部依存を記載しています。）

3. 環境変数 / .env の設定
   - プロジェクトルートに `.env` と `.env.local`（必要に応じて）を置けます。
   - 自動読み込みの仕様：
     - パッケージ内で .git または pyproject.toml を探索してプロジェクトルートを特定します。
     - 読み込み優先順位: OS 環境 > .env.local > .env
     - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（例）：
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - OPENAI_API_KEY=<your_openai_api_key>           # score_news / regime_detector 用
   - KABU_API_PASSWORD=<kabu_station_password>
   - SLACK_BOT_TOKEN=<slack_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO

   注意: Settings を経由して必須キーの存在チェックを行うため、欠けていると ValueError が発生します。

4. プロジェクトルートの確認
   - config._find_project_root が .git または pyproject.toml を基準に動作します。パッケージ配布後の挙動に注意してください。

---

## 使い方（主要 API の例）

以下は主要な機能の簡単な使用例です。実行前に環境変数を設定してください。

- settings（環境設定取得）

```python
from kabusys.config import settings

# 必須キーは .jquants_refresh_token などを settings オブジェクト経由で取得
print(settings.jquants_refresh_token)
print(settings.duckdb_path)   # Path オブジェクト
```

- DuckDB 接続例

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 以降 conn を各関数に渡して使用
```

- 日次 ETL 実行（run_daily_etl）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコア付け（score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を参照
print(f"書き込み件数: {n_written}")
```

- 市場レジーム判定（score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB 初期化（init_audit_db）

```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
# これで監査テーブルが作成されます
```

- リサーチ系のユーティリティ

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
# IC の例（mom_1m と fwd_1d の相関）
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
```

テスト時のヒント:
- OpenAI 呼び出しはモジュール内 private 関数をモック可能です。
  - news_nlp._call_openai_api や regime_detector._call_openai_api を unittest.mock.patch で差し替えます。

---

## ディレクトリ構成

主要ファイル / モジュールのツリー（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースの NLP スコアリング（score_news）
    - regime_detector.py     # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py # 市場カレンダー管理
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - etl.py                 # ETLResult の再エクスポート
    - jquants_client.py      # J-Quants API クライアント（fetch / save 等）
    - news_collector.py      # RSS からのニュース収集
    - quality.py             # データ品質チェック
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - audit.py               # 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     # Momentum / Value / Volatility 計算
    - feature_exploration.py # 将来リターン、IC、統計サマリー等

---

## 注意事項・運用上のポイント

- 環境変数の自動ロードは便利ですが、CI／テスト等で不要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- OpenAI API を利用する箇所（news_nlp, regime_detector）は外部 API 呼び出しのため、ネットワーク要件・コストに注意してください。API エラー時はフェイルセーフとしてスコアを 0 にする等の設計になっていますが、運用判断は必要です。
- J-Quants API 用のトークン管理は jquants_client が自動でリフレッシュ処理を実装しています。ID トークン取得・キャッシュを行うため、rate-limit やリトライの挙動に留意してください。
- DuckDB の executemany に対する空リスト制約（バージョン依存）に配慮した実装がされています。DuckDB のバージョンにより挙動が変わる点に注意してください。
- ニュース収集では SSRF / XML 攻撃対策（defusedxml、IP/ホストチェック、レスポンス上限等）が施されています。

---

## 開発・テスト

- 単体テストや CI では外部 API 呼び出しをモックしてください（OpenAI / J-Quants / HTTP）。
- news_nlp/regime_detector の OpenAI 呼び出しは内部で _call_openai_api を使っているため、この関数を patch することで容易にテスト可能です。
- .env のパースはシェル風のフォーマットに対応しています（export プレフィックス、クォート、行内コメント等）。

---

必要に応じて README に追記します。特定の使い方（例: ETL の cron 設定、Slack 通知連携、kabu-station との発注フロー）について詳述したい場合は用途を教えてください。