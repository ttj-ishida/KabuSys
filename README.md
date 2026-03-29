# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
ETL、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログなどを含むモジュール群を提供します。

概要、機能、セットアップ、使い方、ディレクトリ構成を下にまとめます。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量生成・ニュースセンチメント・市場レジーム判定・監査ログ等を含む、アルゴリズム取引・リサーチ基盤向けの Python モジュール群です。  
主な設計方針は次の通りです。

- Look‑ahead バイアス防止（内部で date.today() を不用意に参照しない等）
- DuckDB をデータレイクとして想定した SQL + Python 実装
- J-Quants API / RSS / OpenAI（gpt-4o-mini）等外部 API の扱いをラップして再利用可能に実装
- 冪等な DB 書き込み・トランザクション管理・リトライ/レートリミット制御を備える
- テスト容易性（API 呼び出しの差し替え等）に配慮

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env または環境変数読み込み、設定オブジェクト `settings`
  - 自動 .env ロード（プロジェクトルート検出）をサポート（無効化フラグあり）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 + DuckDB への保存）
  - pipeline / etl: 日次 ETL 実行（prices / financials / calendar の差分取得 + 品質チェック）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS からのニュース収集（SSRF 対策、正規化、冪等保存）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログスキーマの初期化・監査用 DB ヘルパー（signal / order / execution のトレーサビリティ）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュース記事を OpenAI に投げて銘柄ごとのセンチメントを ai_scores テーブルへ格納
  - regime_detector.score_regime: ETF（1321）の MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定し market_regime テーブルへ保存
  - OpenAI 呼び出しはリトライやフェイルセーフの考慮あり（API 未応答時にはフォールバック）
- kabusys.research
  - factor_research: momentum / value / volatility 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（スピアマン）算出、統計サマリー、rank 等

---

## セットアップ手順

前提: Python 3.10+（typing の union 表記等を使用）。実行環境によっては別バージョンを調整してください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   （requirements.txt がある場合はそれを使用、なければ最低限以下をインストールしてください）
   ```
   pip install duckdb openai defusedxml
   ```
   実運用では追加で HTTP クライアント等が必要になる場合があります。

4. 環境変数 / .env の準備  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動読み込みされます（ただしテスト時などに自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で使用）
   - SLACK_BOT_TOKEN: Slack 通知に使用する bot token（使用する場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（使用する場合）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（kabu API 利用時）
   任意またはデフォルトあり:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化

   例 .env（実際のトークンは安全に保管してください）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース用ディレクトリを準備（必要であれば）
   ```
   mkdir -p data
   ```

---

## 使い方（簡易例）

以下はライブラリを直接 Python から利用する簡単な例です。実運用では CLI ラッパーやバッチスクリプトを用意してください。

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアして ai_scores テーブルへ書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY 環境変数が使われる
  print("scored:", n)
  ```

- 市場レジームを判定して market_regime テーブルへ書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は監査ログテーブルが初期化された DuckDB 接続
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  momentum = calc_momentum(conn, date0)
  value = calc_value(conn, date0)
  volatility = calc_volatility(conn, date0)
  ```

注意点:
- OpenAI を使用する機能は `OPENAI_API_KEY` を環境変数に設定するか、関数の `api_key` 引数で明示的に渡してください。
- J-Quants の API は `JQUANTS_REFRESH_TOKEN` を用いて `get_id_token()` により id_token を取得します。
- DuckDB のテーブルスキーマ（raw_prices / raw_financials / raw_news / ai_scores / market_regime 等）が存在することが前提です。スキーマ初期化用のスクリプトはプロジェクトに含めると運用が楽です。

---

## ディレクトリ構成（主要ファイル）

（実際のリポジトリルートは src/ 配下にパッケージがあります）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得 + 保存）
    - pipeline.py              — ETL メインロジック（run_daily_etl 等）
    - etl.py                   — ETL 結果クラス再エクスポート（ETLResult）
    - quality.py               — データ品質チェック
    - stats.py                 — 共通統計ユーティリティ（zscore_normalize）
    - news_collector.py        — RSS 収集（SSRF 対策・正規化・保存）
    - calendar_management.py   — 市場カレンダー管理・営業日判定
    - audit.py                 — 監査ログ（signal / order / execution テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py       — Momentum/Value/Volatility 計算
    - feature_exploration.py   — 将来リターン・IC・summary・rank 等
  - research/feature_exploration.py
  - その他（strategy / execution / monitoring 等のプレースホルダが __all__ に含まれる可能性）

---

## 追加メモ / 運用上の注意

- .env 自動読み込み
  - `kabusys.config` はプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動ロードします。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。
  - 自動ロード時は OS 環境変数が優先され、`.env.local` は `.env` の上書きとして扱われます。

- OpenAI 呼び出しについて
  - `news_nlp` / `regime_detector` は gpt-4o-mini と JSON mode を前提にプロンプト/バリデーションを行います。
  - LLM 呼び出しはリトライ・フォールバックの挙動を持ち、失敗時は安全側の値（0.0 等）で継続します。

- J-Quants API
  - レートリミット（120 req/min）を守るため固定間隔の RateLimiter を実装しています。
  - 401 を受けた場合は refresh token を使って id_token を再取得して自動リトライします。

- テスト / モック
  - OpenAI やネットワーク呼び出しはモックしやすいように内部 API 呼び出しを分離しています（ユニットテストで差し替え可能）。

---

必要であれば以下も作成できます:
- requirements.txt（推奨ライブラリ一覧）
- DB スキーマ初期化スクリプト（raw_* / market_calendar / ai_scores / market_regime 等）
- 実行用 CLI / systemd / Airflow ジョブ定義のテンプレート

ほかに README に含めたい内容（CI 設定例、ロギング設定、サンプル .env.example、SQL スキーマ等）があれば教えてください。