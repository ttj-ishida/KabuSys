# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログなど、自動売買インフラに必要な機能をモジュール化して提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ収集 / ETL
  - J-Quants API から株価（OHLCV）、財務、マーケットカレンダーを差分取得・保存（DuckDB）
  - ページネーション・レート制御・リトライ・トークンリフレッシュ対応
- データ品質チェック
  - 欠損、重複、将来日付、スパイク検出などのチェック群
- ニュース系 NLP（OpenAI）
  - ニュース記事を銘柄ごとに集約し LLM でセンチメント（ai_scores）を生成
  - マクロニュースを使った市場レジーム判定（ma200 + LLM）
  - JSON Mode（gpt-4o-mini 等）による堅牢なレスポンス処理とリトライ
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - Z-score 正規化ユーティリティ
- カレンダー管理（JPX）
  - market_calendar テーブルの更新・営業日判定・next/prev_trading_day 等
- 監査ログ（Audit）
  - signal → order_request → execution をトレース可能な監査スキーマ（DuckDB）
  - 冪等性・UTC タイムスタンプ管理
- ニュース収集（RSS）
  - URL 正規化、SSRF 対策、XML パースの安全処理、冪等保存

---

## 必要条件 / 推奨環境

- Python 3.10+
  - 型注釈で `|` を使用しているため Python 3.10 以上を推奨します
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

---

## セットアップ手順

1. リポジトリをクローン / コピー
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - プロジェクトに requirements ファイルがない場合、最低限以下をインストールしてください:
   ```
   pip install duckdb openai defusedxml
   ```
   - 開発用にローカル編集を反映したい場合:
   ```
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（news/regime に必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知連携用（任意）
     - DUCKDB_PATH: DuckDB の保存先（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE: paper trading のモック埋め方（instant/partial/never/reject）
     - PAPER_TRADING_SQLITE_PATH: paper trading の SQLite パス（デフォルト: data/paper_trading.db）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）

   例 `.env`（抜粋）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABU_API_PASSWORD=your_kabu_password
   ```

---

## 使い方（コード例）

以下は主要 API の利用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を引数で渡すか、OPENAI_API_KEY を環境変数に設定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  rows = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点:
- score_news / score_regime は OpenAI の API を呼び出します。ネットワーク状況やレート制限に注意してください。失敗時はフェイルセーフとしてスコアを 0 にする設計の箇所があります。
- ETL / J-Quants クライアントは J-Quants の ID トークンを自動取得・キャッシュします。JQUANTS_REFRESH_TOKEN を設定してください。

---

## 主要モジュールと機能概要

- kabusys.config
  - .env / 環境変数の読み込み、Settings オブジェクト（各種パスやトークン、モードなど）
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う
- kabusys.data
  - jquants_client: J-Quants API の取得・保存ロジック（rate limit、リトライ、保存の冪等性）
  - pipeline: ETL（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - news_collector: RSS 収集・正規化・保存（SSRF 対策・トラッキング除去）
  - audit: 監査ログスキーマ初期化 / audit DB ハンドリング
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp: 銘柄単位のニュースセンチメント計算（LLM 呼び出し + バリデーション）
  - regime_detector: ma200 とマクロニュース LLM を合成して市場レジーム判定
- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリューなどのファクター計算
  - feature_exploration: 将来リターン計算 / IC / 統計サマリ / ランク変換

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート）
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
      - quality.py
      - calendar_management.py
      - news_collector.py
      - audit.py
      - stats.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
    - monitoring/ (読み出し用に __all__ に含まれるが詳細実装はここに依存)
- pyproject.toml / setup.cfg / .gitignore（プロジェクト管理ファイル）

---

## 運用上の注意 / トラブルシューティング

- 環境変数未設定によるエラー:
  - settings で必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が未設定だと ValueError が発生します。`.env.example` を参考に `.env` を作成してください。
- OpenAI のレスポンスパースエラー:
  - LLM の出力は JSON モードで受け取るよう設計されていますが、稀に期待外のテキストが混ざるため復元処理を行っています。エラー時は該当銘柄をスキップしてログに残します。
- J-Quants API のレート制限:
  - 120 req/min を守るため内部に固定間隔のレートリミッターを実装しています。大量の同期リクエストを投げると遅延が生じます。
- DuckDB の互換性:
  - 一部 executemany の挙動や配列バインドに依存する処理は DuckDB のバージョン差で振る舞いが変わることがあります。DuckDB の安定版を利用してください。

---

## 今後の拡張案（参考）

- モニタリング / アラート用ダッシュボード連携（Prometheus / Grafana）
- 発注（execution）層の broker クライアント統合（kabuステーション実装）
- テストスイート・CI の追加（単体テスト、統合テスト、API モック）

---

README に記載されていない細かな挙動（引数の詳細、ログ形式、DB スキーマ細部など）は各ソースコード（src/kabusys 以下）内の docstring / コメントを参照してください。必要であれば、特定モジュールの使い方や .env の完全な項目一覧、スキーマ定義の抜粋なども別途用意します。どの部分を詳しく説明しましょうか？