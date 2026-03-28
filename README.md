# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。ETL、ニュース収集・NLP、ファクター研究、監査ログなどを含むモジュール群を提供します。

---

## 概要

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、ニュース収集と LLM を使ったニュースセンチメント評価、ファクター計算、監査ログ（発注 → 約定のトレース）などを行うためのライブラリです。バックテストや本番自動売買の基盤として利用できるよう設計されています。Look-ahead バイアス対策や冪等性、フェイルセーフ動作を重視しています。

主な設計方針の例:
- DuckDB を用いたローカル DB（時系列データ格納）
- J-Quants API 用の堅牢なクライアント（レート制御・リトライ・トークンリフレッシュ）
- ニュース収集での SSRF 防止・サイズ制限
- OpenAI（gpt-4o-mini など）を用いたニュースセンチメント・市場レジーム判定（フェールセーフ付き）
- 監査ログテーブルによる完全トレース（UUID ベースの連鎖）

---

## 機能一覧

- 環境設定管理（.env 自動読み込み、必須設定の検証）
- J-Quants API クライアント（株価・財務・カレンダー取得、DuckDB への冪等保存）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS、URL 正規化、SSRF 対策、raw_news 保存）
- ニュース NLP（OpenAI を使った銘柄別センチメント → ai_scores テーブルへ保存）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- 監査ログ初期化ユーティリティ（signal_events, order_requests, executions テーブル）
- audit 用の独立した DuckDB 初期化関数

---

## 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib / json / logging 等を使用

（実運用では logger の設定や Slack 通知等を追加してください）

---

## セットアップ手順

1. Python 3.10 以上をインストール。

2. リポジトリをクローン（またはプロジェクトディレクトリへ移動）し、editable install（推奨）や必要パッケージをインストール:

   pip install -e .
   pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。

3. 環境変数を準備
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` と `.env.local` を置くと、自動で環境変数が読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で使用）。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack ボットトークン（通知を使う場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（通知を使う場合）
   - OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: environment（development / paper_trading / live）, デフォルト development
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）, デフォルト INFO

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（代表的な API）

以下は簡単な利用例です。適宜ログ設定や例外処理を追加してください。

- DuckDB に接続して日次 ETL を実行する:

  python スクリプト例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に書き込む:

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジームスコアを計算して market_regime に書き込む:

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用の DuckDB を初期化する:

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査テーブルへ読み書きできます
  ```

- 環境設定を参照する:

  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)
  print(settings.kabu_api_base_url)
  ```

メソッドの引数や返り値はそれぞれの docstring を参照してください。OpenAI の呼び出しは api_key を明示的に渡すか環境変数 `OPENAI_API_KEY` を設定してください。API 呼び出しはエラー時にフェールセーフ（多くのケースでスコアを 0.0 にフォールバック）を取る設計です。

---

## 自動環境変数読み込みの挙動

- ライブラリは import 時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env` を読み込みます。
- 読み込み順序:
  1. OS 環境変数（既定で優先）
  2. `.env.local`（存在すれば OS を上書きしない範囲で上書き）
  3. `.env`（既存の OS 環境変数を上書きしない）
- テストなどで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリが src レイアウトの場合の主要モジュール）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py               — ニュースの LLM スコアリング（ai_scores へ保存）
    - regime_detector.py        — 市場レジーム判定（ma200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得 + DuckDB への保存）
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - etl.py                    — ETL インターフェース（ETLResult）
    - news_collector.py         — RSS ニュース収集（raw_news 保存）
    - quality.py                — データ品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py                  — 共通統計ユーティリティ（zscore_normalize）
    - calendar_management.py    — 市場カレンダー管理 / 営業日判定
    - audit.py                  — 監査ログ（テーブル作成・初期化）
  - research/
    - __init__.py
    - factor_research.py        — Momentum/Volatility/Value のファクター計算
    - feature_exploration.py    — 将来リターン / IC / 統計サマリー等
  - research/（その他）
  - （strategy, execution, monitoring） — パッケージエクスポートに含まれるが実装の追加が必要な場合があります

主要に利用される DB テーブル（コード内で参照／生成されるもの）
- raw_prices / prices_daily
- raw_financials
- market_calendar
- raw_news / news_symbols / ai_scores
- market_regime
- signal_events / order_requests / executions（監査用）

---

## 注意点 / 運用上のヒント

- OpenAI の利用はコストとレート制限に注意してください。モデルとバッチサイズは news_nlp や regime_detector の定数で調整可能です。
- J-Quants API はレート制御とトークン管理を行っていますが、API 制限に従ってください。
- DuckDB スキーマ（テーブル定義）は ETL や audit.init_audit_schema を通して作成してください。スキーマ定義がリポジトリ内にあればスキーマ初期化スクリプトを用意してください。
- 本システムは Look-ahead バイアス回避を意識して設計されています（target_date 未満のデータしか参照しない等）。バックテストでの利用時はデータセットの準備方法にご注意ください。
- 自動読み込みされる .env のフォーマットは shell 風（export 対応、クォート・コメント対応）です。

---

## 開発 / 貢献

- コード規約やテストはプロジェクト内の方針に従ってください。
- テストでは自動 env ロードを無効にする（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）か、テスト用の一時 .env を使ってください。
- OpenAI / J-Quants 呼び出し部分はモック可能な設計（_call_openai_api の差し替え、jquants_client のレスポンスモック等）になっています。ユニットテストで外部 API をモックしてください。

---

README に書かれている機能や API は、ソースコードの docstring と実装を参照することでより詳細に理解できます。必要があれば各モジュールの使用例やテーブルスキーマ、運用手順を追加で作成します。