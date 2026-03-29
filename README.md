# KabuSys

日本株向け自動売買／データ基盤ライブラリ（KabuSys）

このリポジトリは、日本株のデータ取得（J-Quants）、ニュース収集、AI によるニュースセンチメント評価、ファクター計算、ETL パイプライン、監査ログ（発注→約定トレーサビリティ）などを含む日本株自動売買システム向けの共通モジュール群です。

主な設計方針:
- ルックアヘッドバイアスを避ける（date.today() 等の直接参照を最小化）
- DuckDB を用いたローカルデータプラットフォーム中心の設計
- 冪等（idempotent）な保存処理（ON CONFLICT / DELETE→INSERT など）
- 外部 API 呼び出しはリトライ／レート制御／フェイルセーフを実装
- ニュース収集時の SSRF 対策、XML パースの安全化（defusedxml）などセキュリティ配慮

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）と必須変数チェック
- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務、上場情報、マーケットカレンダー）
  - 差分 ETL / バックフィル / 品質チェック（欠損・重複・スパイク・日付整合性）
  - ETL の統合エントリ（run_daily_etl）
- ニュース処理 / AI
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_scores 書き込み）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
  - API 呼び出しは JSON Mode を使った厳格なレスポンス検証、リトライ処理
- リサーチ（研究）ユーティリティ
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン、IC（情報係数）、統計サマリー
  - Zスコア正規化ユーティリティ
- データ品質・カレンダー
  - 市場カレンダー管理、営業日判定、next/prev/trading days 取得
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルの定義・初期化
  - 監査 DB 初期化ユーティリティ（init_audit_db）
- その他ユーティリティ
  - 統計関数、URL 正規化、RSS の前処理など

---

## 必須環境変数

主に `kabusys.config.Settings` で参照される設定（少なくとも実行環境ではこれらの設定が必要です）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB 等）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動で `.env` / `.env.local` をプロジェクトルートから読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをチェックアウト
   - 例: `git clone <repo-url>`

2. Python 環境を作成（推奨: venv / pyenv-virtualenv）
   - python 3.10+ を想定

3. 依存パッケージをインストール
   - requirements ファイルがある場合はそれを使用してください。なければ以下の主要依存を参考にインストールします。
     - duckdb
     - openai（OpenAI SDK）
     - defusedxml
     - その他標準ライブラリ以外の依存があればプロジェクトの setup を参照

   例（仮）:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` を作成（`.env.example` を参考）し、上記の必須変数を設定します。
   - もしくは OS 環境変数として設定してください。

5. DuckDB / 監査 DB の初期化（オプション）
   - 監査 DB を初期化する（ファイルがなければ親ディレクトリを作成します）:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用のメイン DuckDB は設定 `DUCKDB_PATH` に従って利用します。

---

## 使い方（代表的な例）

以下はライブラリを直接 Python から呼ぶ基本例です。スクリプト／ジョブとして組み込んで使う想定です。

- DuckDB 接続を作る:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得・品質チェック）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（ai_scores）を算出:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数または api_key 引数で渡す
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} symbols")
  ```

- 市場レジーム評価:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- リサーチ用ファクターを計算:
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  value = calc_value(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  ```

- 監査ログスキーマを初期化（既存接続に追加）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- J-Quants から株価を直接取得（必要なら id_token を渡す）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  id_token = get_id_token()  # settings からリフレッシュトークン利用
  records = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,31))
  ```

注意点:
- AI 関連（score_news, score_regime）は OpenAI API を利用します。API キーと課金設定に注意してください。
- J-Quants API はレート制限と認証（リフレッシュトークン）を使用します。環境変数 `JQUANTS_REFRESH_TOKEN` を設定してください。
- ニュース収集は外部 URL を取得するため、実行環境のネットワークセキュリティポリシーを確認してください。モジュールは SSRF 対策やレスポンスサイズ制限を行っています。

---

## ディレクトリ構成（主なファイル）

（リポジトリの `src/kabusys` 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント解析（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL の公開インターフェース（ETLResult 再エクスポート）
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - news_collector.py      — RSS ニュース収集（SSRF 対策・前処理）
    - quality.py             — データ品質チェック
    - stats.py               — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログスキーマ定義 / 初期化
    - pipeline.py (上記)     — ETL 実行ロジック
  - research/
    - __init__.py
    - factor_research.py     — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py — forward returns / IC / rank / summary
  - ai/                      — AI 関連（news_nlp, regime_detector）

各モジュールはドメインごとに分離され、ユニットテストや運用ジョブから個別に呼び出せるよう設計されています。

---

## 運用上の注意 / セキュリティ

- OpenAI 呼び出しや外部 API 呼び出しはコストとレート制限が発生します。実行前に API キーや請求設定を確認してください。
- news_collector は URL 正規化・SSRF 対策・XML の defused パーサ使用・レスポンスサイズ制限などの対策を実装していますが、実行環境のプロキシ／ネットワークポリシー設定も確認してください。
- データの整合性・品質チェックを pipeline のオプションで有効にし、ETL 後の問題を監視してください。
- 監査ログ（order_requests / executions）は削除しない前提です。バックアップとディスク容量に注意してください。

---

## 付録: よく使う関数一覧（抜粋）

- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL のメイン
- kabusys.data.jquants_client.fetch_daily_quotes(...) — 日足データ取得
- kabusys.data.jquants_client.save_daily_quotes(...) — DuckDB への保存
- kabusys.ai.news_nlp.score_news(...) — ニュースセンチメント集計 & ai_scores 書き込み
- kabusys.ai.regime_detector.score_regime(...) — 市場レジーム判定 & market_regime 書き込み
- kabusys.data.audit.init_audit_db(...) — 監査用 DuckDB の初期化

---

README に書かれている挙動はソースコードのドキュメント文字列に基づいています。実際に運用する際は、環境変数・API キー・DB パスなどを適切に設定し、テスト環境で十分に検証してから本番環境へデプロイしてください。質問や補足が必要であればお知らせください。