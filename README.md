# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の用途を想定した Python パッケージです。

- J-Quants API を用いたマーケットデータ（株価日足・財務・カレンダー等）の差分取得（ETL）
- RSS ニュース収集と OpenAI を用いた記事・銘柄ごとのセンチメントスコア算出
- ETF（例: 1321）を利用した市場レジーム判定（MA + マクロニュース）
- 研究用途のファクター算出（モメンタム / バリュー / ボラティリティなど）と統計ユーティリティ
- データ品質チェック、マーケットカレンダー管理、監査ログ（トレース用テーブル）初期化
- J-Quants API のレート制御、認証リフレッシュ、DuckDB への冪等保存ロジック

設計上のポイント：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を無条件に参照しない）
- OpenAI 呼び出しや外部 API 呼び出しはリトライ・フェイルセーフを備える
- DuckDB を主な永続化先とする（軽量かつ SQL ベースで操作しやすい）

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - 環境変数 / .env 読み込み、必須設定の取得（auto-load: OS > .env.local > .env）
  - 主要設定項目（JQUANTS_REFRESH_TOKEN 等）

- kabusys.data
  - jquants_client: J-Quants API クライアント（認証・ページネーション・リトライ・レート制御）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - calendar_management: 営業日判定 / next/prev_trading_day / calendar_update_job
  - news_collector: RSS 収集（SSRF 対策・正規化・前処理）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化・専用 DB 初期化ユーティリティ
  - stats: z-score 正規化など汎用統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF の MA とマクロニュース（LLM）を合成して market_regime を書き込み

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats との連携で Z スコア正規化など

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 型記法を使用）
- DuckDB が必要（pip パッケージ duckdb）
- OpenAI API 利用時は OpenAI API キーが必要

例: 仮想環境を作ってインストールする

1. 仮想環境作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (cmd):
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 必要パッケージをインストール（代表的な依存）
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

3. パッケージを開発モードでインストール（プロジェクトルートに pyproject.toml や setup.py がある場合）
   ```
   pip install -e .
   ```

環境変数 / .env
- 自動読み込み: パッケージはプロジェクトルート（.git / pyproject.toml を探索）で `.env` / `.env.local` を自動読み込みします。テストなどで自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主な必須キー（例）
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabu API のパスワード（必要なら）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に使用する場合
  - OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）を実行する場合
- 主要デフォルト（未指定時）
  - KABU_API_BASE_URL: http://localhost:18080/kabusapi
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PID_FILE_PATH: data/execution.pid
  - LOG_LEVEL: INFO
  - KABUSYS_ENV: development / paper_trading / live（検証あり）

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=DEBUG
KABUSYS_ENV=development
```

---

## 使い方（主要ユースケース）

以下は最小限の利用例。各関数は duckdb の接続オブジェクトを受け取ります。

- DuckDB 接続の取得（settings を使う例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースのスコアリング（OpenAI を用いる）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は env から取得
  print("scored:", n_written)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用途）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

- 監査ログ（監査スキーマ）初期化
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  # 監査用 DB を初期化（settings.duckdb_path または別ファイル）
  audit_conn = init_audit_db(settings.duckdb_path)
  ```

- カレンダー・営業日ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- OpenAI を呼ぶ関数は API キーを引数で渡すこともできます（api_key=...）。未指定時は環境変数 OPENAI_API_KEY が使われます。
- ETL / API 呼び出し系はリトライやフォールバックロジックを備えていますが、API レートや課金に注意してください。

---

## ディレクトリ構成（主要ファイル）

パッケージは src/kabusys 以下に配置されています。主なファイル/モジュール:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュース NLU / OpenAI 呼び出し
    - regime_detector.py            -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        -- マーケットカレンダー管理
    - news_collector.py             -- RSS 収集
    - quality.py                    -- データ品質チェック
    - audit.py                      -- 監査ログ（DDL・初期化）
    - stats.py                      -- 統計ユーティリティ（zscore_normalize 等）
    - etl.py                        -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py            -- モメンタム/バリュー/ボラティリティ
    - feature_exploration.py        -- 将来リターン・IC・統計サマリー
  - monitoring/ (パッケージ公開に含まれる可能性あり)
  - execution/ (発注・ブローカー連携用は別モジュール想定)

各モジュールは docstring と詳細な設計方針・フェイルセーフを備えており、DuckDB を介した SQL 処理と Python ロジックの組合せで実装されています。

---

## 動作上の注意 / ベストプラクティス

- 本ライブラリは「取得したデータを DuckDB に格納してから」分析やバックテストに用いる想定です。Look-ahead バイアス防止のため、バックテストや研究で使用する際にはデータの取得日時(fetched_at) と利用ルールに注意してください。
- OpenAI / J-Quants の API キー・トークンは外部に漏れないように管理してください。
- 自動売買（実際の資金を使う場合）は paper_trading 環境で十分に検証してから live 環境へ移行してください（KABUSYS_ENV による環境区分あり）。
- news_collector は外部 RSS を取得するため SSRF 対策やタイムアウト設定を行っていますが、実行環境のネットワークポリシーも確認してください。

---

必要に応じて README を拡張（例: API リファレンス、ユニットテスト方法、CI 設定、具体的な ETL スケジュール例）できます。追加したい項目があれば教えてください。