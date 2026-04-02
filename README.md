# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリセットです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（LLMによるセンチメント）、市場レジーム判定、リサーチ（ファクター計算）および監査ログ用スキーマを提供します。

---

## 特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ユーティリティ（`kabusys.config.settings`）
- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPXマーケットカレンダーのフェッチ（ページネーション対応）
  - レート制御、再試行、ID トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得、バックフィル、品質チェック（欠損・重複・スパイク・日付整合性）
  - 結果は `ETLResult` オブジェクトで返却
- ニュース収集・NLP
  - RSS 収集（SSRF対策、URL正規化、トラッキングパラメータ除去）と raw_news への保存
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（`score_news`）
  - チャンク・リトライ・レスポンス検証を含む安全な呼び出し
- 市場レジーム判定
  - ETF（1321）200日MA乖離とマクロニュースセンチメントを合成して日次レジームを算出（`score_regime`）
  - LLM を用いる場合のフォールバックとリトライを実装
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査スキーマの初期化（DuckDB）
  - 冪等キー・作成日 timestamp（UTC）・インデックス定義を含む

---

## 動作環境・依存関係

- 推奨 Python バージョン: 3.10+
  - （Union 型 `X | Y` を使用しているため）
- 主な依存ライブラリ
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリの urllib 等を多用）

インストール例（プロジェクトとして扱う場合）:
- 開発中にローカルで使う場合:
  - pip install -e . あるいは必要な依存だけ入れる:
    - pip install duckdb openai defusedxml

---

## セットアップ手順

1. Python（3.10+）の仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに setup.py / pyproject.toml がある場合）
   - pip install -e .

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）に `.env` / `.env.local` を配置すると自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（主要なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
   - SLACK_BOT_TOKEN        : Slack 通知に使用する Bot トークン（必要なら）
   - SLACK_CHANNEL_ID       : Slack 通知先チャンネル ID（必要なら）
   - KABU_API_PASSWORD      : kabuステーション API を使う場合のパスワード

   任意・デフォルト値があるもの
   - KABUSYS_ENV            : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL              : DEBUG / INFO / ...（デフォルト: INFO）
   - OPENAI_API_KEY         : OpenAI を使う処理でデフォルト参照されるキー
   - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            : 監視用 SQLite（デフォルト: data/monitoring.db）

   ※ 必須変数は `kabusys.config.settings` 経由で取得され、未設定時は ValueError を送出します。

4. DuckDB データベースおよび監査DBを初期化（必要に応じて）
   - 監査用 DB 初期化例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - ETL 用のスキーマ初期化はプロジェクト内の schema 初期化ロジックに従ってください（本コードベースの schema 初期化関数等）。

---

## 使い方（よく使うユースケースの例）

以下はパイソンREPL やスクリプトから呼ぶ簡単な例です。

1. 環境設定の参照
   - from kabusys.config import settings
   - settings.jquants_refresh_token
   - settings.duckdb_path  # Path オブジェクト

2. DuckDB 接続を作る
   - import duckdb
   - from kabusys.config import settings
   - conn = duckdb.connect(str(settings.duckdb_path))

3. 日次ETL を実行する
   - from kabusys.data.pipeline import run_daily_etl
   - from datetime import date
   - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   - print(result.to_dict())

   ETL は以下を順に実行します：
   - カレンダー ETL（J-Quants から market_calendar を取得）
   - 株価 ETL（raw_prices）
   - 財務 ETL（raw_financials）
   - 品質チェック（run_quality_checks=True の場合）

4. ニュースセンチメントを算出して ai_scores に書き込む
   - from kabusys.ai.news_nlp import score_news
   - from datetime import date
   - n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key を渡すか OPENAI_API_KEY を env に置く
   - print(f"scored {n} codes")

   - 注意: API 呼び出し失敗時はフェイルセーフでスコアをスキップする設計です。

5. 市場レジーム（日次）を算出する
   - from kabusys.ai.regime_detector import score_regime
   - score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

6. 監査スキーマを初期化する（監査用テーブルを追加）
   - from kabusys.data.audit import init_audit_schema, init_audit_db
   - # 既存接続に対してスキーマを追加する場合:
   - init_audit_schema(conn, transactional=True)
   - # 監査専用 DB を作る（ファイルを作成）
   - audit_conn = init_audit_db("data/audit.duckdb")

7. 研究用ユーティリティ例
   - from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
   - momentum = calc_momentum(conn, target_date=date(2026,3,20))
   - normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

---

## 開発・テストのヒント

- LLM 呼び出しは内部で `_call_openai_api` を使っており、ユニットテスト時はモック（patch）で差し替え可能です。
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")
- .env の自動ロードを無効化したいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany に空リストバインドが許されないバージョン対策が各所にあります。テスト用にインメモリ DB (`":memory:"`) を使用できます。
  - init_audit_db(":memory:")

---

## ディレクトリ構成

（主要ファイル・ディレクトリのみ。src 配下にパッケージがある想定）

- src/kabusys/
  - __init__.py                — パッケージ定義（version 等）
  - config.py                  — 環境変数・設定管理（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch_*, save_*）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETL 結果型の公開
    - news_collector.py        — RSS 収集・前処理
    - calendar_management.py   — マーケットカレンダー管理（is_trading_day 等）
    - quality.py               — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                 — 基本統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査スキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン・IC・統計サマリ等

---

## 注意事項 / セキュリティ

- OpenAI / J-Quants の API キーは厳重に管理してください。リポジトリにキーを含めないでください。
- news_collector は外部 URL をフェッチします。SSRF 対策・受信サイズ制限を実装していますが、運用時はネットワークポリシー等も検討してください。
- 実際の発注機能（kabuステーション等）を組み合わせる際は、ライブ口座での動作確認・リスク管理を十分に行ってください。KABUSYS_ENV を切り替えて paper_trading / live を明示してください。
- DuckDB ファイルの権限管理やバックアップを検討してください。

---

もし README に追記したいコマンド（CLI 例や docker-compose 等）があれば、プロジェクトの運用フローに合わせて具体的に追記します。必要なセクション（例: デプロイ手順、CI 設定、サンプル .env.example）も作成できますので指示ください。