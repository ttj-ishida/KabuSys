# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。J-Quants API を用いたデータ ETL、ニュースの NLP による銘柄センチメント評価、マーケットレジーム判定、ファクター計算、品質チェック、監査ログ（トレーサビリティ）など、運用・リサーチに必要な機能をモジュール化して提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境変数と `.env` の自動読み込み・設定管理（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、マーケットカレンダー取得
  - レートリミット制御・トークン自動リフレッシュ・再試行ロジックを実装
  - DuckDB へ冪等保存（ON CONFLICT を利用）
- ETL パイプライン（差分取得、バックフィル、品質チェック（欠損、スパイク、重複、日付不整合））
- マーケットカレンダー管理（営業日判定、前後営業日の取得、夜間バッチ更新）
- ニュース収集（RSS）と前処理（URL 正規化、SSRF 対策、サイズ制限）
- ニュース NLP（OpenAI を利用）による銘柄ごとのセンチメントスコア付与（ai_scores テーブル）
- マクロニュース + ETF（1321）の MA200 を合成した市場レジーム判定（bull / neutral / bear）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ（Z-score 等）
- 監査ログ（signal_events / order_requests / executions）スキーマの初期化ユーティリティ（監査・トレーサビリティ確保）
- DuckDB を中心とした軽量ローカル DB を想定

---

## 必要要件

- Python 3.10+
- 主要依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトの pyproject.toml / requirements.txt がある場合はそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン／プロジェクトを配置
2. 仮想環境の作成と依存インストール（例）
   ```
   python -m venv .venv
   source .venv/bin/activate    # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb openai defusedxml
   # あるいはローカル開発用にパッケージを editable install:
   # pip install -e .
   ```
3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数の例（config.py を参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - OPENAI_API_KEY（AI 機能利用時）
   - オプション/デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

4. データベース初期化（監査ログなど）
   - 監査ログスキーマを初期化する例（Python）:
     ```py
     import duckdb
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db(settings.duckdb_path)  # ファイルを作成してスキーマを作る
     # または既存の duckdb.connect(settings.duckdb_path) を渡して init_audit_schema を呼ぶ
     ```

---

## 使い方（クイックスタート）

以下は主要ユーティリティの使用例です。すべて Python から呼び出す想定です。

- 共通準備: DuckDB 接続と settings
  ```py
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（差分取得＋品質チェック）
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date.today(), id_token=None)
  print(result.to_dict())
  ```

- ニュース NLP スコア付与（ai_scores へ書き込み）
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数に設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（market_regime へ書き込み）
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  r = score_regime(conn, target_date=date(2026, 3, 20))
  print("結果コード:", r)
  ```

- リサーチ：ファクター計算
  ```py
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

- 品質チェックを個別に実行
  ```py
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

- RSS 取得（ニュース収集の低レベル）
  ```py
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意点:
- OpenAI を利用する処理（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。API の呼び出しはリトライ・エクスポネンシャルバックオフ・JSON バリデーション等の堅牢化がされていますが、API 使用に伴うコストに注意してください。
- ETL / データ取得は外部 API（J-Quants）を使います。J-Quants の認証情報（JQUANTS_REFRESH_TOKEN）を用意してください。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード（発注などで使用）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャネル ID
- OPENAI_API_KEY — OpenAI API キー（AI 関連機能で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パスなど（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live
- LOG_LEVEL — ログレベル
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 `.env` ロードを無効化する (値が存在すると無効化)

例: .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=yourpassword
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
```

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ公開（version, subpackages）
  - config.py — 環境変数 / .env の自動読み込み、設定オブジェクト（settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメントを OpenAI で評価し ai_scores に書き込む
    - regime_detector.py — ETF（1321）MA200 とマクロニュースを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得関数・保存関数）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py — ETL インターフェースの再エクスポート
    - news_collector.py — RSS 収集、前処理、SSRF 対策
    - calendar_management.py — マーケットカレンダー管理・営業日判定・calendar_update_job
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合等）
    - audit.py — 監査ログスキーマ定義・初期化（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー 等のファクター計算
    - feature_exploration.py — 将来リターン、IC 計算、統計サマリー、ランク関数
  - monitoring/, strategy/, execution/, etc. — パッケージ __all__ に含まれるが、この抜粋では詳細は省略

（上記はコード抜粋に基づく主要モジュール一覧です。実際のリポジトリでは追加ファイルが存在する可能性があります）

---

## 運用上の注意

- Look-ahead bias 回避のため、多くの関数は内部で date.today() / datetime.today() を直接参照せず、明示的な target_date 引数を受け取ります。バックテストや再現性ある運用では target_date を明示して利用してください。
- DuckDB の executemany に空リストを渡すとバージョン依存でエラーになるため、コード側で空チェックを行っています（pipeline / ai modules 内で対策済み）。
- OpenAI / J-Quants の API キーは適切に管理してください。自動ロード時に OS 環境変数が優先されます。
- ニュース収集は外部 RSS をパースするため、defusedxml による安全対策、SSRF・サイズ制限など複数の保護を実装していますが、運用時はフィード先ホワイトリスト化等の追加対策を推奨します。

---

## 貢献 / テスト

- モジュールはユニットテストが容易な作り（API 呼び出しは差し替え可能な内部関数設計）になっています。テストを書く場合は各種 API 呼び出しポイント（OpenAI 呼び出し、HTTP クライアント、jquants_client._request 等）をモックしてください。
- ローカルでの開発・検証は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い、テスト用の環境変数を明示的に設定すると再現性が高まります。

---

必要であれば README に以下の追加情報も追記します：
- 具体的な pyproject.toml / setup 手順
- 例となる .env.example（テンプレート）
- データベースのスキーマ（DDL）一覧
- Slack 通知や発注フロー（execution / monitoring）に関するサンプルスクリプト

どの情報を追加したいか教えてください。