# KabuSys

日本株向けのデータプラットフォーム & 自動売買リサーチ基盤ライブラリ（KabuSys）。  
J-Quants / RSS / OpenAI を活用した ETL、ニュース NLP、マーケットレジーム判定、ファクター計算、監査ログスキーマなどを提供します。

---

## プロジェクト概要

KabuSys は次の用途を想定した Python パッケージです：

- J-Quants API からの株価・財務・市場カレンダーの差分 ETL
- RSS を用いたニュース収集と前処理（SSRF やサイズ制限など多数の安全対策あり）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（JSON Mode）
- ETF MA やマクロニュースを組み合わせた市場レジーム判定
- ファクター（モメンタム・バリュー・ボラティリティ）計算・特徴量探索ユーティリティ
- DuckDB を用いたデータ保存と品質チェック、監査ログ（order/signals/executions）のスキーマ初期化機能

設計方針として、バックテストでのルックアヘッドバイアス回避、API 呼び出しのリトライ/レート制御、冪等保存（ON CONFLICT）などに配慮しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（token リフレッシュ、ページネーション、レート制御）
  - News Collector（RSS 取得、URL 正規化、SSRF 対策、raw_news 保存）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP（score_news：銘柄ごとのセンチメントを ai_scores テーブルへ保存）
  - 市場レジーム判定（score_regime：ETF MA200乖離 + LLM マクロセンチメントを合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - .env と環境変数からの設定読み込み（自動ロード機能あり）

---

## 必要条件

- Python 3.9+
- 主要依存（例）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトに応じて追加パッケージが必要になる可能性があります）

推奨インストール例：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトの requirements.txt があればそれを利用
```

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要なパッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # 開発用: pip install -e .
   ```

4. 環境変数の設定
   - ルート（リポジトリルート）に `.env` または `.env.local` を配置すると、自動で読み込まれます（ただし、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 主に必要となる環境変数（例）:

     - J-Quants / データ
       - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - kabuステーション（発注など）
       - KABU_API_PASSWORD: kabu API のパスワード（必須）
       - KABU_API_BASE_URL: (任意) デフォルト: http://localhost:18080/kabusapi
     - OpenAI / AI
       - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
     - Slack（通知等）
       - SLACK_BOT_TOKEN
       - SLACK_CHANNEL_ID
     - DB/運用
       - DUCKDB_PATH: デフォルト data/kabusys.duckdb
       - SQLITE_PATH: デフォルト data/monitoring.db
       - PID_FILE_PATH: デフォルト data/execution.pid
     - モニタリング閾値（任意）
       - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - 実行環境
       - KABUSYS_ENV: development | paper_trading | live
       - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

   - 例 `.env`（簡易）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=secret
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DuckDB データベースの準備（必要に応じて）
   - 監査ログ用 DB を初期化する例（python スクリプト内で）:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn を使って以降の処理を実行
     ```

---

## 使い方（代表的な例）

以下は Python スクリプトから利用する際の基本例です。

- DuckDB 接続を作って日次 ETL を実行する例
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI キー必須）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（既存 conn に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意点：
- score_news / score_regime は OpenAI を呼び出すため、OPENAI_API_KEY を環境変数または関数引数で指定してください。API 呼び出しはリトライ・フォールバック（失敗時はスコア 0 やスキップ）を備えています。
- ETL 実行は各ステップで個別に例外処理され、1 ステップ失敗でも他のステップは継続する設計です。結果は ETLResult に集約されます。

---

## 自動環境変数読み込みについて

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml）から `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。
- テスト等で自動ロードを無効化するには環境変数を設定：
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成

以下は主要ファイル/モジュールの抜粋ツリーです（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

主要な公開 API（一例）:
- kabusys.config.settings — 環境設定（JQUANTS_REFRESH_TOKEN 等）
- kabusys.data.pipeline.run_daily_etl
- kabusys.data.jquants_client.*（fetch_* / save_* / get_id_token）
- kabusys.data.audit.init_audit_db / init_audit_schema
- kabusys.ai.news_nlp.score_news
- kabusys.ai.regime_detector.score_regime
- kabusys.research.*（calc_momentum / calc_value / calc_volatility 等）
- kabusys.data.stats.zscore_normalize

---

## セキュリティ・運用上の注意

- NewsCollector は SSRF 対策（リダイレクト検査、プライベート IP 検出）、受信サイズ制限（MAX_RESPONSE_BYTES）など安全対策を実装しています。外部 URL を扱う際は追加のネットワーク制約を検討してください。
- J-Quants API はレート制限（120 req/min）を遵守するためにスロットリング実装があります。大規模バッチは時間的余裕を持って実行してください。
- OpenAI 呼び出しは JSON Mode を前提にしており、レスポンスのパースや不正応答に対してフォールバックを実装していますが、API 仕様変更などには注意してください。
- 本ライブラリはバックテストと実運用で使うケースを想定しており、ルックアヘッドバイアスを避ける設計となっています。API 呼び出しや date 処理はそのことを念頭に利用してください。

---

## 参考（開発メモ）

- 自動読み込み順序: OS 環境変数 > .env.local > .env
- OpenAI モデル: gpt-4o-mini（JSON Mode）を想定
- DuckDB はファイルパス default: data/kabusys.duckdb
- watchpoints: DuckDB executemany に空リストを渡すと問題になるバージョンがあるため、コード内で空チェックを行っています

---

不明点や README に追加してほしいサンプル（例えば具体的な ETL スケジュール cron 例、CI 設定、より詳細な DB スキーマ一覧など）があれば教えてください。必要に応じて README を拡張します。