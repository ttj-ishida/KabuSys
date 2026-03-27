# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J‑Quants）によるデータ収集、品質チェック、ニュース収集・NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注〜約定トレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J‑Quants API 経由で株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分取得・保存
  - DuckDB への冪等保存（ON CONFLICT / Upsert）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損データ、スパイク（急騰/急落）、重複、日付不整合の検出（quality.run_all_checks）
- ニュース収集・NLP
  - RSS 収集（安全対策: SSRF 対策、サイズ制限、トラッキングパラメータ削除）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成（ai.regime_detector.score_regime）
- リサーチ用ファクター群
  - Momentum / Volatility / Value / 流動性などの計算（kabusys.research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- マーケットカレンダー管理
  - JPX カレンダーの差分更新、営業日判定ユーティリティ
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定までの監査テーブルを初期化 / 管理（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local / 環境変数読み込み、自動ロード（プロジェクトルート検出）および必須設定の取得（kabusys.config.settings）

---

## セットアップ手順

前提: Python 3.10+（型注釈に依存しているため）を推奨します。

1. リポジトリをクローン / ソースを取得
   - 例: git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (UNIX) または .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最低限必要な主要ライブラリ:
     - duckdb, openai, defusedxml
     - 例: pip install duckdb openai defusedxml

4. 開発インストール（任意）
   - pip install -e .

5. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml を含む場所）に `.env` と `.env.local` を配置できます。
   - 自動ロードはデフォルトで有効。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID: 通知対象チャンネル ID
     - KABU_API_PASSWORD: kabuステーション等の API パスワード（発注モジュール利用時）
     - OPENAI_API_KEY: OpenAI を利用する機能を実行する場合に必要（ai モジュール）
   - オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

6. データベース初期化（監査ログ等）
   - 監査用 DB を作る例:
     ```python
     import kabusys.data.audit as audit
     conn = audit.init_audit_db("data/audit.duckdb")
     ```
   - 既存の接続へ監査スキーマを追加する場合は `init_audit_schema(conn)` を使用。

---

## 使い方（主な API / 実行例）

以下は代表的な使い方の抜粋です。関数の詳細は各モジュールの docstring を参照してください。

- 設定の取得
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  is_live = settings.is_live
  ```

- DuckDB 接続作成
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）取得
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須
  ```

- リサーチ関数例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize
  from datetime import date

  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))

  # Z-score 正規化
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- RSS 取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

- J‑Quants クライアント直接利用（必要に応じて）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
  ```

注意:
- ai モジュール（news_nlp / regime_detector）は OpenAI API（gpt-4o-mini）を呼び出します。API キーは `OPENAI_API_KEY` 環境変数か、関数引数の `api_key` に指定してください。
- ETL / データ操作は DuckDB 接続（kabusys が想定するスキーマ）を前提とします。各テーブル定義や期待されるカラムはモジュール docstring を参照してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）から行われます。テスト時などに無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM センチメントスコアリング
    - regime_detector.py  — マクロセンチメント + MA で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J‑Quants API クライアント / DuckDB 保存
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult の再エクスポート
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - news_collector.py   — RSS 収集、前処理、raw_news への保存ロジック
    - quality.py          — データ品質チェック
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化（signal/order_requests/executions）
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Value / Volatility 等の計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー、rank
  - monitoring/ (エントリは __all__ に含まれるが実装は省略されている場合あり)
  - strategy/ (発注・戦略モジュールがある想定)
  - execution/ (発注実行ロジックがある想定)

---

## 設計上の注意点 / ベストプラクティス

- ルックアヘッドバイアス防止:
  - 多くの関数は内部で `date.today()` を参照しない仕様（target_date を明示的に渡すことを推奨）。
  - データ取得・スコアリングの際は常に対象日を明示してください。
- 冪等性:
  - ETL・保存関数は重複防止のため Upsert（ON CONFLICT）を使用していますが、外部から直接 DB を操作する場合は注意してください。
- API キー/トークン管理:
  - J‑Quants のリフレッシュトークンは `JQUANTS_REFRESH_TOKEN` を設定してください。jquants_client は自動で id_token を取得・リフレッシュします。
  - OpenAI は `OPENAI_API_KEY` を設定するか、各関数に `api_key` を渡してください。
- テスト:
  - 自動 .env 読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用。
  - ai モジュールの OpenAI 呼び出しは `_call_openai_api` をパッチしてモック可能（ユニットテスト向け）。

---

## 参考 / 追加情報

- 各モジュールは詳細な docstring を持っています。実装の意図や失敗時のフォールバック戦略、ログ出力内容などを参照してください。
- 本 README はコードベースに含まれる docstring を元に要点をまとめたものです。導入・運用時は実環境の API 制限や認証情報の取り扱いに注意してください。

もし README に追加したい実行スクリプト（例: cron ジョブ、Dockerfile、CI 設定）や、依存関係の完全な requirements.txt を含めたい場合は、その情報を教えてください。README を更新して反映します。