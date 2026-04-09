# KabuSys

日本株向けの自動売買 / 研究 / データ基盤コンポーネント群です。  
ETL（J-Quants）→ データ品質チェック → ファクター計算 → ニュースNLP → 市場レジーム判定 → 監査ログ までを含むモジュール構成になっています。

Version: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象にしたデータプラットフォームとリサーチ / 売買支援ライブラリ群です。主な目的は以下：

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保管する ETL パイプライン
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と LLM を用いた銘柄別ニュースセンチメント算出
- マーケットレジーム判定（ETF の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）とユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化

設計上の特徴として、ルックアヘッドバイアスを防ぐために日付参照は明示的な引数（target_date）ベースで行い、外部 API 呼び出しと DB 書き込みはできるだけ冪等に実装されています。

---

## 機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（認証・リトライ・レートリミット・保存関数）
  - カレンダー管理（営業日判定、次/前営業日取得、カレンダー更新ジョブ）
  - ニュース収集（RSS、SSRF対策、前処理、raw_news 保存）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321)のMA200乖離とニュースセンチメントを合成して market_regime に登録
- research
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数管理（.env の自動読み込みロジック、Settings クラス）

---

## セットアップ手順

前提
- Python 3.10 以上
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

インストール（ローカル開発想定）
1. リポジトリをクローン
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージと依存インストール（例）
   - pip install -e .    # setup.cfg / pyproject があれば editable install
   - 必要パッケージの例:
     - duckdb
     - openai
     - defusedxml
     - これらを requirements.txt にまとめていれば pip install -r requirements.txt

環境変数
- .env または .env.local をプロジェクトルートに置くと自動読み込みされます（CWD ではなくパッケージファイル位置から .git / pyproject.toml を探索してプロジェクトルートを決定）。
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（本番機能を利用する場合）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL）
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注など）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector）
任意 / 設定系
- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH
- PAPER_FILL_MODE : instant | partial | never | reject（paper_trading 用）

.example (.env.example 相当)
- .env ファイルは KEY=VALUE 形式。コメント行や export KEY=VALUE もサポート。
- 値に引用符を使う場合のエスケープ等に対応しています。

---

## 使い方（主要な呼び出し例）

下記は Python REPL やスクリプト内での利用例です。各関数は明示的に DuckDB 接続と target_date を受け取るため、バックテストやバッチ実行で日付を固定して使えます。

1) ETL（日次パイプライン）の実行
- 目的: J-Quants からデータを差分取得して保存・品質チェックまで行う
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント算出（news_nlp）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数または第3引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

3) 市場レジーム判定（regime_detector）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

5) 監査ログスキーマの初期化
```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring_audit.duckdb")
# または既存接続へ追加:
# conn = duckdb.connect("data/kabusys.duckdb")
# init_audit_schema(conn)
```

注意点:
- all API 呼び出しで API キー未設定だと ValueError が発生します（明示的に渡すか環境変数 OPENAI_API_KEY を設定してください）。
- ETL / API 関連はネットワーク・認証が必要です。ローカルでのオフライン検証はパッチやモックで差し替えてください。

---

## 設定（環境変数主要一覧）

- JQUANTS_REFRESH_TOKEN (必須 for ETL)
- KABU_API_PASSWORD (必須 for 発注)
- OPENAI_API_KEY (必須 for AI モジュール。news_nlp / regime_detector)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (instant|partial|never|reject、デフォルト: instant)
- KABUSYS_ENV (development|paper_trading|live、デフォルト: development)
- LOG_LEVEL (デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

.env の自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールのファイルツリー（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult 等)
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
    - (factor/feature utilities)
  - ai/
    - (LLM 関連処理)
  - data/
    - (ETL / DB / audit / news collector 等)

各モジュールは概ね機能別に分割されており、DuckDB 接続を外部から注入する設計になっています。

---

## 実運用上の注意 / ベストプラクティス

- Secrets は .env ファイルに平文で置く場合はアクセス制御を厳格にしてください。可能であれば環境変数を CI/CD シークレット管理により注入してください。
- OpenAI 呼び出し部分はリトライ・バックオフ・レスポンス検証を備えていますが、トークン料金やレート制限には注意してください。
- ETL は差分取得＋backfill の方針で実装されており、定期バッチで run_daily_etl を実行することを想定しています。
- DuckDB のスキーマと初期化関数（audit.init_audit_db 等）を使って適切にテーブルを作成してください。
- news_collector には SSRF 対策や XML パーサ安全化が実装されていますが、外部 RSS を追加する際は信頼性とライセンスに注意してください。

---

## 貢献 / テスト

- ユニットテストやモックを用いた API 呼び出しの差し替えがしやすい構造になっています（例: kabusys.ai.news_nlp._call_openai_api をモックする等）。
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境依存を切り離すとテストが容易です。

---

質問・改善点や README に追加したい利用例があればお知らせください。README を用途（開発者向け / 運用向け / API リファレンス）に分けて拡張することも可能です。