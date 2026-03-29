# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータプラットフォーム、リサーチ、AI 支援のスコアリング、及び監査付きの自動売買ワークフローを支える Python ライブラリ群です。  
本リポジトリは ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP スコアリング、ファクター計算、マーケットレジーム判定、監査ログ（トレーサビリティ）などの主要コンポーネントを含みます。

主な設計方針：
- ルックアヘッドバイアス防止（内部で date.today() を不用意に参照しない）
- DuckDB を使ったローカル/軽量データレイヤ（ETL / 解析用）
- OpenAI を用いたニュースセンチメント判定（JSON Mode + リトライ・検証）
- J-Quants API からの差分取得・冪等保存（ON CONFLICT 等）
- 監査ログによりシグナル → 発注 → 約定までのトレーサビリティを保証

---

## 機能一覧

- データ取得・ETL
  - J-Quants API からの株価（日次 OHLCV）、財務データ、JPX カレンダー取得（ページネーション対応・トークン自動リフレッシュ・レートリミット管理）
  - DuckDB への冪等保存（ON CONFLICT）
  - 日次 ETL パイプライン（calendar → prices → financials → 品質チェック）

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、主キー重複検出、日付整合性チェック
  - QualityIssue オブジェクトで結果を返却

- ニュース収集・NLP
  - RSS フィード取得（SSRF 対策、gzip 対応、トラッキングパラメータ削除）
  - OpenAI（gpt-4o-mini 想定）を使った銘柄ごとのニュースセンチメント（ai_scores）算出
  - レスポンス検証、チャンク送信、リトライ（429/ネットワーク/5xx）

- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュース（LLM）を加重合成して日次で bull/neutral/bear を判定・保存

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Z スコア正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - order_request_id による冪等性、UTC タイムスタンプの利用

---

## セットアップ手順

以下は開発環境や実行環境の最低限のセットアップ手順例です。プロジェクトの packaging（pyproject.toml / requirements.txt）がある場合はそちらに従ってください。

1. Python の準備
   - 推奨: Python 3.10+（コードは型ヒントに union 型等を使用）
   - 仮想環境を作成・有効化することを推奨します。

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows (PowerShell / cmd)
   ```

2. 必要パッケージのインストール（例）
   - 主に以下のパッケージが必要です: duckdb, openai, defusedxml
   - 実際の依存関係はプロジェクトの依存定義に従ってください。

   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. リポジトリをインストール（開発用）
   ```
   pip install -e .
   ```
   （プロジェクトに pyproject.toml / setup.py がある場合）

4. 環境変数の設定
   - 必須（実行機能に応じて）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector で利用）
     - KABU_API_PASSWORD      : kabuステーション API 用のパスワード（発注系を使う場合）
     - SLACK_BOT_TOKEN        : Slack 通知を使う場合
     - SLACK_CHANNEL_ID       : Slack チャンネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
     - KABU_API_BASE_URL — kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

   - .env 自動読み込み:
     パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます（OS 環境変数より低優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例 `.env`（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データフォルダの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な API と実行例）

以下はライブラリを直接インポートして使用する例です。実行前に必須環境変数を設定してください。

- DuckDB 接続の準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定しないと今日を基準に実行します（内部で営業日調整あり）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（ai のエントリ）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions 等のテーブルが作成されます
  ```

- J-Quants クライアントの直接利用（テストやデバッグ）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

  token = get_id_token()  # settings から JQUANTS_REFRESH_TOKEN を参照
  records = fetch_daily_quotes(date_from=date(2026, 1, 1), date_to=date(2026, 3, 1))
  ```

- リサーチ関数（例: モメンタム計算）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点：
- OpenAI 呼び出しを含む機能（score_news, score_regime）は `OPENAI_API_KEY` が必要です。
- J-Quants API 呼び出しを含む機能は `JQUANTS_REFRESH_TOKEN` が必要です。
- これらの関数は外部 API に依存するため、テスト時は該当モジュールの内部呼び出し（_call_openai_api 等）をモックすることを推奨します。

---

## よくあるトラブルシューティング

- 環境変数エラー:
  - missing: 実行時に ValueError で必須環境変数が無い旨が出ます（例: OPENAI_API_KEY）。`.env` か環境に設定してください。

- .env が自動で読み込まれない:
  - パッケージはプロジェクトルート（.git または pyproject.toml）を探索して `.env` を読み込みます。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI のレスポンスパースエラー:
  - news_nlp / regime_detector は API レスポンスを厳密な JSON で期待しており、パース失敗時はログを出して安全にフォールバック（0.0 やスキップ）します。連続失敗が出る場合は API 呼び出し制限やモデルの出力形式を確認してください。

- J-Quants API のレート制限:
  - モジュール内で固定間隔スロットリングを実装していますが、大量同時実行等で問題が出る場合はレート制御設定を見直してください。

---

## ディレクトリ構成

主要なファイル・モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理（.env 自動ロード等）
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py              — 市場レジーム判定（ma200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存関数）
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - etl.py                          — ETL の公開型（ETLResult エクスポート）
    - news_collector.py               — RSS ニュース収集（SSRF 対策・正規化）
    - calendar_management.py          — マーケットカレンダー管理（営業日判定等）
    - quality.py                      — データ品質チェック
    - stats.py                        — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                        — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py              — Momentum/Value/Volatility の算出
    - feature_exploration.py          — 将来リターン、IC、統計サマリーなど
  - monitoring/ (存在が示唆されているがコード省略)
  - strategy/ (戦略層、実行層は別途実装想定)
  - execution/ (ブローカー接続・発注ロジックは別途実装想定)

（上記は本リポジトリのソースファイル群を抜粋したものです）

---

## 貢献・拡張案

- 発注・ブローカー接続層（kabuステーション・API 統合）
- Backtest 用の time-traveling DB snapshot / シミュレーション環境
- モデル学習パイプライン（特徴量エンジニアリング → 学習 → デプロイ）
- Slack / メトリクス用の監視・アラート統合

---

必要に応じて README をプロジェクト固有のインストール手順（pyproject.toml / requirements.txt の内容）や実運用の運用手順（cron / Airflow / GitHub Actions のジョブ例）に合わせてカスタマイズできます。追加で載せたい実行例や運用フローがあれば教えてください。