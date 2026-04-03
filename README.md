# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注・約定トレース）などを含みます。

---

## 主な特徴

- データ取得・ETL
  - J-Quants API から株価（日足）、財務情報、JPX カレンダーを差分取得・冪等保存
  - DuckDB を用いたローカルデータベース運用
  - 差分更新 / バックフィル / ページネーション / レートリミット対応
- データ品質チェック
  - 欠損、重複、スパイク、日付整合性チェックを実装（QualityIssue を返す）
- ニュース収集 & NLP
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）スコアリング
  - マクロニュースを使った市場レジーム判定（ETF 1321 の MA + LLM センチメントの合成）
- リサーチ機能
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化
- 監査ログ / トレーサビリティ
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
  - 発注フローの UUID ベーストレーシングを想定

---

## 機能一覧（モジュール抜粋）

- kabusys.config
  - 環境変数の自動ロード（プロジェクトルートの .env / .env.local）と設定値取得
- kabusys.data.jquants_client
  - J-Quants API クライアント、fetch/save 周りの実装
- kabusys.data.pipeline, kabusys.data.etl
  - 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- kabusys.data.quality
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- kabusys.data.news_collector
  - RSS 取得・前処理・raw_news への保存補助
- kabusys.ai.news_nlp
  - ニュースをまとめて LLM へ送り、銘柄ごとの ai_score を ai_scores テーブルへ書き込む（score_news）
- kabusys.ai.regime_detector
  - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定（score_regime）
- kabusys.research
  - factor_research (calc_momentum / calc_value / calc_volatility)
  - feature_exploration (calc_forward_returns / calc_ic / factor_summary / rank)
- kabusys.data.audit
  - 監査テーブルの初期化（init_audit_schema / init_audit_db）
- kabusys.data.stats
  - zscore_normalize（クロスセクション Z スコア）

---

## セットアップ手順

前提
- Python 3.10 以上（型注記に | None を用いているため）
- DuckDB を利用（ローカルファイルに保存）

1. リポジトリをクローン / 作業ディレクトリへ移動

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（プロジェクトに pyproject.toml があればそれを利用）
   - 最低依存（例）:
     - duckdb
     - openai
     - defusedxml
   - pip で一括:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発ツールやテストがある場合は追加でインストールしてください。

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます（.env.local は優先上書き）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主な環境変数（必須 / 推奨）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY (必須 for LLM 機能) — OpenAI API キー（score_news / score_regime などで使用）
     - KABU_API_PASSWORD — kabu API を使う場合のパスワード
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知連携を使う場合
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   - 例 .env（簡易）
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```

5. データベース初期化（監査ログを使う場合）
   - 監査 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存の DuckDB 接続に監査スキーマを追加する:
     ```python
     from kabusys.data.audit import init_audit_schema
     # conn: duckdb.connect(...)
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（代表的な例）

- 日次 ETL を実行する（DuckDB に保存）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを取得して ai_scores を更新（対象日）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print("written:", n_written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- ファクター計算（リサーチ）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

注意点:
- OpenAI 呼び出しはネットワーク/料金に依存します。テスト時は各モジュールにある `_call_openai_api` をモックする設計になっています（unittest.mock.patch）。
- J-Quants API はレート制限があるため、jquants_client 内の RateLimiter が自動制御します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - quality.py
  - stats.py
  - calendar_management.py
  - news_collector.py
  - audit.py
  - (その他 ETL/補助モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring, execution, strategy など（パッケージ API で __all__ に含まれる可能性あり）

（上記はリポジトリ内の主要モジュール抜粋です。詳細はソースツリーを参照してください。）

---

## 開発・テストに関するメモ

- 環境変数の自動ロードは .env / .env.local をプロジェクトルートから探して行います。テストで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しはエクスポネンシャルバックオフやステータス別のハンドリングが組み込まれていますが、テストではネットワークを叩かないようにモックしてください（例: unittest.mock.patch）。
- DuckDB の executemany はバージョン差分で挙動差があるため、コード内で空リスト渡しを避けるガードが入っています。テスト時は同様の注意を。

---

## ライセンス / 貢献

本 README はコードベースの説明です。実際のリポジトリに LICENSE ファイルがあればそちらを参照してください。  
バグ修正・機能追加の貢献はプルリクエストを歓迎します。コードスタイルやテストを整えてから送ってください。

---

この README はソース内 docstring と実装方針に基づいて作成しています。より詳細な利用例やセットアップ、自動化ジョブ（cron/systemd など）に関するテンプレートが必要であれば追加で作成します。