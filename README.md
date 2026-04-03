# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
データ取得（J-Quants）、ETL、ニュース収集とLLMによるニュースセンチメント、ファクター計算、監査ログ／発注トラッキングなどを組み合わせて、戦略研究から実運用までを想定したユーティリティ群を提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境変数／.env 自動読み込み（プロジェクトルート検出）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPXカレンダーの差分取得と保存（ページネーション・リトライ対応）
  - DuckDB へ冪等（ON CONFLICT DO UPDATE）で保存
- ETL パイプライン（run_daily_etl）
  - カレンダー → 日次株価 → 財務データ → 品質チェック の一括実行
  - 品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）と前処理（SSRF対策・トラッキングパラメータ除去）
- ニュースNLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを ai_scores に書き込む（バッチ・リトライ・JSON Mode）
  - 市場マクロセンチメントを合成して市場レジーム判定（regime_detector）
- Research 用ユーティリティ
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン、IC、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブル定義・初期化
  - 監査トレース用の初期化ユーティリティ（DuckDB）

---

## 前提（Prerequisites）

- Python 3.10 以上（type union 演算子 `X | Y` を使用）
- ネットワークアクセス（J-Quants API、OpenAI API、RSS フィードなど）
- 推奨パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

pip でインストールする例は下記参照。

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 開発用途（editable install）
     ```bash
     pip install -e ".[dev]" || pip install -e .
     ```
     ※ プロジェクトに pyproject/requirements の設定がある場合はそちらに従ってください。
   - 最低限必要なライブラリを個別に入れる場合：
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   プロジェクトルートに `.env`（または `.env.local`）を配置すると自動で読み込まれます（読み込み優先度は OS 環境 > .env.local > .env）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   KABUSYS_ENV=development  # development | paper_trading | live
   ```

   - `settings` オブジェクトからアクセスできます:
     ```py
     from kabusys.config import settings
     print(settings.jquants_refresh_token)
     ```

---

## 使い方（主要ユースケース例）

下記は簡単な使用例です。実環境ではログ設定や例外ハンドリングを適切に行ってください。

- DuckDB 接続の作成例
  ```py
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl）
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（銘柄ごとの AI スコアを ai_scores に保存）
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーを環境変数 OPENAI_API_KEY で指定するか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"wrote {written} scores")
  ```

- 市場レジームスコア（regime判定）
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  rc = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  print("score_regime done", rc)
  ```

- 監査ログ DB の初期化
  ```py
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで signal_events 等のテーブルが作成されます
  ```

- カレンダー関連ユーティリティ
  ```py
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

---

## 環境変数 / 設定（主な項目）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注機能と連携する場合）
- KABU_API_BASE_URL: kabu エンドポイント（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（1で無効）

注意: Settings でいくつかの必須環境変数は未設定時に ValueError を投げます（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD が必要な機能を使う場合）。

---

## ディレクトリ構成（主要ファイルと説明）

プロジェクトの主要モジュールツリー（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動読み込み、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約し OpenAI に送って ai_scores を更新する
    - regime_detector.py
      - ETF 1321 の MA とマクロ記事の LLM センチメントを合成して market_regime を書き込む
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API の取得・保存ユーティリティ（rate-limit・リトライ・トークンリフレッシュ）
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等
      - ETLResult クラス
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 収集、URL 正規化、SSRF 対策、raw_news 保存ロジック
    - calendar_management.py
      - market_calendar の取得・営業日判定・next/prev_trading_day 等
    - stats.py
      - zscore_normalize などの統計ユーティリティ
    - quality.py
      - 欠損・スパイク・重複・日付不整合チェック（QualityIssue）
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）DDL と初期化
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク関数

（上記は主要機能のみ抜粋しています。詳細は各ファイルの docstring を参照してください。）

---

## ロギングと運用に関する注意

- OpenAI API 呼び出しや外部 HTTP はリトライとフェイルセーフ（失敗時はスコア0/スキップなど）を備えていますが、運用時はログと監視を必ず設定してください。
- market_regime / ai_scores / raw_prices 等の書込みは DuckDB トランザクションで保護していますが、接続先ファイルのパーミッションやバックアップ方針を検討してください。
- KABUSYS_ENV を `live` に設定すると実運用フラグとして挙動を切り替えるコードがあるため、テスト時は `development` を使用してください。

---

## 開発 / 貢献

- 各モジュールはユニットテストを想定した設計（依存注入・小さな関数分割）になっています。テストの追加・モック化を行いやすい構造です。
- PR の際は docstring と型注釈を維持し、API の互換性に注意してください。

---

以上がこのリポジトリの README です。必要があれば「セットアップの詳細（requirements.txt/pyproject 例）」「具体的な .env.example を作るテンプレート」「運用用ユーティリティ（systemd, supervisor 起動例）」などを追記しますので、ご希望を教えてください。