# KabuSys

日本株向けの自動売買プラットフォーム向けユーティリティ群（データパイプライン、研究用ファクター、ニュースNLP、監査ログ等）。  
このリポジトリはデータ収集／ETL、品質チェック、ファクター計算、LLM を用いたニュースセンチメント評価、ならびに監査（オーダー／約定）スキーマ初期化などを提供します。

注意: 本 README はソースコード (src/kabusys/) に基づく概要と利用手順を記載しています。実際の売買は別途発注／実行モジュールと接続する想定です。

主要な設計方針（抜粋）
- ルックアヘッドバイアスを避ける実装（datetime.today()/date.today() を内部処理で直接参照しない設計）
- DuckDB を主要なオンデバイス DB として利用
- J-Quants API からの差分取得と冪等保存（ON CONFLICT DO UPDATE）
- OpenAI（gpt-4o-mini）によるニュース評価はフェイルセーフ（失敗時は 0 相当で継続）
- セキュリティ配慮（RSS 収集の SSRF 対策、XML パース防御、受信サイズ制限など）

------------------------------------------------------------
目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要ユーティリティの使い方サンプル）
- 環境変数
- ディレクトリ構成
- 注意事項 / 運用上のヒント

------------------------------------------------------------
プロジェクト概要
- 名称: KabuSys
- 目的: 日本株のデータ基盤（ETL / 品質チェック / カレンダー管理 / ニュース収集）および研究用ファクター計算・ニュースNLPによる銘柄スコアリング、監査ログ初期化のユーティリティ。
- 主要技術: Python（3.10+ を想定）、DuckDB、OpenAI API（gpt-4o-mini）、J-Quants API、defusedxml

------------------------------------------------------------
機能一覧
- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（株価、財務、カレンダー、上場情報）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: fetch_rss / 前処理 / raw_news への冪等保存（SSRF 対策・XML 防御）
  - データ品質チェック: 欠損、重複、スパイク、日付不整合の検出（QualityIssue を返す）
  - 監査ログ初期化: init_audit_schema / init_audit_db（オーダー・約定・シグナルの監査テーブルを作成）
  - 汎用統計: zscore_normalize
- ai
  - news_nlp.score_news: ニュースを銘柄別にまとめ、OpenAI でセンチメント評価して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility（モメンタム・バリュー・ボラティリティ）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理: kabusys.config.Settings（.env 自動読み込み、必須設定の検査）

------------------------------------------------------------
セットアップ手順（ローカル / 開発用）
前提
- Python 3.10+
- DuckDB を使用（python パッケージ duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS XML パースの安全化）
- その他標準ライブラリ

手順（概略）
1) 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2) 必要パッケージをインストール
   pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt を用意して pip install -r requirements.txt する想定）

3) 環境変数を設定（.env または環境に直接）
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env / .env.local を置くと自動読み込みされます。
   - 自動ロードを無効にする場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4) DuckDB データベースの配置（デフォルト）
   - duckdb_path のデフォルト: data/kabusys.duckdb
   - 事前にディレクトリを作っておくか、コード側で自動作成される関数（init_audit_db は親ディレクトリを自動作成）を利用

5) 必須外部 API キー準備（下記「環境変数」参照）

------------------------------------------------------------
環境変数（主なもの）
必須
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token() で ID トークンを取得するために使用されます。
- KABU_API_PASSWORD
  - kabu ステーション API のパスワード（発注実行等で必要な場合）。
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
  - Slack 通知に利用する場合。
- OPENAI_API_KEY
  - OpenAI API 呼び出しに使用（news_nlp / regime_detector）。関数の api_key 引数で上書き可能。

任意 / デフォルトあり
- KABUSYS_ENV
  - development / paper_trading / live（デフォルト development）
- LOG_LEVEL
  - DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH
  - デフォルト data/kabusys.duckdb
- SQLITE_PATH
  - 監視 DB など（デフォルト data/monitoring.db）

注意: .env の書式はシェル形式に準拠。config モジュールは .env と .env.local をプロジェクトルートから自動的に読み込みます（既存 OS 環境変数を上書きしない / .env.local は上書き可）。テスト等で自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

------------------------------------------------------------
使い方（代表的な API／実行例）
※ 以下はコード内関数（DuckDB 接続等）を直接呼ぶ例です。実運用では各種 runner / scheduler から呼び出します。

1) DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコア（特定日・ai_scores 書込）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {n_written} scores")
```

3) 市場レジーム判定（ma200 とマクロニュース合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査 DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリがなければ自動作成
# conn を用いて監査テーブルにアクセス可能
```

5) 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
# records は [{ "date":..., "code":..., "mom_1m":..., ...}, ...]
```

6) ETL の部分実行（株価のみ）
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
```

------------------------------------------------------------
ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py                          # .env 自動読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py                      # ニュースセンチメント → ai_scores への保存
  - regime_detector.py               # マーケットレジーム判定（1321 MA200 + マクロセンチメント）
- data/
  - __init__.py
  - calendar_management.py           # 市場カレンダー / 営業日ロジック / calendar_update_job
  - etl.py                           # ETL インターフェース（ETLResult）
  - pipeline.py                      # 日次 ETL パイプライン / 個別 ETL ジョブ
  - stats.py                         # zscore_normalize
  - quality.py                       # データ品質チェック（QualityIssue）
  - audit.py                         # 監査ログスキーマ初期化 / init_audit_db
  - jquants_client.py                # J-Quants API クライアント & DB 保存
  - news_collector.py                # RSS 収集・前処理・SSRF 対策
- research/
  - __init__.py
  - factor_research.py               # calc_momentum / calc_value / calc_volatility
  - feature_exploration.py           # forward returns, IC, factor summary, rank

------------------------------------------------------------
注意事項 / 運用上のヒント
- OpenAI 呼び出しはコストとレート制限に注意。news_nlp はバッチ処理（最大チャンクサイズ等）を行いますが、運用時はコール頻度と API キーの管理を慎重に。
- J-Quants API はレート制限（120 req/min）があるため、jquants_client では固定間隔スロットリングを実装。ETL のスケジュールはこれを考慮してください。
- データ品質チェックを ETL の後に実行し、結果（QualityIssue）を監査ログやアラートに繋げてください。quality.run_all_checks はエラー／警告の詳細を返します。
- ニュース収集では RSS のコンテンツ長・リダイレクト先の検査・XML の安全なパースを行っていますが、外部ソースの変更・不具合に備えたモニタリングが必要です。
- 本ライブラリは売買の意思決定基盤や研究に資するユーティリティ群を提供します。実際の発注や本番稼働の前に十分な検証とリスク管理・監査手順を実施してください。

------------------------------------------------------------
ライセンス / 貢献
- 本 README はソースコードからの情報をもとに生成されています。実運用での利用にあたってはソースコード内コメントおよびプロジェクトのライセンス表記を確認してください。

------------------------------------------------------------
補足（トラブルシューティング）
- .env が読み込まれない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD がセットされているか確認
  - プロジェクトルートに .git または pyproject.toml が存在するか確認（config._find_project_root がこれらを基準に自動検出します）
- OpenAI 呼び出し時に API 例外が発生した場合、news_nlp と regime_detector はフェイルセーフ（部分失敗をスキップして処理継続）する設計です。ログを確認して再試行やリトライの実装を検討してください。

もし README に追加したい実行例や CI / デプロイ手順、あるいは実行スクリプト（例: cron / Airflow の DAG サンプル）があれば教えてください。必要に応じて追記します。