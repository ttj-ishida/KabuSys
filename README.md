# KabuSys README

バージョン: 0.1.0

KabuSys は日本株のデータパイプライン、機械学習（NLP/LLM）ベースのニュース評価、リサーチ・ファクター計算、監査ログ管理、ETL を備えた自動売買・リサーチ基盤の Python モジュール群です。本リポジトリは主に DuckDB をデータレイヤに使用し、J-Quants API / RSS / OpenAI など外部サービスと連携してデータ収集・品質チェック・特徴量生成を行います。

主な目的:
- 日次 ETL による株価・財務・市場カレンダー収集と品質チェック
- ニュース（RSS）収集→LLM による銘柄センチメント算出
- マクロニュース + ETF MA200 乖離を用いた市場レジーム判定
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 発注・約定に向けた監査ログ（トレーサビリティ）管理

---

## 機能一覧

- 設定管理
  - .env / 環境変数自動読み込み（プロジェクトルートを検出）
  - 必須環境変数チェック
- Data（kabusys.data）
  - J-Quants API クライアント（rate limit / リトライ / トークン自動リフレッシュ）
  - ETL パイプライン（差分取得・保存・品質チェック）
  - 市場カレンダー管理（営業日判定・更新ジョブ）
  - ニュース収集（RSS）と前処理（SSRF 対策・サイズ制御）
  - 監査ログスキーマ初期化（signal / order_request / executions）
  - 汎用統計ユーティリティ（Zスコア正規化 等）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- AI（kabusys.ai）
  - ニュース NLP（gpt-4o-mini による銘柄センチメント scoring）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロ LLM 評価の合成）
- Research（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（情報係数）、統計サマリー
- 監査・トレーサビリティ
  - 監査用 DuckDB 初期化ユーティリティ（init_audit_db / init_audit_schema）

---

## 必要な環境変数

以下はコード内で参照される主な環境変数です（.env に記載して運用する想定）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（取引 API を使用する場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack のチャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（モニタリング用途、デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")
- OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合は環境変数か関数引数で渡すことが可能）

自動 .env 読み込み:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を検出して
  - .env を読み込み（OS 環境優先）
  - .env.local を上書き読み込み
- 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - Linux/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

2. 依存ライブラリをインストール
   - 必須ライブラリ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば）
     pip install -r requirements.txt

3. .env 作成
   - プロジェクトルートに .env（と必要なら .env.local）を作成し、上記必須変数を設定
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...

4. DuckDB 初期化（任意: 監査 DB）
   - 監査ログ用 DB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

5. 注意点
   - OPENAI を利用する機能は API 利用料がかかります。テスト時は api_key 引数に短時間用キーを渡すか、モックすることを推奨します。
   - J-Quants の API 利用にはアカウントとトークンが必要です。

---

## 使い方（代表的な例）

以下は簡単なコード例です。DuckDB 接続を作成して ETL・AI・リサーチ関数を呼び出す流れを示します。

- 日次 ETL 実行（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定済みであること
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")
  ```

  または API キーを直接渡す:
  score_news(conn, target_date=date(2026,3,20), api_key="sk-...")

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))

  # Z スコア標準化
  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 監査スキーマ初期化（既存接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  # 既に conn がある場合
  init_audit_schema(conn, transactional=True)
  ```

---

## よく使う API の説明（補足）

- settings（kabusys.config.settings）
  - settings.jquants_refresh_token / settings.kabu_api_password / settings.slack_bot_token などで環境設定へアクセスできます。
  - settings.env は "development", "paper_trading", "live" のいずれかで、settings.is_live 等のブールも用意。

- jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar で J-Quants からデータを取得
  - save_daily_quotes / save_financial_statements / save_market_calendar で DuckDB へ冪等保存

- news_collector
  - fetch_rss(url, source) で RSS を取得して前処理（SSRF/サイズ/圧縮対応）した記事リストを返す
  - 内部で記事 ID 正規化（URL 正規化 → SHA256）を行うため冪等性あり

- AI モジュール
  - LLM 呼び出しは OpenAI の Chat Completions（gpt-4o-mini）を JSON mode で使う設計
  - API 呼び出し失敗はフェイルセーフ（多くは 0.0 にフォールバック）となる箇所があるが、キー未設定は ValueError を投げる

---

## 典型的な運用フロー（例）

1. .env で J-Quants / OpenAI / Slack 等のキーを設定
2. 日次バッチで run_daily_etl を実行
   - カレンダー更新 → 株価差分取得 → 財務差分取得 → 品質チェック
3. ニュース収集ジョブで raw_news を更新、score_news で ai_scores を更新
4. score_regime を実行して market_regime を更新
5. 戦略が signal を生成 → order_requests を作成 → 発注フロー（ここには発注用モジュールを組み合わせ）
6. executions を受け取り監査ログを保存、Slack 通知などで監視

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys）:

- __init__.py
- config.py — 環境変数・設定管理（自動 .env 読み込み含む）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（銘柄センチメント）
  - regime_detector.py — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — ETL パイプライン・run_daily_etl 等
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 取得・前処理
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - quality.py — データ品質チェック
  - stats.py — 統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログスキーマ初期化・DB 初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

（プロジェクトルート）
- .env（運用環境で追加）
- .env.local（環境固有上書き）
- pyproject.toml / setup.cfg / requirements.txt（存在する場合）

---

## トラブルシューティング

- 環境変数が読み込まれない
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を検出して .env を自動読み込みします。テスト等で自動読み込みを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出し・API キーエラー
  - OPENAI_API_KEY を環境変数に設定するか、各関数の api_key 引数にキーを渡してください。API エラーは多くの場合フェイルセーフ（0.0 返却）として扱われますが、キー未設定時は ValueError が発生します。
- DuckDB のテーブルがない
  - ETL/保存関数は既存のテーブル構造を前提に動きます。初回はスキーマ初期化用スクリプト（プロジェクトの別モジュールなど）でテーブルを作成してください。監査ログは init_audit_db で初期化できます。

---

以上。必要であれば利用例や追加のドキュメント（API リファレンス、運用手順、CI/CD、cron ジョブサンプル、スキーマ定義）を追加で作成します。どの部分の詳細を優先してほしいか教えてください。