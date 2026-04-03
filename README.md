# KabuSys

軽量な日本株向けデータプラットフォーム兼自動売買補助ライブラリ（モジュール群）。  
ETL（J-Quants → DuckDB）、データ品質チェック、研究用ファクター計算、ニュースのNLPスコアリング（OpenAI利用）、市場レジーム判定、監査ログ（発注/約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数一覧
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株向けのデータ収集・前処理・研究・監視・監査ログのユーティリティ群を集めたパッケージです。  
主な用途は以下の通りです。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- raw_prices 等の品質チェック（欠損・重複・スパイク・日付不整合）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量評価（IC、統計サマリー）
- RSS ベースのニュース収集と OpenAI によるニュースセンチメント（銘柄毎）付与
- マクロニュース + ETF MA による市場レジーム判定（bull/neutral/bear）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化
- kabu station（kabu API）連携や監視用設定管理（環境変数ベース）

設計上、バックテストやルックアヘッドバイアスを防ぐために「現在時刻参照を内部で行わない」よう配慮されています（関数に target_date を明示的に与える）。

---

## 機能一覧
主なモジュールと機能（抜粋）

- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）
  - 設定プロパティ（J-Quants トークン、OpenAPI/LINE、DB パス、閾値等）
- kabusys.data
  - jquants_client: J-Quants API の取得/保存（差分取得・ページネーション・リトライ・レートリミット）
  - pipeline / etl: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl 等
  - quality: データ品質チェック（missing, duplicates, spike, date consistency）
  - calendar_management: 市場カレンダー操作・営業日判定ユーティリティ
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF 対策、XML 安全パーサ等）
  - audit: 監査ログテーブル作成・初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得し ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) MA とマクロニュース（LLM）を合成して market_regime に書き込む
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility 等
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 環境（推奨）
   - Python 3.10+ を推奨（typing の | 演算子等を使用）
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要最低限:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそちらを利用してください）

4. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants 用リフレッシュトークン）
     - KABU_API_PASSWORD（kabu station API 用パスワード）※ 使用する場合
   - 詳細は下部の「環境変数一覧」を参照

5. データディレクトリ作成
   - デフォルトの DuckDB パスは data/kabusys.duckdb、監視用 sqlite は data/monitoring.db。必要に応じて親ディレクトリを作成してください（init 関数は親ディレクトリを自動作成するものもあります）。

---

## 使い方（例）

以下は典型的な利用例スニペット。すべて Python スクリプト／ REPL で実行できます。

- DuckDB 接続を作り ETL を実行する（日次 ETL）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は Path 型
conn = duckdb.connect(str(settings.duckdb_path))

# target_date を省略すると今日が対象（内部は明示的 date を使うこと推奨）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを取得して ai_scores に書き込む（OpenAI API Key 必須）:

```python
import os
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

os.environ["OPENAI_API_KEY"] = "<your-openai-key>"
conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written} ai scores")
```

- 市場レジームをスコアリング（1321 ETF + マクロニュース via OpenAI）:

```python
import os
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

os.environ["OPENAI_API_KEY"] = "<your-openai-key>"
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化して接続を取得する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリがなければ自動作成
# テーブルが作成され、UTC タイムゾーンに設定されます
```

- ファクター計算・IC 計算（研究用途、DB 内の prices_daily を参照）:

```python
from kabusys.research.factor_research import calc_momentum
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
fwd = calc_forward_returns(conn, target_date=date(2026, 3, 20), horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

---

## 環境変数一覧（settings が参照する主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。ETL / jquants_client が使用します。

- KABU_API_PASSWORD (必須 if using kabu)
  - kabu station API 接続パスワード

- KABU_API_BASE_URL (任意)
  - デフォルト: http://localhost:18080/kabusapi

- OPENAI_API_KEY (必要な機能のみ)
  - kabusys.ai.* の OpenAI 呼び出しに使用。score_news / score_regime の api_key 引数でも指定可。

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)
  - 通知用途等で利用する場合。

- DUCKDB_PATH (任意)
  - デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)
  - デフォルト: data/monitoring.db

- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START (監視用)
  - デフォルト: data/execution.pid / data/kill.flag / KILL_FLAG_CLEAR_ON_START default "0"

- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - 監視しきい値（デフォルト 90/85/90 等）

- KABUSYS_ENV
  - 値: development / paper_trading / live（デフォルト development）

- LOG_LEVEL
  - 値: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

自動ロード挙動:
- プロジェクトルート（.git または pyproject.toml がある場所）を起点に .env を読み、続けて .env.local を上書き読み込みします。
- 自動ロードを抑制する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 注意点 / 実運用上のヒント
- OpenAI 呼び出しは API 料金が発生します。score_news/score_regime は外部 API 依存なので運用時はキー管理とコストを注意してください。
- jquants_client は API レートリミット（120 req/min）・リトライ・トークン自動リフレッシュ等を実装しています。JQUANTS_REFRESH_TOKEN を適切に設定してください。
- ETL は差分取得 + バックフィル（デフォルト 3 日）を行います。バックテスト用に過去データを固定する場合は初回ロードと使用方法に注意してください（ルックアヘッドバイアス対策）。
- news_collector は SSRF や XML Attack 対策（defusedxml / ホストチェック / レスポンスサイズ制限）を備えていますが、RSS ソースの信頼性には注意してください。
- DuckDB の executemany に関する注意（空リスト不可）への対応がコード中にあります。直接 SQL を投げる場合は互換性を意識してください。

---

## ディレクトリ構成（主要ファイル）
リポジトリ内の主要モジュールとファイル:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            -- 銘柄ニュースのセンチメント付与 (score_news)
    - regime_detector.py     -- 市場レジーム判定 (score_regime)
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch/save）
    - pipeline.py            -- ETL パイプライン / run_daily_etl 等
    - etl.py                 -- ETLResult 再エクスポート
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py -- JPX カレンダー管理、営業日ユーティリティ
    - news_collector.py      -- RSS 収集・前処理
    - audit.py               -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank

（他の補助モジュールやユーティリティがさらに含まれます）

---

## ライセンス / 貢献
- README にはライセンス情報が含まれていません。リポジトリの LICENSE ファイルを参照してください。
- バグ報告や Pull Request はリポジトリの Issue / PR フローに従ってください。

---

この README はコードベースの主要な使い方と構成をまとめたものです。実行時の詳細な設定や運用手順はプロジェクトに同梱のドキュメント（.env.example や運用手順書）があれば併せて参照してください。必要であれば、サンプルスクリプトや CLI ラッパーの README も作成できます。