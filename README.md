KabuSys — 日本株自動売買基盤（README 日本語）
====================================

概要
----
KabuSys は日本株のデータ取得 / ETL、ニュースベースの AI スコアリング、ファクター計算、監査ログ、マーケットカレンダー管理などを含む自動売買プラットフォームのコアライブラリです。DuckDB をデータ層に用い、J-Quants や RSS、OpenAI（LLM）等と連携してデータパイプラインやリサーチ処理、オーダー監査ログの初期化を行います。

主な特徴
--------
- データ ETL（J-Quants 経由で株価・財務・マーケットカレンダーを差分取得・保存）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策・トラッキング除去・gzip 対応）
- ニュースを LLM（gpt-4o-mini）でセンチメント評価して銘柄別スコア作成（ai_scores）
- マクロニュースと ETF（1321）200日移動平均乖離を組み合わせた市場レジーム判定
- 監査ログ（signal_events, order_requests, executions）の冪等初期化ユーティリティ
- 研究用ユーティリティ（ファクター計算、forward returns、IC、Z-score 正規化 等）
- 環境変数 (.env) を自動で読み込む設定管理（自動読み込みは無効化可能）

動作要件（目安）
----------------
- Python 3.10 以上（型ヒントや | 型合成を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで多くの処理を実装）

インストール
------------
（パッケージ化されていれば pip install . などで導入できます。ローカルで開発する場合の例）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

環境変数 / .env
---------------
プロジェクトは .env / .env.local をプロジェクトルートから自動ロードします（OS 環境変数が優先）。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主に使用する環境変数（README 用一覧）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB のファイルパス（省略可、デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（省略可、デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（省略時 development）
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | ... )
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しに使用）

セットアップ手順（簡易）
---------------------
1. リポジトリを取得
   - git clone <repo>

2. 仮想環境と依存導入（上記を参照）

3. .env を作成（.env.example を参照して必要なキーを設定）

4. 初期 DB ファイル（必要なら）および監査 DB を準備
   - デフォルトの DuckDB ファイルは data/kabusys.duckdb（settings.duckdb_path）
   - 監査ログ専用 DB を作る場合は下記 API を使用

使い方（プログラムからの呼び出し例）
---------------------------------

以下は主要な API の利用例（Python スクリプト）です。各関数は duckdb 接続を受け取り処理します。

1) DuckDB 接続を作成して ETL を実行する（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# DuckDB ファイルへ接続（デフォルトパスは settings.duckdb_path）
conn = duckdb.connect("data/kabusys.duckdb")

# ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの AI スコアリング（指定日分）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_scored = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print(f"scored: {n_scored}")
```

3) 市場レジームスコア計算（ETF 1321 とマクロニュース合成）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

4) 監査ログテーブルの初期化（新規 DB 作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成されます
```

主要モジュールと API（概要）
-------------------------
- kabusys.config
  - settings: 環境設定読み出し（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）
  - 自動でプロジェクトルートの .env/.env.local を読み込む（無効化可能）

- kabusys.data
  - pipeline.run_daily_etl: 日次 ETL の総合エントリポイント
  - jquants_client: J-Quants API のフェッチ / DuckDB 保存ユーティリティ（fetch_* / save_*）
  - news_collector.fetch_rss: RSS 取得と前処理
  - calendar_management: 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）、calendar_update_job
  - quality: データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - audit: 監査スキーマ初期化（init_audit_schema, init_audit_db）
  - stats.zscore_normalize: Zスコア正規化ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースを LLM で銘柄別にスコア化して ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書き込む

- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value: ファクター計算
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank: 研究用解析関数
  - zscore_normalize を再エクスポート

設計上の注意点 / 運用メモ
------------------------
- Look-ahead bias を避ける設計（関数は内部で date.today() を直接参照せず、target_date を受け取る設計）
- OpenAI 呼び出し部分にはリトライとフォールバック（失敗時は 0.0 で継続）を実装
- J-Quants API との通信はレート制限（120 req/min）と再試行ロジックを組み込み済み
- save_* 系関数は冪等（ON CONFLICT DO UPDATE）で再処理可能
- news_collector は SSRF 対策・受信サイズ制限・XML の安全パース（defusedxml）などを備える
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、空時は実行しない処理を各所で実装

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py (ETLResult 再エクスポート)
  - pipeline.py (run_daily_etl 等)
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記以外に strategy / execution / monitoring 等のパッケージを __all__ で公開する設計が見られますが、今回の抜粋に全コードは含まれていません）

トラブルシューティング
-----------------------
- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定していないか確認。
  - プロジェクトルートの判定は .git または pyproject.toml を基準に行われます。パッケージとして配布している場合、手動で環境変数を設定してください。

- OpenAI 呼び出し失敗
  - OPENAI_API_KEY を確認。API の一時的障害は内部でリトライされます。失敗時はニューススコアやマクロセンチメントを 0 にフォールバックするため処理は継続しますが、結果の妥当性を運用側で確認してください。

- DuckDB 関連のエラー
  - executemany に空リストを渡さない等の実装上の注意があるため、DB のバージョン差異でエラーが出る場合は DuckDB のバージョンを合わせてください。

最後に
------
この README はコードベース（src/kabusys）から主要 API と設計意図を抜粋してまとめたものです。各関数の詳細な振る舞いや追加のオプションは該当モジュールの docstring を参照してください。必要であれば README にサンプルスクリプトや CI / デプロイ手順の追記を行います。