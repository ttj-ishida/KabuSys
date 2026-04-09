# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ ETL、データ品質チェック、ニュースセンチメント（LLM）スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ等のユーティリティ群を提供します。

主に DuckDB を内部データストアとして利用し、J-Quants や RSS、OpenAI（gpt-4o-mini）など外部サービスと連携する設計です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数と .env 自動読み込み
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量計算・ニュースセンチメント分析・市場レジーム判定・監査ログを一貫して行うためのライブラリ群です。  
設計上の特徴：
- DuckDB を用いたローカルデータベース中心の処理（ETL / 保存は冪等）
- J-Quants API からの差分取得・ページネーション・レートリミット・トークン自動更新対応
- RSS ニュース収集と OpenAI を用いた銘柄ごとのニュースセンチメント（JSON Mode）処理
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを合成）
- 研究用ファクター計算・統計ユーティリティ（外部ライブラリに依存しない実装）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）

---

## 機能一覧

主な機能（モジュール単位）

- kabusys.config
  - 環境変数読み込み (.env, .env.local 自動読み込み)
  - 各種設定プロパティ（J-Quants トークン、DBパス、環境モードなど）

- kabusys.data
  - jquants_client：J-Quants API クライアント（取得・保存・トークン管理・レート制御）
  - pipeline：日次 ETL パイプライン（run_daily_etl など）
  - quality：データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector：RSS 取得と raw_news 保存（SSRF 対策・トラッキング除去）
  - calendar_management：JPX カレンダー管理・営業日ロジック
  - audit：監査ログスキーマの初期化（init_audit_db / init_audit_schema）
  - stats：汎用統計ユーティリティ（zscore_normalize）

- kabusys.ai
  - news_nlp.score_news：ニュースを集約して LLM に投げ、銘柄別 ai_scores を更新
  - regime_detector.score_regime：ETF MA 乖離 + マクロニュース LLM を合成し market_regime を更新

- kabusys.research
  - factor_research：momentum / value / volatility 等のファクター計算
  - feature_exploration：将来リターン計算、IC、統計サマリー等

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子などを利用）
- DuckDB を利用できる環境

推奨インストール手順（開発環境想定）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -U pip
   - 必要な依存（例）:
     - duckdb
     - openai
     - defusedxml
     - さらにプロジェクトによっては urllib3 等が必要
   - 開発用に setup.py / pyproject.toml があれば:
     - pip install -e .

4. データ格納ディレクトリを作る（任意）
   - mkdir -p data

注意: 具体的な requirements ファイルや pyproject.toml は本 README に含まれません。実際のパッケージ定義を参照してください。

---

## 環境変数

主要な環境変数（.env に記載して利用）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。

- OPENAI_API_KEY  
  OpenAI を利用する AI 機能（score_news / score_regime）で使用。

- KABU_API_PASSWORD  
  kabuステーション等の API パスワード（使用する場合）

- KABUSYS_ENV (任意)  
  development | paper_trading | live（デフォルト: development）

- LOG_LEVEL (任意)  
  DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

- DUCKDB_PATH (任意)  
  デフォルト DB パス: data/kabusys.duckdb

- SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH など  
  監視・ペーパートレード周りの設定

自動読み込み:
- パッケージ import 時、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を検索し、
  .env（優先度低）→ .env.local（優先度高）を読み込みます。
- 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 (.env)
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-....

---

## 使い方（主要 API の例）

以下は Python REPL / スクリプト内での利用例です。DuckDB 接続は duckdb.connect() を用います。

1) 日次 ETL 実行（株価・財務・カレンダーの差分取得）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（LLM）で銘柄ごとの ai_scores を更新
- 必須: OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM を合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring_audit.duckdb")
# conn は DuckDB 接続。必要に応じて接続を保持して利用します。
```

5) 研究用ファクター計算の例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list of dict per code
```

注意点
- AI 機能（score_news / score_regime）は OpenAI の JSON Mode を利用します。API の応答失敗時はフェイルセーフとしてスコアを 0 やスキップする挙動です（例外を必ず上げるわけではありません）。
- ETL / 保存処理は冪等設計です（ON CONFLICT 等で上書き）。部分失敗時でも既存データを毀損しない工夫がなされています。

---

## ディレクトリ構成

主要ファイルとモジュール（src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py          — ニュース NLP（score_news）
    - regime_detector.py   — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得/保存）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETL 便宜エクスポート（ETLResult）
    - quality.py           — データ品質チェック
    - news_collector.py    — RSS 収集 / 前処理
    - calendar_management.py — カレンダー管理・営業日ロジック
    - audit.py             — 監査ログスキーマ初期化
    - stats.py             — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py   — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - research/... （その他ユーティリティ）

各モジュールは概ね DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取り、外部システム（発注 API 等）には依存しない設計になっています（研究用・データ用の分離）。

---

## 補足・運用上の注意

- .env の自動読み込みは import 時に行われます。テストなどで無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API はレート制限があります（約 120 req/min）。jquants_client は内部でレート制御とリトライを実装していますが、大量並列呼び出しは避けてください。
- OpenAI への呼び出しはコストとレートに注意してください。レスポンスは JSON Mode を用い、パースおよび検証処理を行いますが、LLM の応答が不正な場合はスコアをスキップまたは 0 にフォールバックします。
- DuckDB のバージョン差異に注意（executemany の空リストバインド等、コメントにも記載あり）。

---

質問や追加したいドキュメント（例: デプロイ手順、CI 用設定、具体的な依存パッケージ一覧など）があれば知らせてください。必要に応じて README を拡張します。