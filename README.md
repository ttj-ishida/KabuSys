# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、研究用ファクター計算、監査ログ（約定トレーサビリティ）などの機能を提供します。

---

## プロジェクト概要

KabuSys は以下の目的に設計された Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダー等を差分取得し、DuckDB に永続化する（ETL）。
- RSS ベースでニュースを収集し raw_news テーブルへ格納、銘柄対応付けを実施。
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント / マクロセンチメント評価（AI スコアリング）。
- 研究用途のファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ。
- 監査ログ（signal_events / order_requests / executions）用のスキーマ初期化と DB ユーティリティ。
- データ品質チェック（欠損・スパイク・重複・日付不整合検査）。

設計上のポイント：
- ルックアヘッドバイアス回避（内部で date.today() 等を不用意に参照しない設計を意識）。
- DuckDB をデータ基盤に使用し、冪等な保存ロジックを採用（ON CONFLICT）。
- OpenAI / J-Quants 呼び出しに対してリトライやフェイルセーフ実装。

---

## 主な機能一覧

- データ ETL
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）：取得・保存・トークン自動リフレッシュ・レート制御
- ニュース収集 / 前処理
  - fetch_rss, preprocess_text, news → raw_news 保存（kabusys.data.news_collector）
- ニュース NLP / AI スコアリング
  - score_news（銘柄毎の ai_scores 作成、OpenAI で JSON Mode を使用）
  - score_regime（ETF 1321 の MA とマクロニュースの LLM スコアを合成して market_regime を作成）
- 研究用ユーティリティ
  - ファクター計算：calc_momentum, calc_volatility, calc_value（kabusys.research.factor_research）
  - 特徴量探索：calc_forward_returns, calc_ic, factor_summary, rank（kabusys.research.feature_exploration）
  - Z スコア正規化：zscore_normalize（kabusys.data.stats）
- データ品質チェック
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks（kabusys.data.quality）
- 監査ログ（トレーサビリティ）
  - init_audit_schema, init_audit_db（kabusys.data.audit）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子などを使用）
- DuckDB（Python パッケージとしてインストール）
- OpenAI Python SDK（OpenAI の Chat Completions を使用）
- defusedxml（RSS の安全なパース）

例：仮想環境作成とパッケージインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発用にローカルパッケージとしてインストールする場合
pip install -e .
```

環境変数（最低限必要なもの）
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD：kabuステーション API パスワード（必要に応じて）
- SLACK_BOT_TOKEN：Slack 通知用トークン（必要に応じて）
- SLACK_CHANNEL_ID：Slack チャネル ID（必要に応じて）
- OPENAI_API_KEY：OpenAI API キー（score_news / score_regime 実行時に使用）
- DUCKDB_PATH（省略可、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（省略可、デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

.env 自動読み込み
- プロジェクトルート（.git や pyproject.toml を基準）にある .env と .env.local を自動的に読み込みます。
- 読み込み順: OS 環境 > .env.local（上書き） > .env
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env 例（リポジトリに置く場合は .env.example を作成し機密情報は置かないでください）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なサンプル）

下記は基本的な操作例です。詳細は各モジュールの関数を参照してください。

1) DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) OpenAI を使ってニュースセンチメントをスコアリング（score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# 環境変数 OPENAI_API_KEY を設定している場合は api_key 引数は省略可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```

3) マーケットレジーム判定（score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルが作成された接続が返る
```

5) J-Quants ID トークンを明示的に取得する（テストや外部連携で useful）
```python
from kabusys.data.jquants_client import get_id_token

token = get_id_token()  # settings.jquants_refresh_token を参照して取得
```

注意点:
- OpenAI の呼び出しはネットワーク / レートエラーに対してリトライやフェイルセーフが組まれていますが、APIキー・課金設定はご自身で管理してください。
- score_news / score_regime は外部 API を呼ぶため実行にコストが発生します。テスト時は各モジュールの _call_openai_api をモックして振る舞いを差し替えてください（モジュール内に mock 用の意図的な差し替えポイントがあります）。

---

## ディレクトリ構成

主要なファイル・ディレクトリ構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                            -- 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                         -- ニュースセンチメント（銘柄別 ai_scores 生成）
    - regime_detector.py                  -- ETF MA + マクロセンチメントで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                   -- J-Quants API クライアント（取得 / 保存 / 認証）
    - pipeline.py                         -- ETL パイプライン（run_daily_etl 等）
    - etl.py                              -- ETL の公開型（ETLResult）
    - news_collector.py                   -- RSS 収集・前処理・SSRF 対策
    - calendar_management.py              -- 市場カレンダー管理 / 営業日判定
    - quality.py                          -- データ品質チェック
    - stats.py                            -- zscore 正規化等の統計ユーティリティ
    - audit.py                            -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py                  -- momentum / volatility / value ファクター計算
    - feature_exploration.py              -- forward returns, IC, factor_summary 等

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取る関数が多く、DB 接続の管理は呼び出し側に委ねられます。ETL 等は冪等性・トランザクション制御を意識した実装になっています。

---

## 注意事項 / 運用上のヒント

- セキュリティ: .env やトークンは機密情報です。リポジトリに直接含めないでください。
- テスト: 外部 API 呼び出しはモックして単体テストを実施してください（各モジュールに差し替えポイントあり）。
- バックテストでの利用: Look-ahead bias を防ぐ設計になっています。バックテストで過去時点のデータだけを参照する場合も、ETL 時点の fetched_at 等に注意してください。
- 運用環境: 本番（live）で実行する場合は KABUSYS_ENV を `live` に設定し、ログレベルや通知の設定を適切に構成してください。

---

必要であれば README に追記する内容（例：詳しい API リファレンス、CI/CD、Docker 化、実運用の runbook、SQL スキーマ定義の抜粋など）を教えてください。