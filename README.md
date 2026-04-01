# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
DuckDB をデータ層に用い、J-Quants API からのデータ取得（ETL）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（オーダー／約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 主な特徴 / 機能一覧

- 環境管理
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
  - 設定値は `kabusys.config.settings` から参照

- データ ETL（J-Quants 統合）
  - 日次株価（OHLCV）取得・保存（ページネーション・リトライ・レート制御対応）
  - 財務データ（四半期 PL/BS）取得・保存
  - JPX マーケットカレンダー（祝日・半日・SQ）取得・保存
  - 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集 / NLP
  - RSS からニュース収集（SSRF 対策・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄単位のニュースセンチメント scoring（ai_scores 保存）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離 + LLM センチメント）

- 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計要約
  - Z-score 正規化などの統計ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを作成する初期化ユーティリティ
  - UUID による一貫したトレーサビリティ設計、UTC タイムスタンプ固定

---

## 必要条件

- Python 3.10 以上
- 必要パッケージ（代表例）
  - duckdb
  - openai (OpenAI Python SDK v1系)
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI 等の API）

（プロジェクトの配布パッケージに requirements.txt / extras があればそちらを利用してください）

---

## セットアップ手順

1. 仮想環境を作成して有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要ライブラリをインストール
   ```bash
   pip install duckdb openai defusedxml
   # 他に必要なものがあれば追加
   ```

3. パッケージを編集可能インストール（開発時）
   ```bash
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くことで自動読み込みされます。
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数（主要なもの）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: environment（development / paper_trading / live）
     - LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
   - 例（.env）
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

---

## 使い方（代表例）

以下はライブラリの主要関数を呼び出すサンプルです。実行は Python スクリプトや cron / Airflow 等から呼び出す想定です。

- DuckDB 接続準備（設定経由でパスを取得）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は pathlib.Path
  ```

- 日次 ETL を実行する（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を None にすると今日が対象（内部で営業日調整あり）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア（ai/news_nlp）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI API キーは env または api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"written ai_scores: {n_written}")
  ```

- 市場レジーム判定（ai/regime_detector）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログスキーマ初期化（data.audit）
  ```python
  from kabusys.data.audit import init_audit_db, init_audit_schema

  # 監査用 DB ファイルを新規作成して接続を得る
  audit_conn = init_audit_db(":memory:")  # または path を指定
  # 既存の conn に監査テーブルを追加する場合:
  init_audit_schema(conn, transactional=True)
  ```

- 研究用ユーティリティ例（ファクター計算）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意:
- score_news / score_regime は OpenAI API を呼び出すため API キー（環境変数 OPENAI_API_KEY または引数）を設定してください。
- ETL / API 呼び出しはネットワーク・API 料金やレート制限に依存するため、本番環境では適切なスケジューラと監視を用いて運用してください。

---

## 主要モジュール / ディレクトリ構成

（リポジトリの src/kabusys 配下の主要ファイル・説明）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込みと Settings クラスを提供
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースの LLM ベースセンチメントスコアリング、score_news
    - regime_detector.py    — マクロ + ETF MA200 乖離を合成した市場レジーム判定、score_regime
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py           — ETL パイプライン (run_daily_etl 等)
    - etl.py                — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py     — RSS 収集と raw_news 保存
    - calendar_management.py— マーケットカレンダー管理と営業日判定
    - quality.py            — データ品質チェック
    - stats.py              — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py              — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py— 将来リターン / IC / 統計要約など

（その他）
- docs / tests / scripts があれば適宜参照してください。

---

## 実運用上の注意・設計上の留意点

- Look-ahead バイアス回避: 内部関数は target_date 未満／以前のデータのみを参照するよう設計されています（datetime.today() の直接使用を避ける）。
- フェイルセーフ: 外部 API の失敗時にはできる限り例外で全面停止せず、部分的にスキップして継続する挙動が多く採用されています（ログ出力が基本）。
- 冪等性: DuckDB への保存は ON CONFLICT / UPDATE を利用し、再実行での上書きを安全にしています。
- セキュリティ: news_collector は SSRF 対策、XML インジェクション対策（defusedxml）を実装済み。

---

## サポート / 貢献

バグ報告や改善提案は Issue を通してお願いします。コード contrib の際はテスト・型チェック・文書更新を添えてください。

---

上記 README はこのコードベースの主要な使い方と構成をまとめたものです。必要であれば、具体的な運用例（Airflow / systemd / cron のジョブ定義や Slack 通知の例）や、より詳細な環境変数のサンプル .env.example を追記できます。ご希望があれば追加します。