# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL、ニュース収集・NLP、ファクター計算、マーケットカレンダー管理、監査ログなどのユーティリティを備え、DuckDB をデータレイヤとして利用します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- RSS ベースのニュース収集と LLM（OpenAI）を用いたニュースセンチメント評価
- 日次 ETL パイプライン（差分取得・保存・データ品質チェック）
- 研究用ファクター計算・特徴量解析ユーティリティ
- 市場レジーム判定（ETF + マクロニュース合成）
- 監査ログ/トレーサビリティ（シグナル→発注→約定の永続化）

設計方針として、バックテスト等でのルックアヘッドバイアス回避、RPC/外部API呼び出しのフォールバック・リトライロジック、DuckDB を用いた効率的な SQL 処理を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save の自動リトライ・レート制御・トークンリフレッシュ）
  - マーケットカレンダー管理（is_trading_day, next_trading_day, get_trading_days 等）
  - ニュース収集（RSS → raw_news 保存、安全対策（SSRF/サイズ）あり）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化 / DB 管理（init_audit_schema / init_audit_db）
- ai
  - ニュース NLP（score_news: OpenAI で銘柄別センチメント算出）
  - 市場レジーム判定（score_regime: ETF の MA とマクロニュース合成）
- research
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC 計算、統計サマリー
- 共通ユーティリティ
  - 設定管理（kabusys.config.Settings）
  - 統計ユーティリティ（zscore_normalize）

---

## 前提 / 必要環境

- Python 3.9+（typing などを広く利用しているため 3.9 以上を想定）
- 以下の主要依存パッケージ（実行する機能に応じて必要）
  - duckdb
  - openai (OpenAI の新しい SDK に対応しているコードを参照)
  - defusedxml
  - （標準ライブラリの urllib 等も使用）
- J-Quants API（データ取得）用のリフレッシュトークン
- OpenAI API キー（ニュース/NLP・レジーム判定で必須）
- kabuステーション等の発注API を使う場合は追加設定（本コードでは発注層は含まれていません）

（必要なパッケージはプロジェクト配下の requirements.txt / pyproject.toml で管理してください）

---

## 環境変数 / 設定

主要な環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（ETL の認証に使用）
- OPENAI_API_KEY (必須 for AI 機能)
  - OpenAI の API キー（score_news, score_regime などで使用）
- KABU_API_PASSWORD (必須 if kabu API を利用する場合)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須 if Slack 通知を行う場合)
- SLACK_CHANNEL_ID (必須 if Slack 通知を行う場合)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視関連）
- KABUSYS_ENV（development|paper_trading|live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

自動的な .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml の存在）を見て、自動的に `.env` と `.env.local` を読み込みます。
- 優先順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意:
- 一部関数（score_news, score_regime, jquants_client.get_id_token など）は API キーが見つからないと ValueError を投げます。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - もしくはプロジェクトの pyproject.toml / requirements.txt があれば:
     - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を作成します（`.env.example` を参考に）。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```
   - OS 環境に直接設定しても構いません。

5. データディレクトリ等を作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単なコード例）

以下は基本的な利用例です。実行は Python スクリプトやジョブマネージャから行ってください。

- DuckDB 接続を作成して ETL を実行する例:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントスコアを計算して ai_scores に書き込む:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# score_news は OPENAI_API_KEY を参照（引数で上書き可）
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(...)
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境から参照
```

- 監査ログ DB の初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

- 研究モジュールの利用例（モメンタム計算）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(...)
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト: [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

注意:
- OpenAI を呼ぶ関数は API キーが必要です。引数で api_key を渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- J-Quants からのデータ取得は `JQUANTS_REFRESH_TOKEN` を必要とします。

---

## 実行上の注意点 / 運用ノウハウ

- Look-ahead バイアス対策:
  - 多くの処理（news window 計算、prices の取得など）は内部で現在時刻を直接参照せず、target_date に基づいて処理します。バッチ処理やバックテストで target_date を明示してください。
- .env 自動ロード:
  - テスト環境で環境を汚したくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- エラーハンドリング:
  - J-Quants クライアントは 401 の際に自動でトークンを更新する等の仕組みが入っています。API 呼び出しは再試行とエクスポネンシャルバックオフを行います。
- DuckDB の executemany について:
  - 一部処理では DuckDB のバージョン差異に依存する挙動を回避するため、空の params を渡さない等の工夫がされています。

---

## ディレクトリ構成（主要ファイル・モジュール）

src/kabusys/
- __init__.py
- config.py
  - 環境変数 / 設定管理、.env の自動読み込み
- ai/
  - __init__.py
  - news_nlp.py           — ニュースセンチメント（score_news）
  - regime_detector.py    — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - etl.py                — ETL インターフェース再エクスポート
  - pipeline.py           — 日次 ETL パイプライン（run_daily_etl 等）
  - stats.py              — 統計ユーティリティ（zscore_normalize）
  - quality.py            — データ品質チェック
  - audit.py              — 監査ログテーブル定義・初期化
  - jquants_client.py     — J-Quants API クライアント（fetch/save）
  - news_collector.py     — RSS ニュース収集と保存
- research/
  - __init__.py
  - factor_research.py    — ファクター計算（momentum / value / volatility）
  - feature_exploration.py— 将来リターン、IC、統計サマリー 等
- research/ 以下は研究用ユーティリティ（バックテスト・分析向け）

---

## テスト / 開発メモ

- LLM / OpenAI 呼び出し部分はテスト容易性を考慮して、内部で API 呼び出し関数を切り替え可能に実装されています（unittest.mock で patch しやすい）。
- DuckDB を用いた関数は接続を引数に取るため、インメモリ DB (":memory:") を使った単体テストが容易です。
- 外部 API 呼び出し（J-Quants / RSS / OpenAI）はネットワーク依存のため、ユニットテストではモック推奨。

---

必要であれば、README にサンプル .env.example、install の具体的な requirements.txt、または各モジュールの API リファレンス（関数引数／戻り値／例外）を追記します。どの情報を優先して追加しますか？