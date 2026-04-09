# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント算出）、因子計算・研究、監査ログ（発注 → 約定のトレース）、市場レジーム判定などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の研究・自動売買基盤を構築するための内部ライブラリ群です。主な目的は以下です。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL と DuckDB への永続化
- RSS を用いたニュース収集と前処理、OpenAI（gpt-4o-mini）によるニュースのセンチメント解析
- ファクター計算（モメンタム、ボラティリティ、バリュー等）や探索的解析ユーティリティ
- 市場レジーム判定（ETF MA 乖離 + マクロニュースセンチメントの合成）
- 監査ログスキーマ（シグナル → 発注 → 約定のトレース）と初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上の特徴:
- DuckDB を中心としたローカル分析データベース設計
- Look-ahead バイアス回避（内部で date.today() 等を直接参照しない設計）
- API 呼び出しはリトライとレート制御を備えた実装
- 冪等保存（INSERT ... ON CONFLICT DO UPDATE 等）による安全な ETL

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env と OS 環境変数の読み込み、設定値の提供（settings オブジェクト）
  - 自動 .env ロードの ON/OFF（KABUSYS_DISABLE_AUTO_ENV_LOAD）

- kabusys.data
  - jquants_client: J-Quants API 呼び出し・保存ユーティリティ（fetch / save）
  - pipeline: 日次 ETL の実装（run_daily_etl 等）および ETLResult
  - calendar_management: 市場カレンダー判定（is_trading_day など）・更新ジョブ
  - news_collector: RSS 取得、前処理、raw_news への保存支援
  - quality: データ品質チェック群（check_missing_data, check_spike など）
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログスキーマ定義と初期化（init_audit_schema / init_audit_db）

- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約し OpenAI でセンチメント算出 → ai_scores へ書込
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュースの LLM センチメントを合成して market_regime へ保存

- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value（ファクター計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（研究用ユーティリティ）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型合成や from __future__ annotations を用いているため）
- DuckDB（Python パッケージとしてインストール）
- OpenAI Python SDK（OpenAI API を利用する機能を使う場合）
- defusedxml（RSS パースで使用）

推奨インストール手順（プロジェクトルートで実行）:

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   追加でテストや運用に必要なパッケージがある場合は適宜インストールしてください。

3. ソースを editable インストール（任意）
   - pip install -e .

4. 環境変数 (.env) を準備
   - プロジェクトルートに `.env` / `.env.local` を配置すると、kabusys.config が自動で読み込みます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必要な主要環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 処理を使う場合必須）
- KABU_API_PASSWORD: kabuステーション API 利用時のパスワード
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: データ用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: paper trading 時のモック fill モード（instant/partial/never/reject）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要ユースケース）

以下はライブラリをプログラムから使う最小例です。DuckDB の接続は `duckdb.connect()` で取得して各関数に渡します。

1) 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（ai_scores）を作成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None -> 環境変数 OPENAI_API_KEY を使用
print(f"scored {count} codes")
```

3) 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

4) 監査ログデータベースを初期化する
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って order_requests / executions に記録できます
```

5) カレンダージョブを手動で実行する
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect(str(settings.duckdb_path))
saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved calendar rows: {saved}")
```

注意点:
- OpenAI を呼ぶ関数（score_news / score_regime）は API キーが必要です。引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API 呼び出しは JQUANTS_REFRESH_TOKEN が必要です（settings.jquants_refresh_token が参照されます）。
- ETL は DuckDB 上のスキーマ（raw_prices / raw_financials / market_calendar / raw_news など）が前提です。スキーマ作成は別途提供されているスクリプトや初期化ユーティリティを用いてください。

---

## 設定と挙動に関する補足

- .env の自動ロード順序:
  - OS 環境変数 > .env.local > .env
  - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env の読み込みはパッケージの配置に依存せずプロジェクトルート（.git または pyproject.toml を探索）から行われます。

- settings（kabusys.config.Settings）により以下のメソッド/プロパティで設定値を取得できます:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url
  - line_channel_access_token, line_user_id
  - duckdb_path, sqlite_path, paper_fill_mode, paper_sqlite_path
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start
  - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
  - env, log_level, is_live, is_paper, is_dev

- Paper Trading の挙動:
  - PAPER_FILL_MODE: instant / partial / never / reject をサポート（モックブローカーの振る舞い切替え）

---

## ディレクトリ構成（主なファイル）

以下はソースルートが `src/kabusys` の想定です（本 README は提供されたコードベースを基にしています）。

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
    - (その他: feed clients, helpers 等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（因子計算・探索用ユーティリティ）
  - monitoring/ (README 要求には含めるよう __all__ にあるが実体はコードベースにより追加)
  - strategy/, execution/, monitoring/ など（パッケージ __all__ に含める構成）

（上記は主要モジュールの抜粋です。実際のリポジトリには追加のサブパッケージやスクリプトが存在する可能性があります。）

---

## 開発 / 貢献時の注意

- DuckDB に対する SQL 実行ではパラメータバインド（?）を使い、SQL インジェクションを避けています。
- OpenAI や外部 API 呼び出しはリトライと指数バックオフ、エラー時のフェイルセーフ（ゼロスコアやスキップ）を実装しています。
- テスト時の差し替え（モック）を想定した設計になっており、内部の API 呼び出し関数は patch で置き換え可能です（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- Look-ahead バイアスに注意してください。多くの関数は内部で「target_date 未満のデータのみ参照」や「target_date を引数で受け取る」設計になっています。

---

## ライセンス / 参考

この README は提供されたコードベースの説明用に作成しています。実際の導入・運用時には J-Quants / OpenAI / 各種 API の利用規約を確認してください。

---

もし特定の操作（ETL スキーマの初期化 SQL、.env.example の具体的な雛形、サンプルデータでの動作確認手順、CI 用のコマンド等）を README に追加したい場合は、用途を教えてください。必要に応じて追記します。