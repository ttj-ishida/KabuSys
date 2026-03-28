# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買パイプラインのライブラリ群です。J-Quants API からデータを収集・保存し、DuckDB を用いた ETL／品質チェック、ニュースの NLP スコアリング（OpenAI）や市場レジーム判定、リサーチ用のファクター計算、監査ログ（オーダー追跡）などを提供します。

主な用途:
- データ収集（株価・財務・JPX カレンダー）
- データ品質チェック
- ニュースセンチメント（LLM）による銘柄スコアリング
- 市場レジーム判定（ETF + マクロニュース）
- ファクター計算・特徴量探索（リサーチ）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）

バージョン: 0.1.0

---

## 機能一覧

- データ収集 / ETL
  - J-Quants API 経由で株価（日次 OHLCV）、財務（四半期 / 報告書）、JPX カレンダーを差分取得（ページネーション対応、レートリミット・リトライ実装）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - run_daily_etl を含む ETL エントリポイント

- データ品質チェック
  - 欠損（OHLC 欠損）検出、スパイク検出（前日比閾値）、主キー重複チェック、日付整合性チェック
  - チェック結果は QualityIssue オブジェクトで取得

- ニュース収集 / NLP
  - RSS 収集（SSRF 対策、gzip 上限、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコア付与（score_news）

- 市場レジーム判定
  - ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次レジーム（bull/neutral/bear）を判定（score_regime）

- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリューなどのファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー、Z スコア正規化

- 監査（Audit）
  - シグナル → 発注要求 → 約定までを追跡する監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）

- 設定管理
  - 環境変数 / .env 自動ロード（プロジェクトルート検出、.env < .env.local の優先度制御）
  - 必須設定チェック（設定がない場合は ValueError）

---

## セットアップ手順

前提
- Python 3.9+（ソースが typing | None 型など最新機能を使用しているため、3.9 以降を推奨）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

推奨手順（例）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成と有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

3. 依存パッケージをインストール
   （プロジェクトの pyproject.toml / requirements.txt がある想定。なければ少なくとも以下をインストール）
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 他に logging や標準ライブラリのみを使うモジュールが多く、上記が主な外部依存です。

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABU_API_PASSWORD=your_pass
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. 初期 DB の作成（必要に応じて）
   - 監査用 DB 初期化例:
     ```python
     from pathlib import Path
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(Path("data/audit.duckdb"))
     ```

---

## 使い方（主要ユーティリティ例）

以下は簡単な Python スニペット例です。プロダクション用途ではログ設定や例外処理を追加してください。

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB 接続を開いて日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを生成（OpenAI API キーは環境変数 `OPENAI_API_KEY` または引数）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定（regime score）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（既存 DB に追加）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect(str(settings.duckdb_path))
  init_audit_schema(conn, transactional=True)
  ```

- リサーチ関数の使用例
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, zscore_normalize

  conn = duckdb.connect(str(settings.duckdb_path))
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

---

## 設定の自動読み込みについて

- パッケージ起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env` → `.env.local` の順で読み込みを行います。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします（ただし既に OS 環境変数にあるキーは保護されます）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

---

## よく使う環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabu API 接続用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

推奨 / 任意:
- OPENAI_API_KEY — OpenAI を使う処理で必要（score_news / score_regime 等）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するフラグ（値を設定すると有効）

---

## ディレクトリ構成

主要なファイルとモジュール構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリングと関連ユーティリティ
    - regime_detector.py — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理と営業日ユーティリティ
    - etl.py (再エクスポート)
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック
    - audit.py — 監査テーブル定義・初期化
    - jquants_client.py — J-Quants API クライアント（取得 & 保存）
    - news_collector.py — RSS からのニュース収集
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai, data, research の各パッケージはそれぞれの公開 API を持ちます。

（README に載せきれない内部関数や詳細実装は各モジュールの docstring を参照してください）

---

## テスト / 開発メモ

- OpenAI や J-Quants の外部 API 呼び出しはモジュール内で抽象化されており、ユニットテストでは該当関数（例: kabusys.ai.news_nlp._call_openai_api, kabusys.data.jquants_client._request など）をモックする設計になっています。
- 自動環境読み込みを無効にすることでテスト環境での環境変数干渉を避けられます。

---

## 補足

- DuckDB を使うため、ローカルファイル DB（デフォルト data/kabusys.duckdb）を用意してください。ファイルパスは settings.duckdb_path で参照できます。
- OpenAI の JSON モードを利用する設計になっているため、API レスポンスのパースやリトライ戦略が組み込まれています。API キーやレート制限に注意して運用してください。
- 本 README はコードベースの docstring を要約したものです。詳細やパラメータの動作は各モジュールの docstring を参照してください。

もし特定の機能の使い方（例: ETL の詳細設定、監査テーブルの拡張、ニュースフィードの追加方法）について詳細が必要であれば教えてください。具体的なコード例や運用手順を追補します。