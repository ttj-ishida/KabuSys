# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL、ニュースNLP、マーケットレジーム判定、監査ログなど、取引システムと研究用途のためのユーティリティ群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（簡単な例）
- 環境変数（必須 / 任意）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の要件を満たすことを目的としたモジュール群です。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を用いた差分ETLパイプライン（冪等性・品質チェック付き）
- RSS によるニュース収集と OpenAI を用いたニュースセンチメントスコアリング
- ETF（1321）を使った 200 日移動平均乖離とマクロニュースを組み合わせた市場レジーム判定
- 監査ログ（signal → order_request → execution のトレース可能なスキーマ）初期化ユーティリティ
- 研究用のファクター計算・特徴量評価ユーティリティ

設計上の共通方針として「ルックアヘッドバイアス防止」「API リトライ・フォールバック」「DuckDB による冪等保存」「外部API呼び出しは最小化（研究モジュール）」が掲げられています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/保存関数、トークン管理、レート制御）
  - NewsCollector（RSS 収集、前処理、SSRF 対策）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（欠損、スパイク、重複、日付整合性）
  - 監査ログ初期化（init_audit_db / init_audit_schema）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースをまとめて OpenAI に送り、銘柄ごとの ai_score を ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime を保存
- research/
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索・IC 計算・統計サマリー
- config.py
  - 環境変数管理（.env 自動ロード機能 / 必須値チェック）
- audit / execution / strategy 等の基礎モジュール（パッケージ API を公開）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（任意）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール

   例（pip）:
   ```
   pip install duckdb openai defusedxml
   ```

   注意: 実行する機能に応じて他パッケージ（urllib は標準）も必要です。パッケージ管理ファイルがある場合はそれを利用してください（requirements.txt / pyproject.toml）。

4. 開発用インストール（パッケージとして扱う場合）

   ```
   pip install -e .
   ```

5. 環境変数を設定

   - .env または環境変数で設定します（下記「環境変数」を参照）。
   - パッケージは import 時に自動でプロジェクトルートの .env / .env.local を読み込みます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

## 使い方（簡単な例）

以下は代表的なユースケースのサンプルです。実行前に必要な環境変数（特に API キー）を設定してください。

- DuckDB 接続の作成例

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（J-Quants ID トークンは settings または引数で指定可能）

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を省略すると今日が対象になります
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores テーブルへ保存する

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key を直接渡すことも可能（省略時は OPENAI_API_KEY を参照）
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"written {n_written} codes")
  ```

- 市場レジーム判定を実行する

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DuckDB を初期化する（監査スキーマ作成）

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査テーブルにアクセスできます
  ```

- 研究用ファクター計算の例

  ```python
  from kabusys.research import calc_momentum
  from datetime import date

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

---

## 環境変数

主に config.Settings 経由で参照されます。必要に応じ .env／.env.local をプロジェクトルートに置いてください。

必須（ValueError を投げるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（Slack 機能を使う場合）
- SLACK_CHANNEL_ID: Slack の投稿先チャンネル ID
- KABU_API_PASSWORD: kabu ステーション API のパスワード（kabu 関連機能使用時）

任意（デフォルト値あり）
- KABUSYS_ENV: 実行環境。'development' / 'paper_trading' / 'live'（デフォルト: development）
- LOG_LEVEL: 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視系 DB（data/monitoring.db）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で利用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: import 時の .env 自動ロードを無効化

.env の例（テンプレート）

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

※ セキュリティのため .env はリポジトリにコミットしないでください。

---

## 注意点 / 実装上のポイント

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を起点）を探索して行います。テストや他環境で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants クライアントはレート制御（120 req/min）とリトライ（指数バックオフ）を実装しています。401 は自動でトークンをリフレッシュします。
- OpenAI 呼び出しは gpt-4o-mini を仕様（JSON mode を使って厳密な JSON を期待）。API エラー時はフェイルセーフ（基本はスコア 0.0 を使用）になっています。
- DuckDB に対する保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用しています。
- 研究モジュールは外部 API へアクセスしない設計（prices_daily / raw_financials を参照）です。バックテスト時のルックアヘッドバイアスに注意してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュース NLP（score_news）
    - regime_detector.py            - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント（fetch / save）
    - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
    - etl.py                        - ETL 結果型 ETLResult エクスポート
    - news_collector.py             - RSS ニュース収集
    - calendar_management.py        - マーケットカレンダー管理
    - quality.py                    - データ品質チェック
    - stats.py                      - 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                      - 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            - ファクター計算（momentum/value/volatility）
    - feature_exploration.py        - 将来リターン / IC / 統計サマリー
  - ai, research, data 以下にさらに細かな実装が含まれます

---

## 追加情報 / 開発者向けメモ

- テスト時は環境変数の自動読み込みを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）して、モックやテスト専用設定を注入してください。
- OpenAI への呼び出しはモジュール内で _call_openai_api をラップしており、ユニットテストでは patch して差し替え可能です（例: unittest.mock.patch）。
- DuckDB に対する executemany の空リスト渡しに制約があるため、保存処理では事前に空でないことをチェックしています（互換性考慮）。
- ニュース収集は SSRF 対策、圧縮爆弾（Gzip）対策、トラッキングパラメータ除去などを実装しています。

---

以上です。README に追記したい実例（CLI スクリプト、CI 設定、より詳しい .env.example）や、特定の機能の詳しい使い方（例: ETL のパラメータ調整、OpenAI のレスポンス検証方法など）が必要であれば教えてください。