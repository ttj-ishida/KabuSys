# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログの初期化などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を備えています。

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得（ETL）
- RSS ニュース収集とテキスト前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores）とマクロセンチメント合成による市場レジーム判定
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal_events / order_requests / executions）用スキーマの初期化・専用 DB 作成ユーティリティ
- 環境変数管理（.env 自動読み込み機能を持つ設定）

設計上、バックテストやバッチ処理での「ルックアヘッドバイアス」を防ぐ実装方針が徹底されています（date.today() / datetime.today() を不用意に参照しない等）。

---

## 主な機能一覧

- ETL
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）
- データ品質
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks（kabusys.data.quality）
- ニュース
  - RSS 取得・前処理・記事ID正規化（kabusys.data.news_collector）
  - news_nlp.score_news（OpenAI による銘柄別ニューススコアリング）
- AI / レジーム判定
  - ai.regime_detector.score_regime（MA200 とマクロセンチメント合成）
- 研究用ユーティリティ
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize
- 監査ログ（監査スキーマ初期化）
  - data.audit.init_audit_schema / init_audit_db

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. Python 環境を用意（推奨: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要なパッケージをインストール
   必要最小限の外部依存:
   - duckdb
   - openai
   - defusedxml

   例:
   ```bash
   pip install duckdb openai defusedxml
   ```

   （プロジェクトによっては追加依存がある場合があります。requirements.txt があればそれを使用してください。）

4. 環境変数の設定
   ルートに `.env`（または `.env.local`）を置くと自動的に読み込まれます（プロジェクトルートは .git または pyproject.toml を基準に探します）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（利用機能により必須項目は異なります）:
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（ETL）
   - KABU_API_PASSWORD : kabu ステーション API パスワード（発注系）
   - SLACK_BOT_TOKEN : Slack 通知（任意）
   - SLACK_CHANNEL_ID : Slack 通知（任意）
   - OPENAI_API_KEY : OpenAI（news_nlp / regime_detector を利用する場合）

   デフォルトパス（環境変数未設定時）:
   - DUCKDB_PATH : data/kabusys.duckdb
   - SQLITE_PATH : data/monitoring.db
   - PID_FILE_PATH : data/execution.pid

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要ユースケース）

以下は Python から直接呼び出す利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の返り値）を引数に取ることが多い点に注意してください。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- マーケットレジーム判定（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用途）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作成）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は initialized な DuckDB 接続
  ```

- データ品質チェック
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.quality import run_all_checks

  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

注意:
- OpenAI を使用する関数は API レスポンスの不安定さを考慮し、フェイルセーフ（失敗時は 0.0 にフォールバック、あるいはスキップ）設計になっていますが、API キーは必須です。
- J-Quants API 利用はトークン（JQUANTS_REFRESH_TOKEN）を用いた認証が必要です。

---

## 自動環境変数読み込みについて

- モジュール `kabusys.config` はプロジェクトルート（.git または pyproject.toml の場所）を探索し、`.env` → `.env.local` の順で自動読み込みします。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きできます。
- 自動読み込みを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください（テスト時に便利です）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル/モジュールの構成です。実際のツリーは src/kabusys 配下にまとまっています。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLU / OpenAI 呼び出し
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS 収集・前処理
    - quality.py             — データ品質チェック
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査ログスキーマ初期化
    - etl.py                 — ETLResult 再エクスポート
    - stats.py               — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - research/...             — 研究用ユーティリティ群
  - その他:
    - data/（データ用ディレクトリにデフォルトで DB を作る想定）

---

## 注意事項 / 運用上のポイント

- セキュリティ
  - news_collector は SSRF 対策・受信サイズ制限・XML パースの安全化（defusedxml）を実装しています。外部 URL 取得の前にスキームやプライベート IP を検証します。
- リトライ / レート制御
  - J-Quants クライアントは 120 req/min のレート制限に従う固定間隔スロットリングを行います。OpenAI コールはリトライと exponential backoff を実装しています。
- ルックアヘッドバイアス防止
  - 日付を扱う機能は、内部で現在時刻を無条件に参照することを避け、引数で与えた target_date に基づいて安全に動作します。バッチやバックテスト時はこれを活用してください。
- DB 互換性
  - DuckDB のバージョン差異に備えた実装（executemany の空リスト扱いなど）に配慮していますが、使用する DuckDB のバージョンと挙動は確認してください。

---

## 追加情報・開発者向け

- 自動ロードされる .env のパースはシェルスタイル（export KEY=val、クォート対応、コメント対応）をサポートします。
- テスト時は環境変数の自動ロードを無効化して、明示的に settings を差し替えるかモックしてください。
- OpenAI 呼び出し部分はテストで差し替え可能なよう、モジュール内でラッパー関数（_call_openai_api）を用意しています。unittest.mock.patch で差し替えてテスト可能です。

---

この README はソース内のドキュメント文字列と設計コメントを要約したものです。各モジュールの詳細な使い方や取得できるテーブルスキーマ等は、ソースコード内の docstring を参照してください。必要であれば、導入手順や運用ガイド、API キーの取得方法などを追記します。