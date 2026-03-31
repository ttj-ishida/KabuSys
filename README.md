# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）などのユーティリティ群を提供します。

## 目的（概要）
- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に蓄積する ETL パイプライン
- RSS ニュースを収集して自然言語処理（LLM）で銘柄ごとのセンチメントを算出し ai_scores に保存
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- Research 用のファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索ユーティリティ
- 発注〜約定に至る監査ログスキーマ（DuckDB）を初期化・管理する機能
- データ品質チェック（欠損、スパイク、重複、日付整合性）

---

## 主な機能一覧
- 環境設定読み込みと管理（.env/.env.local 自動読み込み、必須キー検査）
- J-Quants API クライアント（トークン自動リフレッシュ、レートリミット、ページネーション、保存の冪等性）
- 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
- ニュース収集（RSS）と前処理（URL除去、正規化、SSRF/サイズ制限等の安全対策）
- ニュース NLP（OpenAI）による銘柄別スコアリング（batch・リトライ・JSON バリデーション）
- 市場レジーム判定（1321 ETF の MA200 とマクロニュースの LLM スコアを合成）
- 研究モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー）
- 監査ログ（signal_events, order_requests, executions）スキーマ初期化・専用 DB 作成
- データ品質チェック群（check_missing_data, check_spike, check_duplicates, check_date_consistency）

---

## 動作要件
- Python 3.10+
- 必要なライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリの urllib 等を多用）
- 環境変数（主要）
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabu API パスワード（必須）
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector の呼び出し時に省略可能）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用（必須）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL — ログレベル（DEBUG, INFO, ...）

設定読み込みはパッケージ内の config モジュールで行います（プロジェクトルートの .env/.env.local を自動読み込み）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - またはパッケージが setup 配下にある場合: pip install -e .

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成してください。自動的に読み込まれます。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. DuckDB のデータ格納先ディレクトリが必要なら作成
   - mkdir -p data

---

## 基本的な使い方（Python から）

以下は主要な機能の呼び出し例です。各関数は look-ahead bias を防ぐために target_date を明示的に受け取る設計です。

- DuckDB 接続を作成して ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（OpenAI API キーは環境変数または引数で指定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {n} symbols")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化（専用ファイル）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions のテーブル等が初期化されます
```

- research 用ユーティリティ例
```python
from kabusys.research import calc_momentum, calc_value
# calc_momentum(conn, date) のように使用
```

注意:
- OpenAI の呼び出しは内部でリトライや JSON バリデーションを行いますが、API キーは `OPENAI_API_KEY` 環境変数か関数引数で指定してください。
- J-Quants API はリクエストレート制限があります。`JQUANTS_REFRESH_TOKEN` は必須で、`kabusys.data.jquants_client` が自動で ID トークンを取得します。

---

## .env（例）
プロジェクトルートに `.env.example` を配置している場合はそれを参考にコピーしてください。主要なキー例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=sk-...

# kabu ステーション API
KABU_API_PASSWORD=...

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB / 実行環境
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid

# システム
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主要ファイル）
（リポジトリ直下の src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py (score_news をエクスポート)
    - news_nlp.py         — ニュースの LLM スコアリング（batch / JSON mode / バリデーション）
    - regime_detector.py  — 市場レジーム判定（ETF ma200 + macro LLM）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）・ETLResult
    - etl.py              — ETL インターフェース（ETLResult の再エクスポート等）
    - calendar_management.py — 市場カレンダー管理（営業日判定、update job）
    - news_collector.py   — RSS 収集・前処理（SSRF・サイズ・XML 対策）
    - quality.py          — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py            — zscore_normalize 等の統計ユーティリティ
    - audit.py            — 監査ログスキーマ初期化・DB 作成
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — forward returns, IC, rank, factor_summary

---

## 注意事項 / 設計上のポイント
- ルックアヘッドバイアス対策: date を明示的に渡し、内部で date.today() を安易に参照しない設計（ETL と分析の再現性を重視）
- 外部 API 呼び出しはリトライ・フェイルセーフを組み込み、API 失敗時はデフォルト値やスキップで継続する（ただし重大な欠損はログや QualityIssue として報告）
- DuckDB への保存は可能な限り冪等（ON CONFLICT）で実装
- ニュース収集では SSRF 対策・受信サイズ制限・トラッキング除去など安全性に配慮
- OpenAI 呼び出しは JSON Mode を利用し、応答の厳密なバリデーションを行う

---

## 開発 / 貢献
- コードはユニットテストで各 API 呼び出しや外部接続をモックして検証することを想定しています（_call_openai_api 等はテスト用に差し替え可能）。
- バグや機能リクエストは Issue を立ててください。

---

必要であれば、README にチュートリアルや API リファレンス（関数一覧や戻り値の詳細）を追記します。どの機能の詳細を優先してドキュメント化しますか？