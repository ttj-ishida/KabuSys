# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL・データ品質チェック・ニュース収集・LLMベースのニュースセンチメント・市場レジーム判定・ファクター計算・監査ログ（トレーサビリティ）まで、トレーディングシステム構築に必要な主要コンポーネントを揃えています。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API クライアント（ページネーション・レートリミット・トークン自動リフレッシュ・リトライ実装）
  - 日次 ETL パイプライン（株価、財務、カレンダー取得 + 品質チェック）
  - 差分取得 / バックフィル機能

- データ品質管理
  - 欠損検出、スパイク検出（前日比閾値）、主キー重複、日付整合性チェック
  - QualityIssue オブジェクトで詳細を収集

- 市場カレンダー管理
  - JPX カレンダーの差分更新、営業日判定・前後営業日検索・SQ判定など
  - カレンダーが未取得の場合は曜日ベースでフォールバック

- ニュース収集
  - RSS フィードの安全な取得（SSRF対策、gzip制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存

- ニュース NLP（LLM）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント付与（ai_scores テーブルへの保存）
  - レスポンス検証、バッチ処理、リトライ（429/ネットワーク/5xx）等の堅牢化

- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュースセンチメント（重み30%）を合成して 'bull'/'neutral'/'bear' を判定
  - OpenAI 呼び出しに対するフォールバックやリトライ実装

- 研究（Research）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン（forward returns）、IC（Information Coefficient）、統計サマリー、Z スコア正規化など

- 監査ログ（Audit / トレーサビリティ）
  - signal_events / order_requests / executions など監査テーブル定義と初期化ユーティリティ
  - UUID による一貫したトレーサビリティ設計

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 環境変数ベースの設定アクセス（kabusys.config.settings）

---

## 前提（Prerequisites）

- Python 3.10 以上（typing の | 型表記と __future__ 注釈を利用）
- 必要なライブラリ（代表例、実際は requirements.txt を用意してください）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API / OpenAI / RSS フィード 等）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows (PowerShell 等)
   ```

3. 依存パッケージをインストール
   - 例 (requirements.txt がある前提):
     ```
     pip install -r requirements.txt
     ```
   - 手動で:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数を設定
   - 必須（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — 通知先チャンネルID
     - OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定で使用）
   - 任意（デフォルトあり）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   - .env ファイル
     - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（OS 環境変数が優先）。
     - 自動読み込みを無効化するには:
       ```
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
       ```

5. DuckDB 初期化（監査ログ用）
   - 監査ログ用 DB を作成してスキーマを初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 他のテーブルスキーマはプロジェクト内の schema 初期化用関数を用意している想定です（必要に応じて実行してください）。

---

## 使い方（基本的な例）

以下に代表的な利用例を示します。実稼働ではログ設定、例外処理、ジョブスケジューラ（cron / Airflow 等）を併用してください。

- DuckDB 接続の用意
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（AI）をスコアリングして ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジームを判定して market_regime に書き込む
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  moments = calc_momentum(conn, date(2026, 3, 20))
  vols = calc_volatility(conn, date(2026, 3, 20))
  values = calc_value(conn, date(2026, 3, 20))
  ```

- Z スコア正規化ユーティリティ
  ```python
  from kabusys.data.stats import zscore_normalize

  normed = zscore_normalize(moments, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

- 監査ログスキーマ初期化（既存 DB に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注意:
- OpenAI 呼び出しはネットワーク API を使用するため、テスト時は kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api をモックしてください（ユニットテスト向け設計あり）。
- 日付処理はバックテストのルックアヘッドバイアス対策が各モジュールで配慮されています。target_date を明示的に渡して利用してください。

---

## よく使う環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（AI スコアリング・レジーム判定で必須）
- KABU_API_PASSWORD — kabu API 用パスワード
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ公開（data, strategy, execution, monitoring）
  - config.py — 環境変数 / .env 読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM によるセンチメントスコア生成（ai_scores へ保存）
    - regime_detector.py — 市場レジーム判定（ETF 1321 MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL 代表インターフェース（ETLResult 再エクスポート）
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（QualityIssue）
    - news_collector.py — RSS 収集・前処理・保存
    - audit.py — 監査ログテーブル定義と初期化（init_audit_db 等）
  - research/
    - __init__.py — 研究用 API エクスポート
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン・IC・rank・summaries 等

（上記は主要ファイルのみ抜粋。実際のリポジトリにはさらに strategy / execution / monitoring 等のモジュールが存在する想定です。）

---

## テストとモックについて

- OpenAI 呼び出しは専用のラッパー関数（_call_openai_api）を経由しているため、ユニットテストではこれらをモックして deterministic にテスト可能です。
- news_collector のネットワーク呼び出しも _urlopen を差し替え可能にしてあり、外部接続を行わずに RSS ロジックを検証できます。

---

## 注意点 / 運用上の補足

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して行います。CI／ユニットテスト等で自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants API のレート制限や OpenAI の利用に伴うコストに注意してください。jquants_client は 120 req/min を守る RateLimiter を実装していますが、運用スケジュールに合わせて設計してください。
- DuckDB の executemany の挙動（空リストバインド）やスキーマ初期化時のトランザクション周りの挙動に注意（コメントや関数内の注意書きを参照）。

---

もし README に追加したいサンプルジョブ（cron 例、Airflow DAG、CI 用のテストスクリプト等）があれば教えてください。必要に応じてサンプルを追記します。