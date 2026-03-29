# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買基盤のための Python モジュール群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP による銘柄センチメント算出、ファクター計算 / リサーチユーティリティ、監査ログ（トレース可能な発注監査テーブル）などを提供します。

主な設計方針：
- ルックアヘッドバイアス対策（内部で datetime.today() を直接参照しない等）
- DuckDB をデータレイクとして利用（冪等保存やトランザクション処理を重視）
- 外部 API 呼び出し（J-Quants, OpenAI）にはリトライ・バックオフ・フェイルセーフを実装
- モジュール構成を分離してテストと再利用性を高める

バージョン: 0.1.0

---

## 機能一覧

- 環境設定 / 自動 .env ロード
  - settings オブジェクト経由で環境変数を参照（`kabusys.config.settings`）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む機能（無効化可）

- データ ETL（J-Quants）
  - daily prices（raw_prices）、financials（raw_financials）、market_calendar を取得・保存
  - ページネーション・ID トークン自動リフレッシュ・レートリミット制御・リトライを実装
  - run_daily_etl 等の高レベル API を提供（差分取得・バックフィル・品質チェック含む）

- データ品質チェック
  - 欠損データ、重複、スパイク（急騰/急落）、日付整合性チェック等（`kabusys.data.quality`）

- ニュース収集
  - RSS 取得（SSRF 対策、gzip サイズチェック、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存を想定した設計（`kabusys.data.news_collector`）

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（`score_news`）を ai_scores に保存
  - マクロニュースを LLM にかけて市場レジーム判定（`score_regime`）

- リサーチ / ファクター計算
  - momentum / value / volatility 等のファクター計算（`kabusys.research`）
  - 将来リターン算出、IC（スピアマン相関）計算、統計サマリー等

- 監査ログ（Audit）
  - signal → order_request → executions をトレースする監査テーブル定義 / 初期化ユーティリティ（`kabusys.data.audit`）

---

## セットアップ手順

1. リポジトリをチェックアウト（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   必要なパッケージ（例）：duckdb, openai, defusedxml
   プロジェクトの pyproject.toml / requirements.txt がある想定であれば：
   ```
   pip install -e .
   ```
   または最小依存を直接インストール:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定
   プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須の環境変数（本コードベースで参照される主なもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN        : Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - KABU_API_PASSWORD     : kabu ステーション API のパスワード
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 実行時に必要）

   任意（デフォルト値あり）:
   - KABUSYS_ENV (development|paper_trading|live) - デフォルト development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) - デフォルト INFO
   - DUCKDB_PATH - DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH - 監視 DB のパス（デフォルト data/monitoring.db）

   例 .env の最小例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   KABU_API_PASSWORD=passwd
   ```

---

## 使い方（主要ユースケース）

以下はライブラリをインポートして利用する基本例です。詳細な引数や戻り値は各モジュールの docstring を参照してください。

- DuckDB 接続準備
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- ETL（日次パイプライン）を実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に保存
  - OpenAI API キーは環境変数 OPENAI_API_KEY を設定するか、引数で渡します。
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None=環境変数から取得
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（マクロ + MA200 乖離）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB を初期化（監査専用 DB を作成する例）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit を使って監査ログに書き込みが可能
  ```

- ファクター計算 / リサーチ
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  val = calc_value(conn, date0)
  vol = calc_volatility(conn, date0)
  ```

注意点：
- score_news / score_regime は OpenAI API を呼ぶため API キーとネットワークが必要です。API 呼び出しはリトライやフェイルセーフを備えていますが、API 制限や料金に注意してください。
- DuckDB に対する多数の executemany 呼び出しや大規模データ保存を行うため、ファイルパスやディスク空き容量に注意してください。
- ETL / ニュース収集はバッチ処理として夜間に実行することを想定した設計になっています。

---

## ディレクトリ構成（主要ファイル）

リポジトリの `src/kabusys` 配下に主要モジュールがあります。ファイルは大まかに次の役割に分かれます。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py          : ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py   : マクロ + ETF(1321) MA200 を使った市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    : J-Quants API クライアント + DuckDB への保存ロジック
    - pipeline.py          : ETL パイプライン（run_daily_etl 等）
    - etl.py               : ETLResult の再エクスポート
    - news_collector.py    : RSS 取得・前処理・raw_news 保存ロジック
    - calendar_management.py : 市場カレンダー判定 / 更新ジョブ
    - quality.py           : データ品質チェック
    - stats.py             : zscore_normalize 等統計ユーティリティ
    - audit.py             : 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py   : Momentum / Value / Volatility ファクター計算
    - feature_exploration.py : 将来リターン / IC / 統計サマリー 等
  - research パブリック API は kabusys.research.* でエクスポート

---

## 設計上の留意点（運用・開発者向け）

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テスト時など自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- LLM 呼び出し（OpenAI）は JSON-mode を前提とし、レスポンスのパースやバリデーションに厳格な実装をしています。失敗時はスコアを 0 にフォールバックするなどフェイルセーフ設計になっています。
- ETL は idempotent（冪等）にデータを保存するよう設計されています（ON CONFLICT DO UPDATE 等）。
- DuckDB の executemany に関するバージョン差異（空リスト不可など）に配慮した実装が含まれます。
- 運用時は KABUSYS_ENV を適切に設定してください（development / paper_trading / live）。live 実行時は外部 API や発注周りの扱いに注意してください。

---

## よくある操作例（まとめ）

- 開発環境でローカル DuckDB を使って ETL を試す:
  1. .env を用意（JQUANTS_REFRESH_TOKEN 等）
  2. Python から run_daily_etl を呼ぶ
- OpenAI を使ってニューススコアを取得:
  - `OPENAI_API_KEY` を設定して `kabusys.ai.news_nlp.score_news(conn, target_date)` を実行
- 監査テーブル初期化:
  - `kabusys.data.audit.init_audit_db("data/audit.duckdb")`

---

必要であれば README に以下を追記できます：
- .env.example の具体例ファイル
- CI / デプロイ手順（systemd / Airflow ジョブ例）
- 運用時のモニタリング / Slack 通知フロー例
- API 使用料・レート制限の注意（OpenAI / J-Quants）

追加で入れてほしい情報や使い方のサンプルがあれば教えてください。README を拡張して整備します。