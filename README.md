# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・LLM によるニュースセンチメント評価、ファクター計算、マーケットカレンダー管理、監査ログ（注文・約定トレース）など、投資・バックテスト・実運用に必要な基盤機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダー
  - ページネーション・レート制御・トークン自動更新・リトライ実装
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を ETLResult として集約
- ニュース収集
  - RSS フィード収集、前処理、raw_news への冪等保存（SSRF / Gzip / XML 爆弾対策あり）
- AI（LLM）モジュール
  - ニュースセンチメント（銘柄単位）を OpenAI（gpt-4o-mini）で評価（ai_scores へ保存）
  - マクロニュース + ETF MA200 乖離を合成して市場レジーム（bull/neutral/bear）を判定・保存
  - API 呼び出しのリトライやレスポンスバリデーション実装
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター算出
  - 将来リターン・IC（Information Coefficient）計算、Zスコア正規化ユーティリティ
- マーケットカレンダー管理
  - market_calendar の更新ジョブ、営業日判定ユーティリティ（next/prev/get）
- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブル定義・初期化
  - 発注・約定のトレーサビリティ（冪等キー、UTC タイムスタンプ）

---

## 動作要件

- Python 3.10+
- 主要依存（プロジェクトに合わせて適宜インストールしてください）
  - duckdb
  - openai（OpenAI の Python SDK）
  - defusedxml
  - その他標準ライブラリ

（パッケージ管理は pyproject.toml / requirements.txt に従ってください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール
   - 開発環境例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -e .  または  pip install -r requirements.txt

2. 環境変数（.env）の準備
   - プロジェクトルートに `.env` または `.env.local` を作成すると、パッケージ起動時に自動で読み込まれます（ただしテスト等で無効化可能）。
   - 自動ロードを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 必須の主な環境変数（詳細は下部の「環境変数一覧」参照）:
     - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
     - OPENAI_API_KEY（OpenAI API キー）※AI 機能を使う場合
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知に使用する場合）
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

3. DuckDB データベースの用意
   - デフォルトの DuckDB ファイルパスは `data/kabusys.duckdb`（settings.duckdb_path）。
   - 必要に応じてディレクトリを作成してください。多くの初期化関数は親ディレクトリを自動作成します。

4. 監査ログスキーマの初期化（任意）
   - 監査用 DB を別で用意する場合:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な例）

以下はライブラリの主要な関数の利用例です。適宜ログ設定やエラーハンドリングを追加してください。

- 共通準備（設定・DuckDB 接続）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコアを取得して ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数に設定していれば api_key=None で可
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（regime scoring）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログスキーマを初期化（既存の接続へ）
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn, transactional=True)
  ```

- 監査用 DB を新しく作って初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/monitoring_audit.duckdb")
  ```

- RSS を取得（ニュース収集のユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- マーケットカレンダー関連ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意:
- AI 関連関数（score_news / score_regime）は OpenAI API キーを要求します。api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定してください。
- OpenAI 呼び出しに失敗した場合はフェイルセーフとしてスコアを 0 や空スキップする実装が多く使われています（例: レスポンスパースエラー時など）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)  
  - J-Quants のリフレッシュトークン。ETL の認証に使用されます。
- OPENAI_API_KEY (AI 機能利用時に必須)  
  - OpenAI の API キー。score_news / score_regime などに必要。
- KABU_API_PASSWORD (必須)  
  - kabuステーション API 接続のパスワード（使用する場合）。
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (通知用)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)  
  - DuckDB ファイルのパス
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, デフォルト: development)  
  - 有効値: development, paper_trading, live
- LOG_LEVEL (任意, デフォルト: INFO)  
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、パッケージ起動時の .env 自動ロードを無効化します（テスト時に便利）。

.env の例はプロジェクトルートに `.env.example` を置いておくことを推奨します（このリポジトリではサンプルに合わせて編集してください）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースの LLM スコアリング（ai_scores 書き込み）
    - regime_detector.py         — マクロ + MA200 で市場レジーム判定（market_regime 書き込み）
  - data/
    - __init__.py
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult の再エクスポート
    - jquants_client.py          — J-Quants API クライアント・保存関数
    - news_collector.py          — RSS 取得・前処理・保存ユーティリティ
    - calendar_management.py     — 市場カレンダー管理・営業日判定
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                   — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py         — モメンタム/ボラ/バリュー等のファクター計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー等
  - research/* その他のユーティリティモジュール

（上記は主要モジュールのみを抜粋しています）

---

## 開発者向けメモ / 注意事項

- ルックアヘッドバイアス対策:
  - 多くの関数は内部で datetime.today() / date.today() を直接参照せず、引数で target_date を受け取る設計です。バックテストや再現性のある処理では target_date を明示的に指定してください。
- DuckDB との互換性:
  - 一部の executemany 呼び出しは DuckDB のバージョン差異（空リスト不可など）に配慮した実装になっています。DuckDB のバージョンに注意してください。
- テスト時のフック:
  - AI の HTTP 呼び出しや URL オープンなどは内部で関数を分離してあり、unittest.mock.patch で差し替え可能です（例: kabusys.ai.news_nlp._call_openai_api）。
- 自動 .env ロード:
  - config モジュールはプロジェクトルート（.git または pyproject.toml）を探索し、.env / .env.local を自動読み込みします。CI / テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

必要であれば、README に以下を追加できます:
- 具体的なテーブルスキーマ定義（raw_prices, raw_financials, raw_news, ai_scores, market_regime 等）
- サンプル .env.example
- CI / テストの実行方法
- デプロイ（本番・paper_trading 環境）時の運用手順

どの項目を追加したいか教えてください。