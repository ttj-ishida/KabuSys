# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、リサーチ用のファクター計算、監査ログ（トレーサビリティ）、および運用向け設定管理を含みます。

## 特徴（機能一覧）
- データ取得 / ETL
  - J-Quants API からの株価日足（OHLCV）・財務データ・マーケットカレンダー取得（ページネーション対応、トークン自動リフレッシュ、レート制御、リトライ）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、重複、将来日付、スパイク検出などの品質チェック（quality.run_all_checks）
- ニュース収集 & NLP
  - RSS 取得と前処理（SSRF 対策・トラッキング URL 除去）
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメントスコアリング（銘柄別 ai_scores 生成）
  - マクロニュースと ETF MA200 乖離からの日次市場レジーム判定（bull/neutral/bear）
- リサーチ（研究用）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン、IC（Information Coefficient）、ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注防止を考慮
- 設定管理
  - .env / .env.local / OS 環境変数から自動読み込み（ただし無効化可能）
  - 運用環境（development / paper_trading / live）やログレベルの検証

---

## 要件
- Python 3.10+
- 主な依存パッケージ（少なくとも以下）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib, logging, datetime, pathlib など

依存関係はプロジェクト配布側で requirements.txt / pyproject.toml を用意してください。

---

## 環境変数（主なもの）
アプリケーションは環境変数またはプロジェクトルートの `.env` / `.env.local` を参照します。自動ロードはデフォルトで有効です（.git または pyproject.toml をプロジェクトルートとして探索）。

必須（実行時に必要となるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行に必須）
- KABU_API_PASSWORD: kabuステーション等の API パスワード（実行環境に応じて）

任意（運用向け / デフォルト値あり）
- OPENAI_API_KEY: OpenAI API キー（news NLP / regime 判定に使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視・プロセス管理関連
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）

補助:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、パッケージ読み込み時の .env 自動読み込みを無効化できます（テスト用途）。

.env のパース実装は bash ライクな形式（export の有無、クォート、インラインコメントの取り扱い）に対応しています。

---

## セットアップ手順（例）
1. リポジトリをクローン
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があれば pip install -e . 等）
4. .env を作成（プロジェクトルート）
   - .env.example がある想定。最低限 JQUANTS_REFRESH_TOKEN を設定してください。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
5. 必要に応じてデータディレクトリを作成
   - mkdir -p data

---

## 初期化・基本的な使い方（コード例）
以下は Python REPL またはスクリプトからの簡単な利用例です。

- DuckDB に接続して日次 ETL を実行（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key=None なら OPENAI_API_KEY を参照
print("score_news wrote:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
res = score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーは環境変数から取得
print(res)
```

- 監査ログ DB の初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルを操作可能
```

- ETL 内部ユーティリティ（個別 ETL の実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

注意:
- OpenAI 呼び出しはネットワークと料金が発生します。テスト時は各モジュールの private 関数（_call_openai_api 等）をモックする設計になっています。
- run_daily_etl / score_news / score_regime はルックアヘッドバイアスを避けるため内部で date.today() を直接使わない設計です。必ず対象日（target_date）を明示して呼び出すことが推奨されます。

---

## 運用メモ
- .env の自動ロード順: OS 環境変数 > .env.local > .env（.env.local の方が上書きされる）
- 環境切替: KABUSYS_ENV により is_live / is_paper / is_dev を判定
- ログレベル検証: LOG_LEVEL は DEBUG|INFO|WARNING|ERROR|CRITICAL のいずれかでなければ ValueError を投げます
- ETL は品質チェック（quality.run_all_checks）を行い、QualityIssue を返します。致命的エラーや品質エラーの扱いは呼び出し側で決定してください。

---

## ディレクトリ構成（主なファイルと説明）
（プロジェクトの src/kabusys 以下を抜粋）

- kabusys/__init__.py
  - パッケージのバージョン情報とエクスポート

- kabusys/config.py
  - 環境変数・設定管理（.env 自動読み込み、Settings クラス）

- kabusys/ai/
  - news_nlp.py      : ニュースの NLP スコアリング（OpenAI 呼び出し、score_news）
  - regime_detector.py : マクロセンチメント + ETF MA200 で市場レジーム判定（score_regime）
  - __init__.py

- kabusys/data/
  - jquants_client.py    : J-Quants API クライアント（取得・保存ロジック, rate limit, retry）
  - pipeline.py          : ETL パイプライン（run_daily_etl 他）
  - etl.py               : ETL 結果型の再公開
  - news_collector.py    : RSS 収集・前処理・保存ロジック
  - calendar_management.py : 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - quality.py           : データ品質チェック（欠損・スパイク・重複・日付整合性）
  - stats.py             : 汎用統計ユーティリティ（zscore_normalize）
  - audit.py             : 監査ログテーブル定義と初期化
  - __init__.py

- kabusys/research/
  - factor_research.py   : ファクター計算（momentum, value, volatility）
  - feature_exploration.py : 将来リターン、IC、統計サマリ、rank
  - __init__.py

- kabusys/ai/news_nlp.py / regime_detector.py : OpenAI 呼び出しに関する細かなリトライ・パース・サニティチェックを実装

---

## テスト・開発 tips
- OpenAI や外部 API 呼び出し部分はモックしやすいように設計されています（モジュール内部の _call_openai_api を patch する等）。
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからパッケージを読み込んでください。
- DuckDB を使うため軽量にローカルデータベースを運用可能。監査ログ用に別 DB を作ることも推奨。

---

## 参考
- 各モジュールの docstring に設計方針や処理フローが詳細に書かれています。実装や拡張の際はそちらを先に参照してください。

---

以上がこのコードベースの概要と導入・利用方法の README です。README に追加してほしい実行例（CLI スクリプト、Docker、CI 手順など）があれば教えてください。