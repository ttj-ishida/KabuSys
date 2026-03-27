# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。  
DuckDB をデータレイクとして用い、J‑Quants API からのデータ取得（株価・財務・市場カレンダー）・ETL、ニュース収集・NLP によるセンチメント算出、マーケットレジーム判定、監査ログテーブルの初期化などを提供します。

---

## 主な特徴（機能一覧）

- データ収集 / ETL
  - J‑Quants API から日次株価（OHLCV）、財務データ、上場情報、JPX市場カレンダーを差分取得・永続化（ページネーション・レート制御・冪等保存対応）
  - ETL パイプライン（run_daily_etl）でカレンダー取得→株価→財務→品質チェックの一括実行
- データ品質管理
  - 欠損・重複・異常スパイク・日付不整合のチェック（quality モジュール）
- ニュース処理 / NLP
  - RSS 収集（news_collector.fetch_rss）：SSRF 対策、URL 正規化、前処理、冪等保存設計
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント算出（news_nlp.score_news）
- マーケットレジーム判定
  - ETF(1321) の 200 日移動平均乖離 + マクロニュースの LLM センチメントを合成（regime_detector.score_regime）
- リサーチ用ユーティリティ
  - モメンタム/バリュー/ボラティリティ等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）、ファクター要約など
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ（data.audit）
- 設定管理
  - .env ファイルまたは環境変数から設定を自動ロード（config.Settings）

---

## 動作要件

- Python 3.10 以上（型ヒントの | 演算子を使用）
- 主な依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外はプロジェクトの requirements.txt を参照してください）

※実行には外部 API（J‑Quants / OpenAI 等）の認証情報が必要です。

---

## 環境変数（主なもの）

このプロジェクトは環境変数および `.env`/.env.local をサポートします。自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（少なくとも開発で使う場合）:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知を使う場合に必要
- SLACK_CHANNEL_ID — Slack チャネルID
- KABU_API_PASSWORD — kabuステーション API を利用する場合

任意 / デフォルト付き:
- KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 で自動 .env 読み込みを無効化
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に未指定時に参照）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   - 実際にはプロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください。

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` を作成するか、環境変数をエクスポートしてください。
   - 例は上節を参照。

---

## 使い方（主要なユースケース例）

以下は Python REPL やスクリプト内で呼び出す例です。すべての呼び出しで DuckDB 接続（duckdb.connect）を渡します。

- ETL（デイリー ETL 実行）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント算出（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")
  ```

- 市場レジーム判定（regime スコアの算出と保存）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（監査用 DB を別途用意）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # :memory: も可
  # conn を使用して order/signals の書き込みを行う
  ```

- J‑Quants の id token を直接取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # JQUANTS_REFRESH_TOKEN を参照
  print(token)
  ```

注意:
- OpenAI API の呼び出しは gpt-4o-mini を想定した JSON Mode を使っています。API レスポンスのスキーマ依存があるため、OpenAI SDK の互換性とレスポンス形式に注意してください。
- DuckDB によるトランザクション管理や executemany の仕様に依存する部分があります（空リスト渡しに注意）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なモジュールと概略：

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py        -- ニュースセンチメント算出（score_news）
    - regime_detector.py -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  -- J‑Quants API クライアント（fetch / save）
    - pipeline.py        -- ETL パイプライン（run_daily_etl, run_*_etl）
    - news_collector.py  -- RSS 収集と前処理
    - calendar_management.py -- マーケットカレンダー管理（is_trading_day 等）
    - quality.py         -- データ品質チェック
    - stats.py           -- 汎用統計ユーティリティ（zscore_normalize）
    - audit.py           -- 監査ログテーブルの初期化
    - etl.py             -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/, research/ 以下にはリサーチや戦略検証で使う関数群あり

（各ファイルは詳細な docstring と設計方針・失敗時のフォールバックを記載しています）

---

## 補足 / 運用上の注意

- 自動 .env ロード
  - config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を読み込みます。自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Look‑ahead Bias 対策
  - 多くの関数は内部で datetime.now() / date.today() を直接参照せず、target_date を明示的に渡す設計になっています。バックテストなどでのルックアヘッドを避けるため、target_date を適切に指定してください。
- フェイルセーフ設計
  - OpenAI / J‑Quants API 呼び出しはリトライやフォールバック（スコア 0.0 へのフォールバックなど）を実装しており、外部 API の一時的障害下でも処理が完全停止しないように設計されています。ただし重大なエラーはログに残して上位に伝播します。
- セキュリティ
  - news_collector は SSRF 対策（ホストチェック、リダイレクト検査）、XML パースの安全化（defusedxml）などを実装しています。
- DuckDB バージョン依存
  - 一部実装（executemany の空リスト制御や型バインディング）は DuckDB バージョンに依存するため、運用時は安定版の DuckDB を利用してください。

---

必要な追加情報（例: requirements.txt、CI/デプロイ手順、戦略レイヤーの例）を README に追記したい場合は、どの内容を優先するか教えてください。