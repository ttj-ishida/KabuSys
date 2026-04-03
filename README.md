# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（約定トレース）、市場レジーム判定などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得・品質管理・特徴量計算・AI ベースのニュース分析・市場レジーム判定・監査用テーブル構築などを行うためのコード群です。DuckDB をデータプラットフォームとして用い、J-Quants API からのデータ取得や OpenAI（gpt-4o-mini）によるニュースセンチメント評価を組み合わせて、研究（research）・データ（data）・AI（ai）層の機能を提供します。

設計上の特徴：
- Look-ahead バイアス防止のため、日付の扱いに注意し ETL/スコアリングは指定日ベースで処理
- ETL / 保存は冪等（ON CONFLICT を利用）で安全
- 外部 API 呼び出しに対してリトライ、バックオフ、フェイルセーフを備える
- ニュース収集に対する SSRF 対策や XML パース安全化を実装

---

## 主な機能一覧

- data
  - J-Quants API クライアント（fetch / save / 認証・レート制御・リトライ）
  - ETL パイプライン（run_daily_etl、個別 ETL ジョブ）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - マーケットカレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS 取得、前処理、raw_news への保存）
  - 監査ログ（signal_events / order_requests / executions テーブルの初期化）
  - 汎用統計ユーティリティ（Z-score 正規化等）
- ai
  - ニュース NLP スコアリング（銘柄ごとの ai_score を ai_scores に書き込む）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- research
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン・IC 計算・統計サマリー等
- 設定管理
  - 環境変数（.env / .env.local / OS 環境）の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ユーティリティ

---

## セットアップ手順

前提：Python 3.10+ を推奨（型注釈で Union | を使用しています）

1. リポジトリをクローンまたはコピー
2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （任意）テスト・開発用に logging 等の標準ライブラリを利用
   - プロジェクトに requirements.txt があれば pip install -r requirements.txt
4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるフォルダ）に `.env` または `.env.local` を置くと自動読み込みされます
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
   - 必須環境変数の例（後述の「設定（環境変数）」参照）
5. DuckDB/監査 DB 用ディレクトリ作成（デフォルトは data/）
   - mkdir -p data

---

## 設定（環境変数）

主な環境変数（大文字）:

必須:
- JQUANTS_REFRESH_TOKEN  
  - J-Quants API のリフレッシュトークン。jquants_client.get_id_token で使用。

- KABU_API_PASSWORD  
  - kabu ステーション API のパスワード（発注モジュールが利用）。

OpenAI 関連:
- OPENAI_API_KEY  
  - news_nlp.score_news / regime_detector.score_regime に使用（引数でキー注入も可）。

任意:
- KABUSYS_ENV ＝ development | paper_trading | live （デフォルト: development）
- LOG_LEVEL ＝ DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用途の sqlite、デフォルト: data/monitoring.db）
- PID_FILE_PATH（実行監視用、デフォルト: data/execution.pid）
- KILL_FLAG_PATH（実行停止フラグ、デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（"1"で起動時にクリア）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）

.env 例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意:
- .env の読み込み順は OS 環境 > .env.local > .env（.env.local が優先）
- パーサは簡易シェル形式に対応（export 文やクォート、コメント処理あり）

---

## 使い方（主要な呼び出し例）

以下は PythonREPL / スクリプトでの利用例です。適宜 logging 設定や例外処理をしてください。

1) DuckDB 接続を作って ETL を実行する（日次 ETL）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))  # target_date 省略で今日
print(result.to_dict())
```

2) ニュース NLP スコアを生成する:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("書込銘柄数:", n_written)
```

3) 市場レジームを判定して保存する:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログスキーマを初期化する:
```python
import duckdb
from kabusys.data.audit import init_audit_schema, init_audit_db
from kabusys.config import settings

# 既存の main DB に監査テーブルを追加
conn = duckdb.connect(str(settings.duckdb_path))
init_audit_schema(conn, transactional=True)

# または監査専用 DB を作成して接続を取得
audit_conn = init_audit_db("data/audit.duckdb")
```

5) ニュース RSS を取得して処理する（news_collector を利用）:
- news_collector.fetch_rss は RSS をパースして NewsArticle のリストを返します。取得結果を DB に保存するロジックはプロジェクト側で組み合わせてください。

6) J-Quants から直接データを取得する（デバッグ用）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# get_id_token() は settings.jquants_refresh_token を利用
quotes = fetch_daily_quotes(date_from=..., date_to=..., id_token=None)
```

注意点:
- OpenAI 呼び出しは内部でリトライや JSON モードの処理を行います。テスト時は各モジュールの _call_openai_api をモックすることを想定しています（例: unittest.mock.patch）。
- ETL/保存関数は DuckDB のテーブルスキーマが前提。スキーマ初期化はプロジェクト側のスキーマ初期化ユーティリティを使用してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（.env の自動読み込み、settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP スコアリング（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save/get_id_token）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - news_collector.py — RSS ニュース取得・前処理
  - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
  - audit.py — 監査ログテーブル定義・初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — forward returns, IC, factor_summary, rank

（上記以外に strategy / execution / monitoring 等の名前が __all__ に含まれる想定ですが、今回提示コードの範囲では data / ai / research に重点があります。）

---

## 開発・テスト時の注意点

- 環境変数の自動読み込みはプロジェクトルートを検出して `.env` / `.env.local` を読み込みます。テストで自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API 呼び出し部はモジュール内で `_call_openai_api` を定義しており、ユニットテストではこれを patch することで実 API 呼び出しを回避できます。
- DuckDB の executemany は空リストを受け付けないバージョンの挙動に配慮した実装が多く見られます。呼び出し側でも空のパラメータを渡さないように注意してください。
- news_collector の外部ネットワークアクセスは SSRF 回避ロジックや最大受信バイト数制限を持ちますが、本番運用時のフィードソースの信頼性は運用者側で確認してください。

---

## ライセンス・貢献

（プロジェクト固有の LICENSE があればここに記載してください）

---

この README はコードベースに基づいて作成しました。追加で README に掲載したい実行スクリプト例や CI/CD、Docker の利用方法等があれば教えてください。必要に応じてサンプル .env.example や schema 初期化スクリプトも作成します。