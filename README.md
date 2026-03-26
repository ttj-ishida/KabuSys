# KabuSys

日本株向けのデータプラットフォーム＆自動売買支援ライブラリ（モジュール群）。  
ETL・データ品質チェック・ニュース収集・LLM ベースのニュース/レジーム評価・ファクター計算・監査ログなど、量的投資・研究ワークフローで使うユーティリティを提供します。

> 本リポジトリはシステムコンポーネントの集合であり、実際の発注（ブローカー接続）を行うためには別途設定・承認が必要です。バックテスト／研究用途での利用を想定したモジュールも含みます。

## 主な機能
- 環境変数/設定管理（.env の自動ロード、必須変数チェック）
- J-Quants API クライアント（株価・財務・マーケットカレンダー取得、ページネーション/リトライ/レート制御）
- ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- ニュース収集（RSS → raw_news、SSRF 対策・前処理・トラッキング除去）
- ニュース NLP（OpenAI を使った銘柄ごとのセンチメントスコア算出）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価を合成）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC・統計サマリー・Z スコア正規化）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティを確保する DuckDB スキーマ定義・初期化）
- DuckDB ベースの永続化（冪等保存・ON CONFLICT ハンドリング）

## 前提 / 必須環境
- Python >= 3.10（型ヒントの union 表記などを使用）
- pip
- 推奨ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml

※ 実行には外部 API キー（J-Quants, OpenAI, Slack 等）が必要です。環境変数または .env ファイルで設定します。

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu ステーション API パスワード（必須）
- KABUSYS_ENV : "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL : "DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"（デフォルト: INFO）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : 通知用 Slack 設定（必須）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime 等で使用）
- DUCKDB_PATH / SQLITE_PATH : データベースファイルパス（デフォルト設定あり）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動ロードを無効化（テスト用）

設定ファイル（.env）はプロジェクトルートの .env / .env.local を読み込みます。読み込み優先度は OS 環境変数 > .env.local > .env です。

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン／チェックアウト
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージのインストール（例）
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトに setup.py/pyproject があれば:
   pip install -e .
   ```

4. 環境変数を用意
   - プロジェクトルートに .env を作成するか、環境変数として設定してください。
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```
   - テストや CI で自動ロードを抑止したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. データベース格納ディレクトリの作成（必要に応じ）
   ```
   mkdir -p data
   ```

## 使い方（代表的なユースケース）

- DuckDB 接続を作って ETL を実行する（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（特定日のニュースをスコアリング）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定（regime score を market_regime テーブルへ書き込む）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/monitoring.duckdb")
  ```

- 設定アクセス
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.is_live, settings.log_level)
  ```

注意点:
- OpenAI（LLM）を呼ぶ処理は API キーが必要です。テストでは内部の _call_openai_api をモックして使用できます。
- 日付の取り扱いはルックアヘッドバイアスを防ぐ設計になっており、関数は内部で date.today() 等に依存しないようにしています。バックテストでは target_date を明示的に渡すことを推奨します。

## 開発者向けメモ
- .env のパースは堅牢に実装されています（クォート、コメント、export プレフィックス対応）。
- J-Quants クライアントはレート制御（120 req/min）やトークン自動リフレッシュを備えています。
- DuckDB への保存は基本的に ON CONFLICT DO UPDATE（冪等）になっています。
- ニュース収集モジュールは SSRF 対策・gzip サイズ制限・XML 安全処理を行っています。
- LLM 呼び出しはリトライや 5xx の扱いを考慮して実装されています。テストでは _call_openai_api をパッチして擬似応答に差し替えてください。

## ディレクトリ構成（主要ファイル）
（リポジトリ内の src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL 公開インターフェース（ETLResult）
    - calendar_management.py  — 市場カレンダー / 営業日判定
    - news_collector.py       — RSS 収集・正規化・保存
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー / rank
  - research/... (その他ユーティリティ)

（この README に記載のない submodule がさらに存在する可能性があります。実際のツリーはリポジトリの内容を参照してください）

## よくある質問 / トラブルシューティング
- .env を更新したのに反映されない：
  - プロセス開始時に自動ロードされます。テストで自動ロードを無効にしている場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。また .env の場所はプロジェクトルート（.git または pyproject.toml を基準に検索）です。
- OpenAI の呼び出しが失敗する：
  - OPENAI_API_KEY が設定されているか確認。テストでは内部関数をモックして実行できます。
- DuckDB の executemany が空リストで失敗する：
  - 一部の実装で明示的に空リストを避けるチェックが入っています。呼び出し側（スクリプト）でデータ有無を確認してください。

---

以上がこのコードベースの概観と基本的な使い方です。必要であれば、README に以下を追記できます：
- 具体的な .env.example（サンプル）
- CI / テストの実行手順
- より詳細な API リファレンス（主要関数の引数/戻り値の例）
どの情報を追加したいか教えてください。