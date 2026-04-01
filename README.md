# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ（README）

このリポジトリは「KabuSys」— 日本株のデータETL、ニュースNLP、市場レジーム判定、リサーチ（ファクター計算）や監査ログ管理を行う内部ライブラリ群です。DuckDB をデータストアに用い、J-Quants API や OpenAI（LLM）を利用する設計になっています。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（必要な設定）
- ディレクトリ構成（主要ファイルの説明）
- 注意点 / 設計上のポイント

---

プロジェクト概要
----------------
KabuSys は、日本株向けの次の機能を提供する Python パッケージです。

- J-Quants からの株価・財務・カレンダー等の差分ETLと品質チェック
- RSS ニュース収集と銘柄紐付け（news_collector）
- ニュースを LLM（OpenAI）でスコアリングして ai_scores を作成（news_nlp.score_news）
- ETF（1321）の 200 日 MA とマクロニュースのセンチメントを組み合わせた市場レジーム判定（ai.regime_detector.score_regime）
- 研究用ファクター計算（momentum, value, volatility 等）および統計ユーティリティ
- 監査用スキーマ（signal / order / execution の監査ログ）初期化ユーティリティ
- 設定管理（.env 自動読み込み・環境変数ラッパー）

設計方針のポイント
- ルックアヘッドバイアスを避けるため、各処理は内部で date.today() を不必要に参照せず、明示的な target_date を受け取る設計。
- ETL / データ保存は冪等（ON CONFLICT / INSERT ... DO UPDATE）に配慮。
- 外部API呼び出しはリトライ・レート制御・フォールバック（失敗時は安全側のデフォルト）を実装。
- DuckDB を中心に SQL と Python を組み合わせた処理。

主な機能一覧
--------------
- データ関連（kabusys.data）
  - jquants_client: J-Quants API からデータ取得（価格・財務・カレンダー等）と DuckDB への保存関数
  - pipeline: 日次 ETL パイプライン（run_daily_etl）と個別 ETL
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合等）
  - news_collector: RSS からニュース収集・前処理・DB保存（SSRF 対策、トラッキング除去）
  - audit: 監査ログスキーマの初期化 / audit DB 作成ユーティリティ
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
  - stats: z-score 正規化等の統計ユーティリティ
- AI 関連（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime を生成
- Research（kabusys.research）
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー、ランク化

セットアップ手順
-----------------
前提
- Python 3.10 以上（注: 型注釈で | を使用）
- DuckDB、OpenAI SDK、defusedxml などが必要

例: 仮想環境の作成と必要パッケージのインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要最低限の依存パッケージ（プロジェクトの pyproject.toml や requirements.txt があればそちらを使ってください）
pip install duckdb openai defusedxml
```

.env の準備
- プロジェクトルート（.git または pyproject.toml を探します）に .env / .env.local を置くと、kabusys.config が自動でロードします。
- 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

データベース初期化（監査DBの例）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

使い方（簡単なコード例）
-----------------------

1) DuckDB 接続
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path はデフォルト "data/kabusys.duckdb"
conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（J-Quants トークンは .env 経由で自動利用可）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニューススコア（ai_scores への書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY から取得されます
n_written = score_news(conn, target_date=date(2026,3,20))
print("書込み銘柄数:", n_written)
```

4) 市場レジーム判定（market_regime テーブルへ書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, target_date=date(2026,3,20))
print("score_regime result:", res)
```

5) ファクター計算・正規化例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize
from datetime import date

d = date(2026,3,20)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# 例えば mom の列を z-score 正規化
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

環境変数（設定）
-----------------
kabusys.config.Settings 経由でアクセスします。主な環境変数:

必須（少なくとも使用する機能に応じて設定）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行に必要）
- OPENAI_API_KEY: OpenAI 呼び出し（news_nlp, regime_detector）に必要（関数引数で上書き可）
- KABU_API_PASSWORD: kabuステーション API を使う場合
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合

その他（デフォルトあり）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PID_FILE_PATH: デフォルト data/execution.pid
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視の閾値
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml を検出）に .env があれば自動で読み込みます。
- 読み込み順: OS 環境 > .env.local > .env（.env.local は上書き可）
- export KEY=val 形式やクォート、inline コメントなどに対応したパーサが組み込まれています。

ディレクトリ構成（主なファイル）
------------------------------
（実装対象: src/kabusys/ 以下）

- __init__.py
  - パッケージメタ情報（__version__）とサブパッケージの __all__。

- config.py
  - 環境変数の自動読み込み・Settings クラス（アプリ設定のラッパー）。

- ai/
  - news_nlp.py : ニュースを LLM でセンチメント評価し ai_scores に書き込む。batch 化・リトライ・レスポンス検証を実装。
  - regime_detector.py : ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime を書き込む。
  - __init__.py

- data/
  - pipeline.py : ETL の主要ロジック（run_daily_etl 等）と ETLResult クラス。
  - jquants_client.py : J-Quants API クライアント（取得・保存関数・認証）。レート制御・リトライ実装。
  - news_collector.py : RSS 取得・前処理・SSRF 対策・raw_news 保存ロジック。
  - quality.py : データ品質チェック（欠損・重複・スパイク・日付不整合）。
  - calendar_management.py : market_calendar の管理と営業日判定（next/prev/get_trading_days など）。
  - audit.py : 監査ログ（signal_events / order_requests / executions）の DDL と初期化ユーティリティ。
  - stats.py : zscore_normalize 等の統計ユーティリティ。
  - etl.py : pipeline.ETLResult の再エクスポートなど。

- research/
  - factor_research.py : Momentum/Value/Volatility 等のファクター計算（DuckDB SQL 利用）。
  - feature_exploration.py : 将来リターン計算、IC（Spearman）計算、統計サマリー、rank 関数。
  - __init__.py

主な公開関数（ざっくり）
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes / fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar
- kabusys.data.news_collector.fetch_rss(...)
- kabusys.ai.news_nlp.score_news(...)
- kabusys.ai.regime_detector.score_regime(...)
- kabusys.data.audit.init_audit_db / init_audit_schema
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank

注意点 / 実運用上のポイント
------------------------
- OpenAI / J-Quants API の利用にはそれぞれの API キーが必要です。課金・レート制限に注意してください。
- ETL や LLM 呼び出しはネットワーク依存で失敗する可能性があるため、ログ・リトライ・フォールバック（失敗時はスコア 0.0 等）の挙動を理解の上で実装してください。
- DuckDB の executemany に空リストを渡すと問題となるバージョンがあるため、実装内で空チェックを行っています（この点は DB ライブラリのバージョンにより振る舞いが異なる可能性があります）。
- news_collector は RSS の HTML/XML を扱うため、defusedxml を利用して XML 関係攻撃対策を行っています。外部から受け取るデータの扱いは慎重に。
- 監査ログ（audit）は消さずに蓄積する前提なので、ディスクサイズ等の運用監視が必要です。

ライセンス・貢献
----------------
- 本 README はコードベースに基づくドキュメントです。実際のライセンスはリポジトリの LICENSE ファイルを参照してください。
- 貢献や不具合報告はプルリクエスト / issue を通じてお願いします。

---

必要であれば、さらに具体的な実行例（systemd タスクや cron ジョブでの ETL スケジュール、Slack 通知実装例、テスト／CI の説明）を追加できます。どの項目の詳細が必要か教えてください。