# KabuSys

KabuSys は日本株のデータパイプライン、リサーチ、ニュース NLP、マーケットレジーム判定、監査ログや ETL を備えた自動売買／リサーチ基盤のライブラリ群です。本 README はリポジトリの概要、機能、セットアップ、基本的な使い方、ディレクトリ構成をまとめたものです。

> 注: 本プロジェクトの設計上、バックテストやスコアリングでルックアヘッドバイアスが入らないように datetime.today()/date.today() を直接参照しない実装方針が採られています。外部 API 呼び出しはエラー時にフォールバックする設計（フェイルセーフ）になっています。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ Python モジュール群です。

- J-Quants API 経由でのデータ取得（株価日足、財務、上場情報、マーケットカレンダー）
- DuckDB を用いたデータ保存・ETL パイプライン（差分取得、保存、品質チェック）
- ニュース収集（RSS）と NLP（OpenAI）による銘柄別センチメント算出
- 市場レジーム判定（ETF の 200 日 MA とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ）、IC 計算、統計ユーティリティ
- 監査ログ（signal / order_request / executions）用スキーマの初期化とユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上のポイント:
- DuckDB を主な永続化層として使用
- API 呼び出しはリトライとレートリミット制御あり
- ルックアヘッドバイアス防止に配慮
- 冪等性（ON CONFLICT DO UPDATE）と監査性に配慮

---

## 機能一覧（主なモジュール／関数）

- kabusys.config
  - 環境変数ロード（.env / .env.local 自動ロード）、Settings オブジェクト
  - 環境変数例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL

- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への冪等保存）
  - 内部に RateLimiter とリトライ／401 リフレッシュ処理あり

- kabusys.data.pipeline / kabusys.data.etl
  - run_daily_etl(conn, target_date, ...)：日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult データクラス（品質問題やエラーの集約）

- kabusys.data.news_collector
  - RSS フィード取得（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - raw_news テーブルへ冪等保存（ID は正規化 URL の SHA-256 ベース）

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)：銘柄別にニュースをまとめて OpenAI（gpt-4o-mini）に投げ、ai_scores に保存
  - calc_news_window(target_date)：ニュース取得ウィンドウ（JST 前日15:00～当日08:30）

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)：ETF(1321) の MA 偏差とマクロセンチメントを合成して market_regime テーブルへ保存

- kabusys.research
  - calc_momentum, calc_value, calc_volatility（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索／評価）
  - zscore_normalize（kabusys.data.stats）

- kabusys.data.quality
  - run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
  - QualityIssue データクラスによる問題収集

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)：監査ログ専用の DuckDB 初期化

その他、calendar_management（営業日ロジック）、stats（統計ユーティリティ）など。

---

## セットアップ手順

以下はローカルで動かすための基本的な手順です。環境やポリシーに応じて適宜読み替えてください。

1. Python 環境
   - 推奨 Python バージョン: 3.9+（ソースは型ヒントに Union | を使うため 3.10 以上がより安全）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要ライブラリをインストール
   - 本リポジトリに requirements.txt がない場合は少なくとも以下をインストールしてください:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに packaging がある場合は pip install -e . や pip install -r requirements.txt を利用してください）

3. 環境変数（.env）
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env/.env.local を自動ロードします（kabusys.config）。
   - 自動ロードを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 必要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...

   - config.py 内では .env を自動読み込み（.env → .env.local の順、.env.local が優先）します。

4. データベース用ディレクトリ作成
   - settings.duckdb_path の親ディレクトリを作っておくか、init 関数が自動作成します。
   - 監査 DB を別途作る場合は init_audit_db() を使用します。

---

## 使い方（簡単な例）

以下は Python スクリプトや REPL から利用する際の代表的な呼び出し例です。各関数は DuckDB 接続（duckdb.connect(...) で得られる接続オブジェクト）を受け取ります。

- Settings（環境変数取得）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

- DuckDB 接続 & 監査 DB 初期化
```python
import duckdb
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# メイン DuckDB 接続
conn = duckdb.connect(str(settings.duckdb_path))

# 監査専用 DB を初期化（ファイル版）
audit_conn = init_audit_db(settings.duckdb_path.parent / "audit_kabusys.duckdb")
```

- 日次 ETL 実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl

# conn は duckdb connection
result = run_daily_etl(conn, target_date=None)  # target_date を指定するとその日で実行
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY で参照）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written scores:", n_written)
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査スキーマを既存 DB に追加
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- 研究モジュール例（ファクター計算 → IC）
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

注意点:
- OpenAI 呼び出しを含む関数は api_key を引数で注入できます（テストやキー切替に便利）。
- 多くの関数は失敗に寛容で、部分失敗時でも他の処理を継続します（ログと ETLResult で状況確認）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: sqlite 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（環境）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

config.Settings によって必須項目は取得時に検証され、未設定の場合は ValueError が発生します。

---

## ディレクトリ構成（主要ファイル）

リポジトリのソースは src/kabusys 以下に配置されています。主要ファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings / .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 + 保存）
    - pipeline.py                   — ETL パイプライン / run_daily_etl / ETLResult
    - etl.py                        — ETL インターフェース（再エクスポート）
    - news_collector.py             — RSS 収集・前処理・保存
    - calendar_management.py        — 市場カレンダー・営業日ロジック
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン、IC、統計サマリー
  - other modules: strategy, execution, monitoring（パッケージ公開対象として __all__ に含まれるが、今回の抜粋では実装割愛）

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、SQL と Python を組み合わせた実装になっています。

---

## ロギングと運用

- 各モジュールは標準 logging を利用しています。環境変数 LOG_LEVEL でログレベルを制御してください。
- J-Quants や OpenAI の API 呼び出しはレート制限・リトライを実装していますが、運用時は API 利用料やレートに気を付けてください。
- OpenAI のレスポンスパース失敗や API エラーは 0.0 スコア等でフォールバックする実装が多く、致命的な例外は最小化されていますが、ログでの監視は推奨します。

---

## テスト・拡張メモ

- OpenAI 呼び出しやネットワーク関係の関数には差し替え（モック）しやすいように内部呼び出しを分離しています（unittest.mock.patch を使って _call_openai_api などを差し替え可能）。
- ETL/保存処理は冪等に設計されているため再実行に耐えます（ON CONFLICT DO UPDATE 等）。
- データ品質チェックは fail-fast ではなく問題を収集して返すため、運用側でアラートや停止判定を行ってください。

---

何か追加で README に入れたい実例（.env.example の具体的内容、CI 設定例、Docker イメージ化手順、より詳細な API 使用例）などがあれば教えてください。必要に応じて README を拡張してテンプレートや具体的なコマンド例を追加します。