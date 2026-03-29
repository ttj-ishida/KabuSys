# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
データ取得（J‑Quants）、ETL、ニュース収集・NLP、ファクター計算、監査ログなどのユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような目的を持つ Python パッケージです。

- J‑Quants API を用いた株価・財務・マーケットカレンダーデータの差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（ai_scores）および市場レジーム判定
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ用スキーマ（シグナル→発注→約定のトレーサビリティ）
- 環境変数/設定の集中管理

設計方針として「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API障害時の graceful fallback）」を重視しています。

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J‑Quants クライアント（取得＋DuckDB 保存）：fetch_* / save_* 系
  - カレンダー管理・営業日判定（is_trading_day, next_trading_day 等）
  - ニュース収集（RSS）と前処理（news_collector）
  - データ品質チェック（quality.run_all_checks）
  - 監査ログスキーマ初期化（data.audit.init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: ニュース→ai_scores）
  - 市場レジーム判定（score_regime: ETF MA + マクロニュース→market_regime）
  - OpenAI の呼び出しは gpt-4o-mini を想定（JSON Mode）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で環境設定を取得

---

## セットアップ手順

以下は推奨のローカルセットアップ手順の例です（OS により適宜読み替えてください）。

前提
- Python 3.10+（typing の Union 表記などに依存）
- DuckDB（Python パッケージで OK）
- ネットワーク接続（J‑Quants / OpenAI / RSS）

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

3. 必要な依存パッケージをインストール  
   （プロジェクトに requirements.txt がある想定での例。なければ下の主要パッケージをインストールしてください）
   ```bash
   pip install -r requirements.txt
   ```
   または最低限：
   ```bash
   pip install duckdb openai defusedxml
   ```

4. パッケージを開発モードでインストール（任意）
   ```bash
   pip install -e .
   ```

5. 環境変数（.env）を設定  
   プロジェクトルートの `.env`（または `.env.local`）に必要なキーを設定します。自動で読み込まれます（ただしテスト等で無効化可能）。
   必須（主に production で必要となるもの）:
   - JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション用パスワード（発注実装がある場合）
   - SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID — 通知送付先のチャネル ID
   - OPENAI_API_KEY — OpenAI 呼び出しに必要（ai モジュール）
   推奨 / 任意:
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   例 `.env`（.env.example を参考に）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

6. 自動 .env 読み込みについて  
   パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` をロードします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡単な例）

以下は主要なユースケースのサンプルです。実際にはログ設定やエラーハンドリングを追加してください。

- DuckDB に接続して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  # settings.duckdb_path は Path オブジェクト
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア付け（ai_scores へ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
  count = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", count)
  ```

- 市場レジーム判定（market_regime へ保存）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  # 監査用に別ファイルを使うことも可能
  conn = init_audit_db(settings.duckdb_path)
  # これで signal_events / order_requests / executions 等のテーブルが作成される
  ```

- カレンダー判定（営業日判定等）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026, 4, 1)))
  ```

注意点:
- AI モジュール（news_nlp / regime_detector）は OpenAI API（OPENAI_API_KEY）を必要とします。API 呼び出しはリトライやフォールバック（失敗時は中立スコア）を備えていますが、API 利用料やレート制限に注意してください。
- J‑Quants API 呼び出しには JQUANTS_REFRESH_TOKEN が必要です。get_id_token を内部で使い idToken を取得します。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須: data.jquants_client.get_id_token)
- OPENAI_API_KEY (必須: ai.news_nlp, ai.regime_detector)
- KABU_API_PASSWORD (kabu API)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

.env ファイルの読み込みルール:
- プロジェクトルート（.git または pyproject.toml を目印）を探索して .env を読み込み
- 読み込み順: OS 環境変数 > .env.local > .env
- .env ファイルのパーサはシンプルなクォート処理とコメント処理に対応

---

## ディレクトリ構成

主要なファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（自動 .env ロード）
  - ai/
    - __init__.py (score_news エクスポート)
    - news_nlp.py                 — ニュースセンチメント解析（OpenAI）
    - regime_detector.py         — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py          — J‑Quants API クライアント + DuckDB 保存
    - pipeline.py                — ETL パイプライン / run_daily_etl など
    - etl.py                     — ETLResult 再エクスポート
    - calendar_management.py     — 市場カレンダー・営業日ロジック
    - news_collector.py          — RSS 収集・前処理
    - quality.py                 — データ品質チェック（QualityIssue）
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py     — 将来リターン、IC、サマリー等

（上記は主要モジュールのみ。細かい補助関数やユーティリティも多数収録）

---

## 開発・運用時の留意点

- セキュリティ:
  - API トークンやパスワードは決してソース管理にコミットしないでください（.gitignore に .env を追加）。
  - news_collector は SSRF / XML Bomb に対する防御を実装していますが、運用時の接続先制限や監視を行ってください。
- テスト:
  - OpenAI / J‑Quants への外部コールはモックしてユニットテストを実行してください。モジュール内の _call_openai_api 等は差し替え可能です。
- 冪等性:
  - ETL / save_* 関数は ON CONFLICT / upsert を用いて冪等性を保っています。ただし schema 変更時等は注意が必要です。
- ロギング:
  - LOG_LEVEL 環境変数でログレベルを制御してください。運用時は INFO〜WARNING を推奨します。

---

## 今後の拡張・参考

- 発注実装（kabu ステーション経由）やブローカー API 連携の追加
- バックテスト / Strategy 層の実装（現在は research と factor utilities を提供）
- メトリクス・モニタリング（Prometheus / Grafana など）
- CI による品質チェック・自動テスト

---

何か追加したいドキュメント（例: API 仕様、.env.example、セットアップ用の Dockerfile、実行スクリプトなど）があれば教えてください。README をそれに合わせて拡張します。