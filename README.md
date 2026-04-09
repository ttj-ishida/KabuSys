# KabuSys

日本株向けの自動売買 / データパイプライン / 研究用ユーティリティ群です。  
DuckDB をデータストアに、J-Quants API でマーケットデータを取得し、OpenAI（gpt-4o-mini）を用いたニュース NLP や市場レジーム判定、ファクター計算や品質チェックなどを提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「堅牢なエラー処理（リトライ/フォールバック）」です。

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API からの日次株価（OHLCV）、財務データ、JPX カレンダー取得（ページネーション対応、レートリミット対応、トークン自動リフレッシュ）
  - 差分取得 / バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
  - raw_prices / raw_financials / market_calendar への冪等保存

- ニュース収集・NLP
  - RSS フィード取得（SSRF対策、トラッキングパラメータ除去、受信上限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（ai_scores テーブルへ書き込み）

- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルと初期化ユーティリティ（DuckDB）

- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計要約、Z スコア正規化

- その他
  - 環境変数管理（.env 自動読み込みロジック、保護された OS 環境変数）
  - プロジェクトルート判定（.git / pyproject.toml を基準）

---

## セットアップ手順

前提
- Python 3.9+（typing 記法を利用）
- ネットワークアクセス（J-Quants, OpenAI, RSS ソース）可能な環境

1. リポジトリをクローンしてパッケージをインストール（開発時）
   ```bash
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 必要な外部パッケージ（主な例）
   - duckdb
   - openai
   - defusedxml
   これらは pyproject.toml / requirements に含めてください。手動インストール例:
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（優先度: OS env > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   主要な環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須 for ETL）
   - OPENAI_API_KEY: OpenAI API キー（必要な AI 機能を使う場合）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注関連が存在する場合）
   - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
   - LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視等で使う SQLite（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE: paper_trading 用のモック約定モード（instant/partial/never/reject）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（基本例）

ここでは Python スクリプトや REPL から呼び出す代表的な関数例を示します。

- 設定値の取得
  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.env)          # development / paper_trading / live
  ```

- DuckDB 接続を作成して日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"wrote {written} codes")
  ```

- 市場レジームを判定して market_regime に保存
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB を初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが設定されます
  ```

- 研究用ファクター計算の実行（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点
- AI 系関数（score_news / score_regime）は OpenAI API キーが必要です。引数で直接渡すこともできます。
- すべての関数はルックアヘッドバイアスを避けるため、内部で datetime.today() を参照しない設計です。必ず target_date を明示的に渡すか、許容されている挙動を確認してください。

---

## 主要モジュールの説明（短く）

- kabusys.config
  - .env 自動読み込み、Settings による環境変数ラッパー

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline: ETL パイプライン（run_daily_etl、個別 ETL）
  - quality: データ品質チェック
  - calendar_management: JPX カレンダー管理（営業日判定等）
  - news_collector: RSS 収集と raw_news 保存
  - audit: 監査ログテーブルの初期化

- kabusys.ai
  - news_nlp: ニュースを LLM でスコア化（ai_scores への書込み）
  - regime_detector: ETF MA とマクロニュースを用いた市場レジーム判定

- kabusys.research
  - factor_research: モメンタム / バリュー / ボラティリティ等の計算
  - feature_exploration: 将来リターン / IC / 統計サマリー 等

---

## ディレクトリ構成（主要ファイル）

下記は本リポジトリの主要なディレクトリ/ファイル構成です（抜粋）:

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
      - quality.py
      - stats.py
      - calendar_management.py
      - news_collector.py
      - audit.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - その他 research ユーティリティ
    - research/
    - ai/
    - data/

（実際のファイルツリーはリポジトリのルートで `tree src/kabusys` 等で確認してください）

---

## 運用上の注意・ベストプラクティス

- 環境変数管理
  - `.env`/.env.local に機密情報を保存する場合はファイルのアクセス制御に注意してください（git 管理しない等）。

- API レート制御 / リトライ
  - J-Quants ではモジュール内で固定間隔スロットリングおよびリトライを実装しています。大規模バッチでの利用時はさらに呼び出し間隔に配慮してください。

- テスト性
  - OpenAI 呼び出しやネットワーク I/O はモジュール内で呼び出し関数が分離されており、ユニットテスト時に差し替え（モック）しやすい設計になっています（例: kabusys.ai.news_nlp._call_openai_api を patch）。

- 監査性
  - order_requests の order_request_id は冪等キーとして利用し、二重発注を防ぐ運用を推奨します。

---

## トラブルシューティング / よくある質問

- .env が読み込まれない
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストや別ディレクトリ実行の場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で環境変数をセットしてください。

- OpenAI の応答が不安定
  - モジュール内で 5xx・タイムアウト・429 に対して指数バックオフでリトライする実装があります。運用では API クォータやレートを監視してください。

- DuckDB のスキーマがない / テーブルエラー
  - ETL 実行前に期待されるテーブル（raw_prices, raw_financials, market_calendar 等）が存在するか確認してください。audit.init_audit_db 等は必要に応じてスキーマを初期化します。

---

README は以上です。必要であれば以下の追加を提供します:
- フル API リファレンス（各関数の引数と返り値）
- 実運用用の systemd / cron 例（ETL バッチの定期実行）
- .env.example のテンプレート

どれを優先しますか？