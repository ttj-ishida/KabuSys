KabuSys — 日本株自動売買 / データプラットフォーム
========

概要
----
KabuSys は日本株向けのデータパイプライン、リサーチ、AIによるニュース解析、監査ログ、および戦略/発注周りの基本的なインフラを提供する Python パッケージです。主に以下用途を想定しています。

- J-Quants からのデータ ETL（株価日足、財務、JPX カレンダー）
- RSS ベースのニュース収集と LLM を使った銘柄センチメントスコアリング
- 市場レジーム判定（ETF とマクロニュースを組み合わせた手法）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）を DuckDB で管理
- データ品質チェック（欠損・スパイク・重複・日付整合性）

主な機能一覧
-------------
- 環境変数/設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可能）
  - 必須環境変数の取得ラッパー（設定エラー時は例外）
- ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API から差分取得、DuckDB へ冪等保存（ON CONFLICT）
  - レート制御・リトライ・トークン自動リフレッシュ対応
  - run_daily_etl によりカレンダー→株価→財務→品質チェックを順次実行
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、前処理、安全対策（SSRF / レスポンスサイズ / defusedxml）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（kabusys.ai.news_nlp）
  - gpt-4o-mini を用いた銘柄ごとのセンチメントスコア生成（JSON Mode）
  - バッチ送信、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して daily レジーム判定
  - LLM 呼び出しのリトライ・フェイルセーフ実装
- リサーチ（kabusys.research）
  - ファクター計算（momentum/value/volatility）、forward returns、IC 計算、統計サマリ
  - zscore 正規化ユーティリティ（kabusys.data.stats）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの DDL・インデックス・初期化ユーティリティ
  - init_audit_db により監査専用 DuckDB を作成可能
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合などを検出し QualityIssue リストで返却

セットアップ手順
----------------
前提
- Python 3.10 以上（型記法に | を使用）
- duckdb, openai, defusedxml などの依存ライブラリ（下記参照）

1. 仮想環境作成（任意）
- python -m venv .venv
- source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
- pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

3. プロジェクトルートに .env を用意
- このパッケージはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）から .env と .env.local を自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化できます）。

主な環境変数（最低限必要なもの）
- JQUANTS_REFRESH_TOKEN=...    （J-Quants 用リフレッシュトークン）
- OPENAI_API_KEY=...          （OpenAI API キー）
- KABU_API_PASSWORD=...       （kabuステーション API パスワード、必要に応じて）
- SLACK_BOT_TOKEN=...         （Slack 通知を行う場合）
- SLACK_CHANNEL_ID=...        （Slack 通知先）
- KABUSYS_ENV=development|paper_trading|live  （実行環境）
- LOG_LEVEL=INFO|DEBUG|...    （ログレベル、任意）
- DUCKDB_PATH=data/kabusys.duckdb  （DuckDB ファイルパス、既定値）
- SQLITE_PATH=data/monitoring.db   （SQLite 監視用 DB、既定値）

例（.env）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- KABUSYS_ENV=development
- LOG_LEVEL=DEBUG

4. データベースディレクトリ作成（必要なら）
- mkdir -p data

使い方（主要な例）
------------------

1) DuckDB 接続を作って日次 ETL を実行する
- Python から実行する例:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- run_daily_etl は市場カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェックを実行して ETLResult を返します。

2) ニュースセンチメントを算出して ai_scores に書き込む
- from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で環境変数を使用

3) 市場レジームスコア算出
- from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

4) 監査ログ DB の初期化
- from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続

5) 研究用ユーティリティの呼び出し（ファクター計算等）
- from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))

注意点・運用上のヒント
- OpenAI 呼び出しは課金対象かつレイテンシがあるため、デバッグでは API 呼び出しをモックすることを推奨します（モジュール内の _call_openai_api はテストでパッチ可能です）。
- config モジュールは自動で .env を読み込みます。ユニットテストなどで自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB への大量インサートは executemany を利用しています。DuckDB バージョン差分に注意（コード中で互換性対策あり）。
- J-Quants API のレート制限（120 req/min）や OAuth トークンの自動リフレッシュに対応していますが、実運用では id_token の有効期限やレートを監視してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                — パッケージ初期化、公開 API
- config.py                  — 環境変数 / 設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py              — ニュースの LLM スコアリング（score_news）
  - regime_detector.py       — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（fetch / save）
  - pipeline.py              — ETL パイプライン（run_daily_etl など）
  - etl.py                   — ETLResult の再エクスポート
  - news_collector.py        — RSS 収集と前処理
  - calendar_management.py   — 市場カレンダー操作（営業日判定等）
  - stats.py                 — 汎用統計ユーティリティ（zscore_normalize）
  - quality.py               — データ品質チェック
  - audit.py                 — 監査ログ DDL / 初期化
- research/
  - __init__.py
  - factor_research.py       — モメンタム/ボラティリティ/バリュー等
  - feature_exploration.py   — forward returns, IC, factor summary, rank
- monitoring/ (パッケージ内で言及はあるが実装はここに拡張可能)
- execution/, strategy/, monitoring/ などは将来的な発注・戦略・監視用モジュールの公開点として __all__ に含まれます。

補足（設計方針のポイント）
-------------------------
- Look-ahead bias を避けるため、内部処理は target_date を明示して過去のデータのみ参照する設計です（datetime.today() を直接参照しない）。
- DB 操作は冪等性（ON CONFLICT DO UPDATE）を重視し、部分失敗時のデータ保護を行います。
- 外部 API 呼び出しはエラー許容（フェイルセーフ）で設計されており、API 失敗時はスコアを 0 にフォールバックする等の保護があります。
- セキュリティ: news_collector では SSRF 対策、XML の defusedxml 利用、レスポンスサイズ制限などを行っています。

問い合わせ / 開発メモ
-------------------
- テストのしやすさを考慮して API 呼び出しや時間依存部分は差し替え可能な実装にしています（ユニットテストではモックを推奨）。
- 本 README はコードベースに基づく概要と利用方法を記載しています。詳細は各モジュールの docstring を参照してください。

---
必要に応じて README に追加したい内容（例）
- requirements.txt の具体的な内容
- CI / デプロイ手順（コンテナ化、スケジューラ設定）
- Slack 通知の使い方や kabuステーション連携のサンプル
ご希望があればこれらを追記します。