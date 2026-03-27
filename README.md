# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants / kabuステーション / OpenAI を組み合わせたデータ取得・ETL・品質チェック・ニュースNLP・市場レジーム判定・監査ログ用ユーティリティを提供します。

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群を含みます。

- J-Quants API から株価・財務・マーケットカレンダー等を取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と OpenAI を利用した銘柄別ニュースセンチメントスコアリング
- ETF（1321）の長期移動平均とマクロニュースの LLM センチメントを組み合わせた市場レジーム判定
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）を格納するスキーマ初期化ユーティリティ
- 研究用のファクター計算・特徴量解析ユーティリティ

パッケージはモジュール単位で分かれており、バッチ ETL・モデル開発・取引実行フローの各段階で再利用可能な API を提供します。

---

## 主な機能一覧

- 環境変数管理（.env 自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB への冪等保存（ON CONFLICT / INSERT ... DO UPDATE）
- ETL パイプライン（run_daily_etl / 個別 ETL ジョブ）
- ニュース収集（RSS、SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（gpt-4o-mini を用いた銘柄別センチメント、バッチ処理／リトライ）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントの合成）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログスキーマ初期化 / 監査用 DB 作成ユーティリティ
- 研究ユーティリティ（モメンタム・ボラティリティ・バリュー等のファクター計算、Zスコア正規化、IC 計算）

---

## セットアップ手順（開発用）

1. Python 仮想環境を作成・有効化（例: Python 3.9+ 推奨）
   - ※プロジェクトの pyproject.toml/requirements を用意している場合はそれに従ってください。

2. 必要なパッケージをインストール（代表的な依存）
   ```
   pip install duckdb openai defusedxml
   ```
   （実際の依存はプロジェクトの packaging / requirements を参照してください）

3. パッケージをローカルにインストール（開発時）
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - ルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（起動時）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
     - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime のデフォルト）
     - KABU_API_PASSWORD : kabuステーション API パスワード（発注等で使用）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : モニタリング用 Slack 通知設定
   - オプション / デフォルト:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH : データ用 DuckDB パス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視 DB（デフォルト: data/monitoring.db）

---

## 使い方（代表的な例）

- settings の利用（環境変数アクセス）
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  ```

- DuckDB 接続例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定しなければ今日 (ただし内部で取引日調整あり)
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {written} codes")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（監査専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # またはメインの DuckDB 接続に対して init_audit_schema(conn)
  ```

- 研究向けファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

---

## ディレクトリ構成（主要ファイル）

（ルートの src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 自動読み込みと設定ラッパー
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメントのスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得/保存）
    - pipeline.py           — ETL パイプライン / run_daily_etl 等
    - calendar_management.py— 市場カレンダー管理（営業日判定等）
    - news_collector.py     — RSS ニュース収集（SSRF 対策等）
    - quality.py            — データ品質チェック
    - stats.py              — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py              — 監査ログスキーマ初期化・監査用 DB ユーティリティ
    - etl.py                — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility 等
    - feature_exploration.py— forward returns, IC, rank, factor_summary
  - monitoring/ (監視系の実装が入る想定)
  - execution/  (発注実装が入る想定)
  - strategy/   (戦略層の実装が入る想定)

---

## 実運用上の注意点・設計上のポイント

- Look-ahead bias の防止:
  - ニュース・レジーム・ETL 等の機能は内部で date を明示的に扱い、datetime.today()/date.today() を直接参照しないよう配慮されています。バッチやバックテストで利用する際は target_date を明示してください。
- 冪等性:
  - J-Quants からの保存は ON CONFLICT DO UPDATE を使い冪等に実装されています。ETL の再実行で重複しません。
- リトライ & フェイルセーフ:
  - OpenAI / HTTP API 呼び出しはリトライとフォールバックを備え、API の一時的な障害時に全体が停止しない設計です（スコア取得失敗時はスコアをスキップまたは中立値で継続）。
- セキュリティ:
  - RSS 取得時に SSRF 対策、XML 関係の安全対策（defusedxml）を導入しています。
- テスト:
  - 外部 API 呼び出し部分は内部関数をモックできる作りになっています（ユニットテストで _call_openai_api や _urlopen を差し替え可能）。

---

## よく使う環境変数（一覧）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知設定
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH — データ DuckDB のパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化

---

必要に応じて README をプロジェクトの実際の packaging（pyproject.toml / requirements.txt）や CI／運用手順に合わせて追記してください。README の追加・修正希望や、特定の使い方（例: ETL スケジュール設定、Slack 通知設定、kabu API との連携サンプル）があれば教えてください。