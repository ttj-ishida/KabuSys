# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株アルゴリズム取引やリサーチ向けの内部ライブラリ群です。主な目的は以下です。

- J-Quants API からの株価/財務/カレンダー取得（差分ETL・冪等保存）
- RSS ニュースの収集と前処理（SSRF対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント（銘柄別 ai_score）およびマクロセンチメント（市場レジーム）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ツール
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）
- 設定は環境変数 / .env で管理。ローカル .env/.env.local を自動読み込み（オプトアウト可）

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save 関数、認証・レートリミット・リトライ実装）
  - 市場カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS、SSRF 対策、正規化）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログ初期化 / DB 作成（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント（score_news：銘柄ごとに ai_score を ai_scores テーブルへ）
  - レジーム判定（score_regime：ETF 1321 の MA200 とマクロニュースの LLM スコアを合成）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み・検証（自動 .env 読み込み、必須キーの _require）

---

## セットアップ

前提
- Python 3.10 以上（型注釈に `|` 演算子を使用）
- duckdb, openai, defusedxml などが必要（下記参照）

手順（例）

1. レポジトリをクローン
   - git clone <repo>

2. 仮想環境作成・有効化（任意だが推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください：
   pip install -e . または pip install -r requirements.txt）

4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（起動時）。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須環境変数（settings から参照）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabu ステーション API のパスワード
- SLACK_BOT_TOKEN       : Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネルID

任意 / デフォルト付き
- KABU_API_BASE_URL     : デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH           : デフォルト "data/kabusys.duckdb"
- SQLITE_PATH           : デフォルト "data/monitoring.db"
- KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
- LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- OPENAI_API_KEY        : OpenAI API キー（ai.score_news / regime で使用）  
  なお score_news/score_regime に api_key 引数を渡すことでも可能。

注意: .env をバージョン管理に含めないでください（API キー・トークンを含むため）。

---

## 使い方（簡単な例）

以下は代表的な利用方法の抜粋です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の返り値）を受け取ります。

1) ETL（日次パイプライン）の実行例

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path はデフォルト data/kabusys.duckdb
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのセンチメントスコア取得（OpenAIが必要）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数で設定しているなら api_key=None で可
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定（ETF 1321 の MA200 + マクロニュース）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY が必要
```

4) 監査ログ DB を初期化する

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリがなければ自動作成
# conn は duckdb 接続。必要に応じて同一 conn を他処理に渡す。
```

5) ファクター計算・評価（研究用途）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
momentum = calc_momentum(conn, target)
value = calc_value(conn, target)
vol = calc_volatility(conn, target)
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(momentum, ["mom_1m", "mom_3m"])
```

ログや例外は各モジュール内で適切に記録します。AI 系の呼び出しは API エラーをフェイルセーフで扱う設計（失敗時はスコア0やスキップ）になっています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (OpenAI を使う処理で必要)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 (自動 .env 読み込みを無効化)

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / .env 読み込みと設定オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult の再エクスポート
    - news_collector.py              — RSS 収集（SSRF対策・正規化）
    - calendar_management.py         — 市場カレンダー管理（is_trading_day 等）
    - quality.py                     — データ品質チェック
    - stats.py                       — zscore_normalize 等
    - audit.py                       — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             — momentum/value/volatility 計算
    - feature_exploration.py         — forward returns, IC, summary, rank

（リポジトリ全体には docs/ や tests/、例示用スクリプト等が付属する場合があります。本 README はコードベースの主要モジュールを要約しています。）

---

## 注意事項 / ベストプラクティス

- API キーやトークンは必ずシークレット管理し、リポジトリに含めないでください。
- バックテスト目的で DB を使う場合は「ルックアヘッドバイアス」に注意してください。多くの関数は look-ahead を避ける設計（target_date 未満のデータのみ使用、明示的な fetched_at 管理など）になっていますが、呼び出し方に注意してください。
- OpenAI や外部 API の利用はコスト・レート制限があるため、バッチ処理やリトライポリシーを適切に設定して利用してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン依存の注意がコード内にあります。ライブラリ更新時はテストを推奨します。

---

## 開発・テスト

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml がある場所）に依存します。
- テスト時に自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 単体テストでは OpenAI 呼び出しやネットワーク呼び出しをモックする設計になっています（モジュール内の API 呼び出し関数は差し替え可能）。

---

必要であれば、README にサンプル .env.example、データベーススキーマ（DDL）、あるいは主要な API 呼び出しのフロー図なども追加できます。どの情報を優先して追加したいか教えてください。