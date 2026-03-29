# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）・ニュース収集・AI ベースのニュース/レジーム評価・研究用ファクター計算・監査ログなど、バックテスト・運用に必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の機能群を備えた Python パッケージです。

- J-Quants API との対話（株価・財務・カレンダー取得、保存）
- DuckDB を用いたローカルデータ格納・ETL パイプライン
- RSS ベースのニュース収集と前処理（SSRF / Gzip / トラッキング除去対策）
- OpenAI（gpt-4o-mini） を使ったニュースセンチメント / 市場レジーム判定
- 研究用のファクター計算（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution のトレース用テーブル群）
- 環境設定管理（.env 自動読込、必須キーチェック）

設計上のポイント：
- ルックアヘッドバイアスに配慮（内部で datetime.today()/date.today() を不用意に参照しない）
- 冪等性（DB 保存は ON CONFLICT / DELETE→INSERT の形で上書き）を重視
- 外部 API 呼び出しはリトライ・バックオフを備えフェイルセーフ設計

---

## 主な機能一覧

- data.jquants_client
  - J-Quants からのデータ取得 / DuckDB への保存（raw_prices, raw_financials, market_calendar 等）
  - get_id_token（token refresh）、fetch / save 関数、rate limiter
- data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果を表す ETLResult
- data.news_collector
  - RSS フィードの取得、テキスト前処理、記事ID生成、raw_news への保存ロジック
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- data.audit
  - 監査用テーブル定義・初期化（init_audit_schema / init_audit_db）
- data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）
- research.*
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank（研究・ファクター分析用）
- ai.news_nlp
  - score_news: ニュース記事群を OpenAI に送り銘柄ごとの ai_score を ai_scores テーブルへ保存
- ai.regime_detector
  - score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime を更新
- config
  - Settings クラス: 環境変数から必要な設定を提供。自動 .env 読込機能あり。

---

## セットアップ手順

前提:
- Python 3.10+ を推奨
- DuckDB を使用（パッケージ依存）

1. リポジトリをクローンしてパッケージをインストール（開発モード）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -e .

2. 依存ライブラリ（必要に応じて）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（config モジュールの自動ロード）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabuステーション API パスワード（本パッケージの一部と連携する場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に使用する場合
   - OPENAI_API_KEY: OpenAI 呼び出しに必要（ai/news_nlp.py, ai/regime_detector.py を使用する場合）

   追加（任意・デフォルトあり）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

5. .env の例（プロジェクトルートに .env を作成）
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（代表的な例）

以下は簡単な利用例です。パス・日付は適宜置き換えてください。

- DuckDB 接続を作成して ETL を回す
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（target_date の前日 15:00 JST〜当日 08:30 JST のウィンドウ）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", count)
  ```

- 市場レジームの算出（ETF 1321 の MA200 とマクロニュースを統合）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
  ```

- カレンダー関連
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print("is trading:", is_trading_day(conn, d))
  print("next trading:", next_trading_day(conn, d))
  ```

- 研究モジュール（ファクター計算）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点:
- OpenAI 呼び出しを伴う機能には `OPENAI_API_KEY` が必要です。API のレートやコストに注意してください。
- ETL / AI 関連処理では外部 API 呼び出しに対するリトライやフェイルセーフが組み込まれていますが、実行時のログを確認して挙動を把握してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (AI 機能利用時必須)
- KABU_API_PASSWORD (kabu ステーション連携時)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — 環境モード
- LOG_LEVEL (INFO 等)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動読み込みを無効化

設定はプロジェクトルートの `.env` / `.env.local` に記述できます。config モジュールはプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索して自動的に読み込みます。

---

## ディレクトリ構成

主要ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP スコアリング（score_news）
    - regime_detector.py               — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（fetch/save）
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETLResult の再エクスポート
    - news_collector.py                — RSS ニュース収集
    - quality.py                       — 品質チェック
    - calendar_management.py           — 市場カレンダー管理
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査ログ定義・初期化
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算（momentum/value/volatility）
    - feature_exploration.py           — 将来リターン計算・IC・統計サマリー
  - monitoring/ (パッケージ想定)      — 監視・アラート等（コードベースにより存在）
  - strategy/ (パッケージ想定)        — 戦略実装レイヤ（コードベースにより存在）
  - execution/ (パッケージ想定)       — 発注・ブローカー連携（コードベースにより存在）

（実装済みのファイルと設計ドキュメントが混在しています。上記は現在の実装に基づく主要モジュールの一覧です）

---

## ログ・デバッグ

- LOG_LEVEL 環境変数でログレベルを制御できます（例: LOG_LEVEL=DEBUG）。
- DuckDB クエリログ等の詳細が必要な場合は、呼び出し側でロガー設定を上書きしてください。

---

## 注意事項 / 運用メモ

- 本パッケージには実際の売買や証券会社 API 連携機能のスケルトンが含まれます。実運用で利用する場合は、発注ロジック・リスク管理・認証情報保護を厳格に実装してください。
- OpenAI / J-Quants の利用は各サービスの利用規約・レート制限・コストに従ってください。
- DuckDB を永続化する場合はバックアップ方針を検討してください（監査ログは削除しない設計を想定）。
- テスト時は環境自動読込を無効化するか、モックを使用してください（config に KABUSYS_DISABLE_AUTO_ENV_LOAD オプションあり）。

---

必要であれば、README に記載するサンプル .env.example、さらに詳細な API リファレンス（各関数の引数説明・戻り値）や実運用チェックリストも作成します。どの追加情報が必要か教えてください。