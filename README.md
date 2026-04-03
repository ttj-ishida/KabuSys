KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株のデータプラットフォーム / リサーチ / 自動売買のためのライブラリ群です。  
主な目的は以下です。

- J-Quants API からの株価・財務・マーケットカレンダーの ETL
- ニュース収集・NLP（LLM を用いた銘柄センチメント評価）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量探索（研究用途）
- 監査ログ（signal → order → execution のトレーサビリティ）
- データ品質チェック

本 README はソースツリー（src/kabusys）に含まれる主要モジュールの使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

主な機能
--------
- data.etl / pipeline: 日次 ETL パイプライン（株価・財務・カレンダー取得、品質チェック）
- data.jquants_client: J-Quants API クライアント（認証・ページネーション・保存用ユーティリティ）
- data.news_collector: RSS からのニュース収集（SSRF 対策、正規化、raw_news への保存）
- data.quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
- data.calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
- data.audit: 監査ログテーブルの初期化 / 管理（signal / order_request / executions）
- research: ファクター計算（モメンタム、ボラティリティ、バリュー）・特徴量解析（forward returns, IC, summary）
- ai.news_nlp: ニュースを LLM（gpt-4o-mini）でセンチメント評価して ai_scores に書き込む
- ai.regime_detector: ETF（1321）200 日 MA とマクロニュース LLM スコアを合成し市場レジームを決定
- config: 環境変数・.env 自動読み込み / 設定ラッパー

セットアップ
-----------

1) 前提
- Python 3.10+（typing の一部記法や型ヒントを利用）
- DuckDB：Python パッケージ duckdb を利用します
- OpenAI Python SDK（openai パッケージ）を一部モジュールで利用
- defusedxml（RSS パースの安全化）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

2) 仮想環境（推奨）
```bash
python -m venv .venv
source .venv/bin/activate
```

3) 依存パッケージのインストール（例）
pip install で必要なパッケージを入れてください。プロジェクトに requirements.txt が無い場合の一例：
```bash
pip install duckdb openai defusedxml
```
（プロジェクト用途により他パッケージが必要になる可能性があります）

4) ローカル開発インストール（任意）
プロジェクトルートで（pyproject.toml / setup.cfg 等がある前提）：
```bash
pip install -e .
```

環境変数 / .env
----------------
config.py はプロジェクトルートにある .env / .env.local を自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。主要な環境変数:

必須（使用する機能に応じて設定）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector）
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注等に利用する場合）

任意
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO"...)

サンプル .env
```
# .env (例)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password

DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動読み込みの優先順:
OS環境変数 > .env.local > .env

使い方（代表的な操作例）
----------------------

基本的に DuckDB 接続を作り、各モジュールの関数を呼び出します。以下はサンプルコードです。

1) DuckDB 接続作成（監査 DB 初期化）
```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # :memory: を指定するとインメモリ
```

2) 日次 ETL 実行（pipeline.run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントのスコア計算（ai.news_nlp.score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込銘柄数:", n_written)
```

4) 市場レジーム判定（ai.regime_detector.score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査スキーマ初期化（既存接続に対して）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

注意点 / 実運用での考慮
--------------------
- Look-ahead バイアス対策: 多くのモジュールは target_date に対して「未満」あるいは明確なウィンドウを使い、datetime.now() を直接参照しない設計になっています（バックテスト用途で重要）。
- OpenAI 呼び出し: gpt-4o-mini と JSON Mode を使う実装です。API 呼出し時にリトライロジック・フォールバック（スコア 0.0）を備えています。API キーは OPENAI_API_KEY を設定してください。
- J-Quants: レート制限（120 req/min）に合わせた RateLimiter と、401 時の自動リフレッシュを実装しています。JQUANTS_REFRESH_TOKEN を設定してください。
- NewsCollector は SSRF や XML インジェクション対策（defusedxml）を取り入れています。

ディレクトリ構成（主要ファイル）
------------------------------
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py               - パッケージ定義（__version__ 等）
  - config.py                 - 環境変数 / .env 自動読み込み、Settings
  - ai/
    - __init__.py
    - news_nlp.py             - ニュース NPL（score_news）
    - regime_detector.py      - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py             - ETL パイプライン / run_daily_etl / ETLResult
    - etl.py                  - ETL インターフェース再エクスポート
    - jquants_client.py       - J-Quants API クライアント（fetch/save）
    - news_collector.py       - RSS 収集・正規化
    - calendar_management.py  - 市場カレンダー管理・営業日ユーティリティ
    - quality.py              - データ品質チェック
    - stats.py                - 統計ユーティリティ（zscore_normalize）
    - audit.py                - 監査ログスキーマ初期化 / 接続作成
  - research/
    - __init__.py
    - factor_research.py      - ファクター計算（momentum/value/volatility）
    - feature_exploration.py  - 将来リターン / IC / 統計サマリー
  - research.* export 各種関数の集合

ドキュメント / 設計ノート
-----------------------
各モジュール冒頭に設計方針（Look-ahead 防止、フェイルセーフ、冪等性、トランザクション管理等）がコメントとして記載されています。運用時はそれらを参照して下さい（ETL のバックフィル日数、品質チェック閾値などは pipeline.run_daily_etl の引数で調整できます）。

ライセンス / 貢献
-----------------
（この README ではソースにライセンス表記が無いため省略します。実リポジトリでは LICENSE を参照してください。）

最後に
-------
開発・運用に際しては必ずテスト環境（paper_trading / development）で十分に検証してから live 環境への移行を行ってください。特に発注や自動売買周りは二重発注や誤発注を防ぐため、監査ログ（order_request_id の冪等性）や十分なリスク制御を導入してください。

必要であれば、README にサンプル .env.example、docker-compose、CI 設定、より詳しい API 使用例（J-Quants / OpenAI の呼び出し方法）などを追記します。希望があれば教えてください。