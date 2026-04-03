# KabuSys — 日本株自動売買プラットフォーム（README）

概要
----
KabuSys は日本株のデータ取得・品質管理・特徴量計算・ニュース NLP（LLM）によるセンチメント評価・市場レジーム判定・監査ログなどを備えた自動売買プラットフォーム向けのライブラリ群です。  
主に以下用途を想定しています。

- J-Quants API を用いた株価 / 財務 / カレンダーの差分 ETL
- DuckDB を用いたデータ保存・分析
- ニュース記事の収集・前処理・LLM による銘柄センチメント算出
- ETF 指標とマクロニュースを組み合わせた市場レジーム判定
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 研究用のファクター計算・特徴量探索ユーティリティ

主な機能一覧
--------------
- data
  - jquants_client: J-Quants からデータ取得（株価、財務、上場銘柄、マーケットカレンダー）・DuckDB への保存（冪等）
  - pipeline / etl: 日次差分 ETL を実装（backfill・品質チェック含む）
  - news_collector: RSS 収集・前処理・raw_news への保持（SSRF 対策・トラッキング除去）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - audit: 監査ログスキーマの初期化・管理（signal / order_request / executions）
  - stats: 汎用統計ユーティリティ（Zスコア正規化等）
- ai
  - news_nlp.score_news: 指定ウィンドウのニュースをまとめて LLM に投げ、銘柄ごとの ai_score を ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）200日 MA 乖離とニュースセンチメントを合成して市場レジームを判定し market_regime に保存
- research
  - factor_research: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等

前提 / 必要環境
----------------
- Python 3.10+
- duckdb
- openai (OpenAI の新 SDK を想定)
- defusedxml
- （標準ライブラリ以外の依存は setuptool/pyproject に記載される想定）

インストール（開発環境）
-----------------------
1. リポジトリをクローン
2. 仮想環境を作成・有効化
3. 依存パッケージをインストール（例）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"   # プロジェクトが pyproject / setup を提供している想定
# または必要なパッケージだけ:
pip install duckdb openai defusedxml
```

設定（環境変数）
----------------
プロジェクトは .env / .env.local（プロジェクトルート）を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必須・推奨の環境変数:

必須
- JQUANTS_REFRESH_TOKEN  
  → J-Quants 用リフレッシュトークン（jquants_client.get_id_token に利用）
- KABU_API_PASSWORD  
  → kabuステーション等の API パスワード（実行・注文モジュールで使用）

任意（機能に応じて）
- OPENAI_API_KEY  
  → OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- KABUSYS_ENV  
  → 実行モード: development / paper_trading / live（デフォルト development）
- LOG_LEVEL  
  → ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID  
  → 通知用 LINE トークン
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）  
- SQLITE_PATH（監視系用 SQLite、デフォルト data/monitoring.db）  
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

.env の自動読み込みは、プロジェクトルートを .git または pyproject.toml を基準に探索して行います。

セットアップ（データベース初期化）
---------------------------------
監査ログ用の DuckDB を初期化する例:

```python
from pathlib import Path
import duckdb
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)  # テーブル作成、UTC タイムゾーン固定
```

基本的な使い方（サンプル）
--------------------------

1) DuckDB 接続を用意して ETL を実行（日次 ETL）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- run_daily_etl は calendar / prices / financials の差分取得と品質チェックを行い、ETLResult を返します。

2) ニュースセンチメント（AI）スコア付与

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print("書き込んだ銘柄数:", n_written)
```

- score_news は raw_news / news_symbols / ai_scores を参照・更新します。OPENAI_API_KEY を環境変数に設定しておくと api_key 引数は不要です。

3) 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルに保存します。

4) RSS フィード取得（ニュース収集）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

設計上の注意点 / 制約
---------------------
- ルックアヘッドバイアス対策: 日付計算・クエリは target_date より未来のデータを直接参照しない設計になっています（バックテスト適合）。
- ETL / API は冪等（ON CONFLICT / INSERT … DO UPDATE）で実装されています。
- OpenAI 呼び出しはリトライ・フォールバックを含み、API 失敗時は安全側のデフォルト（例: スコア 0.0）で継続することがあります。
- DuckDB バインディングに対する互換性（executemany の空リスト等）に注意した実装が行われています。
- news_collector は SSRF・XML Bomb 等を考慮した安全な取得処理を実装しています（defusedxml、ホスト検査、リダイレクト検査、レスポンスサイズ制限等）。

ディレクトリ構成（主要ファイル）
-------------------------------

想定されるパッケージ構造（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 読み込みロジック（settings）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存ロジック
    - pipeline.py                   — ETL パイプライン + run_daily_etl 等
    - etl.py                        — ETL インターフェース再エクスポート
    - news_collector.py             — RSS 取得・前処理
    - quality.py                    — データ品質チェック
    - calendar_management.py        — 市場カレンダー管理・営業日ユーティリティ
    - audit.py                      — 監査ログスキーマ初期化・DB 初期化ヘルパ
    - stats.py                      — 汎用統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility 等
    - feature_exploration.py        — 将来リターン・IC・summary
  - research/... (その他研究用ユーティリティ)
  - その他: strategy/ execution/ monitoring（パッケージとして __all__ に置かれますが、このコードベースでは主要ロジックは上記に含まれます）

運用上のヒント
---------------
- .env と .env.local の読み込み順:
  - OS 環境変数 > .env.local（override=True）> .env（override=False）
- 自動 .env 読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利です）。
- ETL や AI 呼び出しは API レートやコストに注意して運用してください（OpenAI / J-Quants のレート制限・請求）。

開発・貢献
---------
- まず lint / formatting と単体テストを整備してください（このリポジトリでは標準ライブラリのみで実装されている箇所が多く、テストしやすい設計になっています）。
- 外部 API 呼び出しはモック可能なように設計されています（例: news_nlp._call_openai_api をパッチする等）。
- セキュリティ上の注意点（RSS の SSRF対策、XML パースの防御、レスポンスサイズ制限）を順守してください。

ライセンス
---------
（ここにプロジェクトのライセンスを明記してください。例: MIT / Apache-2.0 等）

最後に
------
この README はコードベースの主要機能と使い方の概要をまとめたものです。詳細な API 仕様や運用ドキュメント（DataPlatform.md、StrategyModel.md など）が別途ある想定です。必要であれば各モジュールの docstring を基にさらに詳しいガイドを作成します。