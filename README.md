KabuSys — 日本株自動売買プラットフォーム
====================================

概要
----
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買サブシステム群です。  
主に以下の目的を持つモジュール群を提供します。

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- ETL（差分取得・保存・品質チェック）パイプライン
- ニュース収集・NLP（OpenAI）によるセンチメントスコア
- 市場レジーム判定（マクロセンチメント + ETF MA）
- ファクター計算・特徴量探索（リサーチ用）
- 監査ログ（シグナル → 発注 → 約定のトレース用 DB スキーマ）
- 各種ユーティリティ（カレンダー管理・統計関数等）

設計上の留意点（主要）
- ルックアヘッドバイアスを防ぐ設計（内部で date.today()/datetime.today() を直接参照しない等）
- DuckDB を中心としたローカル DB 保存（冪等な保存ロジックを採用）
- 外部 API 呼び出し（J-Quants / OpenAI）はリトライ・レート制御を実装
- ニュース収集は SSRF・XML ボム対策を実装

主な機能一覧
----------------
- data.jquants_client: J-Quants API クライアント（fetch / save / 認証・レート制御）
- data.pipeline: 日次 ETL 実行(run_daily_etl) と個別 ETL ジョブ
- data.quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
- data.calendar_management: JPX カレンダーヘルパ（営業日判定 / next/prev 等）
- data.news_collector: RSS 収集・前処理（SSRF対策、正規化、raw_news 保存想定）
- data.audit: 監査ログ用のスキーマ定義・初期化（signal_events / order_requests / executions）
- ai.news_nlp: ニュースを OpenAI でスコアリングして ai_scores に書き込む（score_news）
- ai.regime_detector: ETF 1321 の MA とマクロニュースの LLM スコアを合成して market_regime を算出（score_regime）
- research.*: ファクター計算（momentum/value/volatility）・特徴量探索・IC 計算等
- config: 環境変数/設定の読み込みと管理（自動 .env ロード機能あり）

セットアップ手順
----------------

1. Python と仮想環境
   - Python 3.10+ を推奨
   - 仮想環境を作成してアクティベートしてください
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必須（代表例）:
     - duckdb
     - openai
     - defusedxml
   - pip install duckdb openai defusedxml
   - もしパッケージ化されたプロジェクトであれば:
     - pip install -e .

   （リポジトリに requirements.txt / pyproject.toml があればそちらを使用してください）

3. 環境変数 / .env の準備
   - プロジェクトルート（.git / pyproject.toml がある場所）に .env を置くと自動で読み込まれます。
     自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
     - KABU_API_PASSWORD : kabuステーション API 用パスワード（発注等に使用）
   - OpenAI / LINE 等（用途に応じて）:
     - OPENAI_API_KEY : OpenAI API キー（ai.score_news / regime_detector で使用）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用途
   - DB パス（デフォルト値あり）:
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
   - 実行環境フラグ:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

使い方（簡単な利用例）
--------------------

- DuckDB 接続を作って日次 ETL を走らせる

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーが環境にあるか引数で渡す）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None => env OPENAI_API_KEY を参照
  print("scored", n_written)
  ```

- 市場レジームスコア算出

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査 DB 初期化（別ファイルに監査用 DB を作る）

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

設定詳細（主な環境変数）
-----------------------
- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) : kabuステーション API のパスワード
- OPENAI_API_KEY (AI 機能を使う場合必須) : OpenAI の API キー
- KABUSYS_ENV : "development" / "paper_trading" / "live"（検証用フラグ）
- LOG_LEVEL : ログレベル（デフォルト INFO）
- DUCKDB_PATH : DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLLITE_PATH : 監視用 sqlite パス（default: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env 読み込みを抑止

注意点 / 実運用への留意
-----------------------
- OpenAI 呼び出しはコストがかかり、レート制限もあるためバッチ単位・バッチサイズに注意してください。
- J-Quants API に対するレート制御とリトライは実装されていますが、API キーや権限が必要です。
- ETL や AI スコアリング処理は「ルックアヘッドバイアス」を意識した実装方針になっています。バックテストで使用する場合、必ず target_date を明示的に渡して過去情報のみで再現可能な形で利用してください。
- news_collector モジュールは RSS 取得時の SSRF / XML Bomb 対策を持っていますが、実行環境のネットワーク権限やタイムアウト設定を適切に管理してください。

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py — パッケージ初期化（version）
- config.py — 環境変数と設定管理（自動 .env ロード、Settings クラス）

src/kabusys/ai/
- __init__.py
- news_nlp.py — ニュース NLP（score_news）
- regime_detector.py — 市場レジーム判定（score_regime）

src/kabusys/data/
- __init__.py
- jquants_client.py — J-Quants API クライアント（fetch/save/get_id_token）
- pipeline.py — 日次 ETL と個別 ETL ジョブ、ETLResult
- quality.py — データ品質チェック
- stats.py — 統計ユーティリティ（zscore_normalize）
- calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
- news_collector.py — RSS 収集・正規化
- audit.py — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- etl.py — pipeline.ETLResult の再エクスポート

src/kabusys/research/
- __init__.py
- factor_research.py — momentum/value/volatility 計算
- feature_exploration.py — 将来リターン / IC / 統計サマリー 等

ログとモニタリング
-------------------
- settings.log_level でログレベルを制御
- PID ファイルや kill flag など監視用設定は config.Settings で管理（pid_file_path / kill_flag_path 等）

貢献・拡張
----------
- モジュールは小さな単位で責務分離されています。新規の ETL 追加・品質チェック・戦略ロジックを追加する際は既存の conn（DuckDB 接続）を受け取る形で実装すると統合が容易です。
- テストでは設定の自動 .env ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。また OpenAI 呼び出しやネットワークはモック可能な設計になっています（モジュール内の _call_openai_api など）。

ライセンス
---------
- このリポジトリにライセンス情報が含まれていない場合は、チームのポリシーに従って追加してください。

最後に
------
この README はコード内の docstring と実装に基づいて作成しています。実行時には必須環境変数や外部サービスの認証情報が必要です。開発・本番環境それぞれで安全にキー管理・ネットワーク設定を行ってください。必要ならば、サンプル .env.example や運用手順（cron/airflow 等での定期実行）を別ドキュメントとして追加することを推奨します。