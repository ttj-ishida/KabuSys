# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）などの機能を提供します。

---

## 主な特徴（概要）

- J-Quants API 連携による日次株価 / 財務 / 市場カレンダーの差分ETL（レート制御・再試行・トークン自動リフレッシュ付き）
- RSS ベースのニュース収集と前処理（SSRF対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）と市場レジーム判定（market_regime）
- 研究用途のファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events / order_requests / executions）スキーマと初期化サポート
- DuckDB を中心としたオンプレミス / ローカル高速分析向けの設計

---

## 機能一覧（抜粋）

- kabusys.config: .env / 環境変数の自動ロードと設定アクセス（settings）
- kabusys.data.jquants_client: J-Quants API クライアント（fetch / save / token 管理）
- kabusys.data.pipeline & etl: 日次 ETL 実行（run_daily_etl など）と ETL 結果クラス
- kabusys.data.news_collector: RSS 収集・前処理・raw_news への保存ロジック
- kabusys.ai.news_nlp: OpenAI を用いた銘柄ごとのニュースセンチメント算出（score_news）
- kabusys.ai.regime_detector: ETF（1321）MA とマクロニュースで市場レジーム判定（score_regime）
- kabusys.research: ファクター計算・特徴量探索（calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary 等）
- kabusys.data.quality: データ品質チェック（run_all_checks 等）
- kabusys.data.audit: 監査ログスキーマ初期化ユーティリティ（init_audit_schema / init_audit_db）
- kabusys.data.calendar_management: JPX カレンダー管理と営業日ユーティリティ

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | 演算子等を使用）
- システムに必要な外部ライブラリ（下記参照）

1. リポジトリをクローン
   - git clone ...（省略）

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクト配布に requirements.txt があれば pip install -r requirements.txt を使用）

4. パッケージとしてインストール（開発モード）
   - pip install -e src

5. 環境変数 / .env の準備
   - プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config が自動ロード）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

推奨設定例（.env）:
- JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token_
- OPENAI_API_KEY=あなたの_openai_api_key_
- KABU_API_PASSWORD=kabuステーション接続用パスワード
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LINE_CHANNEL_ACCESS_TOKEN=（任意）LINE 通知用
- LINE_USER_ID=（任意）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|...

.env ファイル内の読み込み仕様は kabusys.config がサポート（export 形式・クォート処理・コメント処理等）。

---

## 使い方（代表的な例）

以下に代表的な処理の使用例を示します。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

1) DuckDB 接続を開き日次 ETL を実行する（run_daily_etl）
- 目的: 株価・財務・市場カレンダーを差分取得して保存し品質チェックを行う

Python スクリプト例:
- from datetime import date
- import duckdb
- from kabusys.data.pipeline import run_daily_etl
- from kabusys.config import settings
- conn = duckdb.connect(str(settings.duckdb_path))
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

2) ニュースセンチメントを算出して ai_scores に保存（score_news）
- from datetime import date
- import duckdb
- from kabusys.ai.news_nlp import score_news
- from kabusys.config import settings
- conn = duckdb.connect(str(settings.duckdb_path))
- n_written = score_news(conn, target_date=date(2026, 3, 20))  # returns 書込銘柄数

3) 市場レジーム判定を実行（score_regime）
- from datetime import date
- import duckdb
- from kabusys.ai.regime_detector import score_regime
- from kabusys.config import settings
- conn = duckdb.connect(str(settings.duckdb_path))
- score_regime(conn, target_date=date(2026, 3, 20))

4) 監査ログ DB の初期化（監査専用 DB 作成）
- from kabusys.data.audit import init_audit_db
- conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
- # 必要なら conn を使ってクエリ・確認

5) jquants_client の直接利用例
- from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
- token = get_id_token()  # settings.jquants_refresh_token を利用して取得
- records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))
- conn = duckdb.connect(str(settings.duckdb_path))
- save_daily_quotes(conn, records)

注意:
- OpenAI 呼び出しは API キーが必要です（環境変数 OPENAI_API_KEY または関数引数で注入可能）。
- DuckDB の接続はスレッド間で共有する場合の注意点やトランザクション制御に注意してください（モジュール内でも明示的に BEGIN/COMMIT を使う箇所があります）。

---

## 主要 API（抜粋）

- kabusys.config.settings: 各種設定プロパティ（jquants_refresh_token / kabu_api_password / duckdb_path 等）
- kabusys.data.pipeline.run_daily_etl(conn, target_date, id_token=None, ...)
- kabusys.data.pipeline.ETLResult: ETL 実行結果クラス
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.jquants_client.get_id_token(refresh_token=None)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.audit.init_audit_db(db_path) / init_audit_schema(conn)

各関数は docstring に詳細な使用方法・引数・返り値・例外条件が記載されていますので、実装を参照してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数 / .env の自動ロードと Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント & DuckDB 保存
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py — ETL インターフェース再エクスポート
  - news_collector.py — RSS 取得・前処理・保存
  - calendar_management.py — JPX カレンダー管理 / 営業日ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログスキーマ定義と初期化
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

（上記は主要モジュールの一覧です。詳細は各モジュールの docstring を参照してください。）

---

## 運用上の注意 / ベストプラクティス

- 環境: production（本番）実行時は KABUSYS_ENV を `live` に設定してください。設定値チェックにより誤設定が検出されます。
- キー保護: .env に機密情報を置く場合はリポジトリにコミットしないでください。`.env.local` を使用してローカル上書きも可能です。
- リトライとフォールバック: OpenAI や J-Quants API 呼び出しはリトライやフェイルセーフ（失敗時はスコア 0.0 やスキップ）を導入しており、部分失敗でも処理継続する設計です。
- Look-ahead バイアス対策: モジュール内はバックテストでのルックアヘッドバイアスを避けるため、target_date を明示的に渡す設計になっています。date.today() 等に依存しません。
- DuckDB の executemany 空配列制約: 一部の保存処理は executemany に空リストを渡さないようガードしています（DuckDB 互換性対策）。

---

## 参考（トラブルシューティング）

- .env が読み込まれない: プロジェクトルートの検出は `pyproject.toml` または `.git` を基準に行います。テスト環境や一時的に自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- OpenAI API エラー時: レート制限・ネットワーク断・サーバーエラーは内部でリトライしますが、API キーやクォータを確認してください。エラーの多い場合はバッチサイズ等を調整してください。
- J-Quants 認証エラー（401）: jquants_client は 401 を検出すると自動でリフレッシュを試行しますが、refresh token が無効な場合は更新に失敗します。`JQUANTS_REFRESH_TOKEN` の有効性を確認してください。

---

必要であれば README にさらに具体的なコマンド例（systemd ユニット、cron / Airflow の実行例、Dockerfile など）や `.env.example` のテンプレートを追加できます。どの情報が必要か教えてください。