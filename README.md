# KabuSys

日本株向けの自動売買 / データパイプライン用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注／約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量生成・AI ベースのニュースセンチメント評価・市場レジーム判定・監査用スキーマといった機能群をモジュール化して提供するライブラリです。設計上の主要な方針は以下のとおりです。

- Look‑ahead bias を避ける（日時を安易に参照しない、DB クエリで排他条件を利用）
- 冪等性（DB 保存は ON CONFLICT / UPDATE を使用）
- フォールバック・フェイルセーフ（外部 API 障害時は安全に継続）
- API レート制御・リトライ（J-Quants, OpenAI）
- セキュリティ対策（RSS 収集時の SSRF 対策、XML の安全パース等）

---

## 主な機能一覧

- data（データプラットフォーム）
  - J-Quants API クライアント（fetch/save）：株価（日足）、財務、上場情報、マーケットカレンダー
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - カレンダー管理（営業日判定、次/前営業日検索、カレンダー更新ジョブ）
  - ニュース収集（RSS → raw_news、SSRF 対策、前処理）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - 統計ユーティリティ（Zスコア正規化 等）
- ai（AI/NLP）
  - news_nlp: ニュースタイトル/本文をまとめて OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントスコア化し ai_scores テーブルへ書き込み
  - regime_detector: ETF 1321 の 200 日 MA とニュースセンチメントを組み合わせて市場レジーム判定（bull/neutral/bear）を market_regime テーブルへ保存
- research（研究用ユーティリティ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク化ユーティリティ

その他、環境変数や設定値の管理ユーティリティ（kabusys.config）を提供します。

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに union 型などを使用）
- ネットワークからの外部 API（J-Quants, OpenAI）へのアクセスが可能であること

1. リポジトリを取得／配置
   - 開発環境では `pip install -e .` を想定した構成です（setup 配置が必要な場合あり）。

2. 依存パッケージをインストール
   - 必須例（プロジェクトの実際の pyproject.toml / requirements.txt を参照してください）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 他に標準ライブラリを拡張する軽量なパッケージを使っています。実際の環境では pyproject.toml を確認してください。

3. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動でロードされます（自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN : Slack 通知で使う場合のボットトークン
     - SLACK_CHANNEL_ID : Slack チャンネル ID
     - KABU_API_PASSWORD : kabu ステーション API を使う場合のパスワード
   - 任意・デフォルトあり:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/...（デフォルト INFO）
     - KABU_API_BASE_URL : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH : デフォルト data/kabusys.duckdb
     - SQLITE_PATH : デフォルト data/monitoring.db
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=passwd
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベースディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡易例）

以下は主要な利用例（Python スクリプト内での呼び出し例）です。実行時は上で設定した環境変数が適切にセットされていることを前提にしています。

- DuckDB 接続の取得（ファイル DB を利用する例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定しない場合は今日（ただし内部で営業日調整あり）
  print(result.to_dict())
  ```

- ニュースの NLP スコア付け（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数に設定されていれば api_key=None で OK
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査テーブルを別 DB に作る例）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 以降、audit_conn を使って監査ログを挿入・参照
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意:
- OpenAI 呼び出しは API キーを引数で渡すことも可能（テストやキー切替用）。
- 多くの操作は DuckDB 接続（kabusys が期待するスキーマを持つ DB）を前提とします。初期スキーマ作成は用途に応じて実装側で行ってください（audit.init_audit_schema など一部初期化関数あり）。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン（通知用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID（通知用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等用）ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_ENV — environment。development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動で .env をロードしたくない場合に 1 をセット

---

## 設計上の注意点 / 実運用の考慮

- Look‑ahead bias の防止: 多くの関数は target_date を明示的に受け取り、内部で datetime.now()/today() を直接参照しないよう設計されています（バックテストでの公平性維持）。
- 冪等性: J-Quants から取得したデータ保存は ON CONFLICT DO UPDATE で上書きされるため、再実行が安全です。
- API レート制御: J-Quants のレート制限 (120 req/min) を守るレートリミッタを実装済み。OpenAI 呼び出しはリトライや 429 ハンドリングロジックを持ちます。
- フェイルセーフ: LLM や API の異常があっても例外を投げずフォールバックする処理が多く含まれており（例: マクロセンチメントが取得できない場合 0.0 を採用）、パイプライン全体が停止しないように設計されています。
- セキュリティ: RSS 取得では SSRF 防止（ホストのプライベートアドレス検査、リダイレクト検査）、defusedxml を使った XML パース、応答サイズ制限などを実装しています。
- テスト支援: いくつかの内部 API 呼び出し部分は簡単にモック差し替えできるよう実装されています（例: news_nlp._call_openai_api を patch）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
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
      - audit.py
      - stats.py
      - (その他: pipeline から再エクスポートされる ETLResult 等)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（再帰的）: factor / feature utilities...
    - (将来) strategy/, execution/, monitoring/ などのサブモジュールを公開予定（__all__ に名前あり）

---

## 追加情報 / 開発者向けメモ

- 自動で .env を読み込む実装はプロジェクトルート（.git または pyproject.toml のある場所）を探索して .env / .env.local を読み込みます。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化してください。
- OpenAI の呼び出しでは JSON Mode を想定して厳密な JSON を返すようプロンプトを構築していますが、万一の余計なテキスト混入に対しても部分復元（最外の `{...}` を抽出）してパースを試みる保険があります。
- DuckDB の executemany の挙動（空リストがエラーになる等）を考慮した実装があります。DuckDB のバージョン差に注意してください。
- audit.init_audit_db は監査用 DB を別ファイルに作成するユーティリティです。監査ログは削除しない前提で設計されています。

---

この README はコードの主要点をまとめた概要です。より詳細な利用方法やスキーマ、運用フロー（ジョブスケジューリング、監視、Slack 通知の実装方法など）は別途ドキュメント（Design Docs / DataPlatform.md / StrategyModel.md など）が必要になります。必要であれば README に追記する項目（例: Docker 化、CI 設定、デプロイ手順、詳細なスキーマ定義）を教えてください。