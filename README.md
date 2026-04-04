# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）。  
ETL（J-Quants 経由の株価・財務・カレンダー収集）、ニュース収集・NLP（OpenAI）による銘柄センチメント評価、リサーチ用ファクター計算、監査（オーダー/約定）スキーマなどのユーティリティを提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数（主要な設定）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は、日本株の自動売買システムおよびデータプラットフォームのための共通ライブラリ群です。  
主に次を目的とします。

- J-Quants API を用いた株価・財務・カレンダーデータの差分ETL
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価（銘柄単位 / マクロ）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- DuckDB を用いた監査ログ / スキーマ初期化（order / execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の要点：ルックアヘッドバイアスの回避、冪等性、外部APIの堅牢なリトライ・レート制御、SSRF対策。

---

## 機能一覧（主なモジュール）
- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）、環境変数管理
- kabusys.data
  - jquants_client: J-Quants API 呼び出し・ページネーション、DuckDB への保存（冪等）
  - pipeline: 日次 ETL 実行（run_daily_etl）等と ETLResult
  - news_collector: RSS 収集、記事正規化、raw_news への保存
  - calendar_management: 市場カレンダーの取得／営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査用スキーマ定義と初期化（init_audit_schema / init_audit_db）
  - stats: z-score 正規化ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとニュースセンチメントを算出して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA 乖離とマクロニュース LLM を組合せ市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. Python 環境（推奨）
   - Python 3.10 以上を推奨（PEP 604 の union 型等を使用）
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（代表的なライブラリ）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - 開発向けに pyproject.toml / requirements.txt がある場合はそちらを利用:
     - pip install -e .
     - あるいは pip install -r requirements.txt

4. 環境変数 / .env の準備
   - ルートに `.env` または `.env.local` を置くことで自動読み込みされます（優先順: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ（必要に応じて自動生成）
   - デフォルトの DuckDB ファイルは data/kabusys.duckdb
   - 監視用 SQLite は data/monitoring.db
   - 監査DB を初期化する場合、parent ディレクトリは自動作成されます（init_audit_db 参照）。

---

## 簡単な使い方（コード例）

- DuckDB に接続して日次 ETL 実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

- 市場レジームスコアを計算:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査スキーマ初期化（新規監査DBを作成）:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査テーブルへ書き込みが可能
```

注意:
- OpenAI 呼び出しは API キーが必須（api_key 引数か環境変数 OPENAI_API_KEY）。
- J-Quants API はリフレッシュトークンが必要（環境変数 JQUANTS_REFRESH_TOKEN）。

---

## 主要な環境変数（概要）
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（必須：jquants_client.get_id_token 等で使用）
- KABU_API_PASSWORD
  - kabuステーション API のパスワード（発注連携等で使用）
- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY
  - OpenAI API キー（news_nlp / regime_detector で利用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
  - 通知用（任意）
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - デフォルト: data/monitoring.db
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - 実行監視関連（デフォルト path は data/ 配下）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - 監視スレッショルド
- KABUSYS_ENV
  - 有効値: development, paper_trading, live（デフォルト development）
- LOG_LEVEL
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト INFO）

.env の自動読み込み:
- プロジェクトルートを .git または pyproject.toml から検出して .env を読み込みます。
- .env.local は .env を上書きします（OS 環境変数は保護されます）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）
（src/kabusys 以下の主要ファイルを示します）

- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py (環境変数管理・自動 .env 読み込み)
  - ai/
    - __init__.py
    - news_nlp.py (銘柄ニュースの LLM スコアリング)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存ユーティリティ)
    - pipeline.py (ETL パイプライン, ETLResult)
    - etl.py (ETLResult の再エクスポート)
    - news_collector.py (RSS 収集・前処理)
    - calendar_management.py (市場カレンダー管理、営業日判定)
    - quality.py (データ品質チェック)
    - stats.py (z-score 等)
    - audit.py (監査スキーマ定義・初期化)
  - research/
    - __init__.py
    - factor_research.py (モメンタム / ボラティリティ / バリュー)
    - feature_exploration.py (将来リターン, IC, 統計サマリー)
  - research/*、ai/* 内に多数の関数・ユーティリティが実装されています。

この README の記載内容はコード内ドキュメント（docstring）に基づいてまとめています。各モジュールの詳細実装やパラメータについては該当ファイルの docstring を参照してください。

---

## テスト・開発に関するメモ
- OpenAI 呼び出しやネットワーク関連はモックが用意しやすいように実装が分離されています（例: news_nlp._call_openai_api を patch）。
- DuckDB を ":memory:" で使えばインメモリでの単体テストが容易です。
- .env 読み込みの自動化を無効にしてテスト環境を安定化できます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

ご不明点や追加で README に記載したい使用例（CI、デプロイ、監視手順など）があれば指示ください。