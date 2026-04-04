# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants からのデータ取得（ETL）、ニュースの収集・NLP スコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）、市場レジーム判定などを含むモジュール群を提供します。

主に DuckDB をデータストア、OpenAI（gpt-4o-mini 等）をニュース解析の LLM、J-Quants API をデータソースとして想定しています。

---

## 主な機能

- ETL（データ取得 / 差分保存 / 品質チェック）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・冪等保存
  - 品質チェック（欠損・スパイク・重複・日付不整合など）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキングパラメータ除去、文字列正規化）
- ニュース NLP（OpenAI）による銘柄別センチメントスコアリング（ai_scores への書き込み）
- 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュースセンチメント → bull/neutral/bear）
- 研究用ユーティリティ（モメンタム / バリュー / ボラティリティ等のファクター計算、将来リターン、IC 計算、Zスコア正規化）
- 監査ログ（signal_events, order_requests, executions）のスキーマ初期化ユーティリティ（冪等）
- J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ対応）
- 環境変数設定管理（.env / .env.local の自動読み込み、無効化フラグあり）

---

## 動作環境 / 前提

- Python >= 3.10（型ヒントに | 演算子を使用）
- 必要な主要依存（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）
- J-Quants リフレッシュトークン（環境変数または .env）

（実際のインストール要件はプロジェクトの requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン

2. 仮想環境を作成・有効化（推奨）

   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存をインストール

   例（pip）:
   - pip install duckdb openai defusedxml

   またはプロジェクトに pyproject.toml / requirements.txt があればそれに従ってください。

4. 環境変数の設定

   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込み順: OS 環境 > .env.local > .env）。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（一部、省略時デフォルトあり）:

   - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（news_nlp/regime_detector で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視関連
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

   例 .env（参考）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_pass
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（監査用 DuckDB など）

   監査ログスキーマを初期化する簡単な例:

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は DuckDB 接続（初期化済み）
   ```

---

## 使い方（主要な例）

以下は簡単な Python からの呼び出し例です。実行前に環境変数等を設定してください。

- DuckDB 接続の用意

  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（run_daily_etl）

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

  run_daily_etl は市場カレンダー ETL → 株価ETL → 財務ETL → 品質チェック の順で実行し、ETLResult を返します。

- ニュースセンチメントスコア（銘柄別）を生成して DB に書き込む

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")
  ```

- 市場レジームスコア計算（ETF 1321 + マクロニュース）

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（既存 DB に付与）

  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- 設定値の参照

  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## 主要モジュールとディレクトリ構成

（リポジトリ内の src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定の読み込みと Settings クラス（.env 自動読み込み機能あり）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集合を OpenAI で評価し ai_scores に書き込む
    - regime_detector.py
      - ETF 1321 の MA 乖離 + マクロニュースセンチメントから市場レジームを判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レートリミット、リトライ、トークン管理）
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等
      - ETLResult データクラス
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 収集、前処理、SSRF 対策、raw_news 保存
    - quality.py
      - 品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - calendar_management.py
      - market_calendar の管理、営業日判定（is_trading_day / next_trading_day 等）
    - audit.py
      - 監査ログ（シグナル→発注→約定）スキーマ定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py
      - 将来リターン / IC / 統計サマリー 等
  - ai、data、research の間は設計上可能な限り疎結合を保つように実装されています。

---

## 実装上の注意点・運用メモ

- .env の自動読み込み
  - 実行時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し、.env → .env.local の順で読み込みます。
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利です）。
- Look-ahead bias 防止
  - AI モジュールや ETL は日付に対して look-ahead を生まないよう設計されています（内部で date.today() を不用意に参照しない、データ取得は target_date 未満等）。
- API キーの扱い
  - OpenAI API は score_news / regime_detector の引数で直接渡せます（テスト時の差替えや複数キー運用に便利）。未指定時は環境変数 OPENAI_API_KEY を使用します。
- J-Quants クライアント
  - レート制限（120 req/min）や 401 リフレッシュ、ページネーション処理などを実装済みです。
- DuckDB 用の executemany 空リスト制約等に配慮した実装がなされています（DuckDB バージョン差分への互換性確保）。

---

## トラブルシューティング / テストヒント

- OpenAI 呼び出しや外部 API 呼び出しはリトライやフェイルセーフ設計です。ユニットテストでは以下の関数をモックできます：
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
  - kabusys.data.news_collector._urlopen
  - kabusys.data.jquants_client._request（あるいは get_id_token / fetch_* をモック）
- DuckDB のファイルがロックされる場合は接続を閉じる、もしくは ":memory:" を使ったテストを検討してください。
- ETL 実行後に品質チェック結果（ETLResult.quality_issues）を確認し、重大な品質エラーがあるかどうかを判断してください。

---

この README はコードベースから得られる情報に基づいた導入ガイドです。運用ポリシー（実際の発注、リスク管理、LINE 通知・kabu ステーション連携など）については別途運用ドキュメントを参照してください。必要であれば README を実際の setup.py / pyproject / CI と整合させた形に更新できます。