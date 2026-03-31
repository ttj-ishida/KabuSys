# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース NLP（LLM を用いたセンチメント評価）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定トレース）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群を含む Python パッケージです。

- J-Quants API からのデータ取得（株価日足・財務・カレンダー）
- DuckDB ベースの ETL パイプラインと品質チェック
- RSS ニュース収集と LLM による銘柄ごとのニュースセンチメント評価
- マクロニュース＋テクニカル（ETF MA）を組み合わせた市場レジーム判定
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログスキーマ（シグナル → 発注 → 約定のトレース）

設計上の主な方針は「ルックアヘッドバイアス防止」「安全性（SSRF/XML爆弾対策）」「ETL の冪等性（ON CONFLICT）」です。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API 呼び出しのラッパー（認証・ページネーション・レート制御・リトライ）
  - save_* 系で DuckDB へ冪等保存
- data/pipeline.py
  - run_daily_etl: 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl などの個別ジョブ
  - ETLResult 型による実行結果管理
- data/quality.py
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue）
- data/news_collector.py
  - RSS 取得・正規化・前処理・raw_news への保存（SSRF/サイズ制限等の防御）
- ai/news_nlp.py
  - ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）でスコア化し ai_scores に保存
- ai/regime_detector.py
  - ETF（1321）200日 MA 乖離 + マクロニュース LLM スコアを合成して market_regime に保存
- research/
  - factor_research.py（モメンタム・バリュー・ボラティリティ計算）
  - feature_exploration.py（将来リターン、IC、統計サマリー等）
- data/audit.py
  - 監査テーブル（signal_events / order_requests / executions）DDL と初期化ユーティリティ
- config.py
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクト

---

## 必要な環境変数

以下は本コードベースで参照される主要な環境変数です（少なくとも実行する処理に応じて必要なものを用意してください）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：jquants_client.get_id_token 等で使用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp.score_news / regime_detector.score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注関連で使用予定）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知に使うトークン
- SLACK_CHANNEL_ID: Slack チャネル ID
- DUCKDB_PATH: DuckDB 保存パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite 保存パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development | paper_trading | live）（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

自動的にプロジェクトルート（.git または pyproject.toml を探索）を検出し、`.env` と `.env.local` をロードします。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. Python 環境を用意（推奨: Python 3.10+）
2. 必要パッケージをインストール（例）:

   ```bash
   pip install duckdb openai defusedxml
   ```

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

3. プロジェクトルートに `.env` を作成（`.env.example` を参考に）。少なくとも JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY を設定してください。

4. DuckDB ファイルのディレクトリを作成（必要なら）:

   ```bash
   mkdir -p data
   ```

5. （任意）監査ログ専用 DB を初期化する場合:

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な例）

以下は各主要機能を呼び出すための簡単なコード例です。実行時は必要な環境変数（上記）を設定してください。

- DuckDB 接続を作成して日次 ETL を実行する:

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーが必要）:

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} stocks")
  ```

- 市場レジーム判定:

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査ログスキーマを既存 DuckDB に追加:

  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- リサーチ用ファクター計算（例: モメンタム）:

  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2026,3,20))
  # recs は各銘柄のファクター値を含む辞書リスト
  ```

- 市場カレンダー判定ユーティリティ:

  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026,3,20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意:
- OpenAI 呼び出しを含む処理は API キーとネットワークが必要です。API 呼び出しはリトライ・フェイルセーフを備えていますが、キー未設定時は ValueError が発生します。
- ETL / 保存処理は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, ai_scores, market_regime など）に依存します。初回はスキーマ作成処理を用意する必要があります（このリポジトリにスキーマ初期化スクリプトがある前提）。

---

## ディレクトリ構成

（主要ファイル / モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         # ニュースの LLM スコアリング（ai_scores への書き込み）
    - regime_detector.py  # ETF MA とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   # J-Quants API クライアント（取得・保存）
    - pipeline.py         # ETL パイプライン（run_daily_etl 等）
    - quality.py          # データ品質チェック
    - calendar_management.py  # 市場カレンダー管理（営業日判定等）
    - news_collector.py   # RSS ニュース収集・前処理
    - audit.py            # 監査ログスキーマ・初期化
    - stats.py            # 汎用統計ユーティリティ
    - etl.py              # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py  # ファクター計算（momentum/value/volatility）
    - feature_exploration.py  # forward returns / IC / summary 等
  - research/... (他の研究用モジュール)
  - (その他: strategy/ execution/ monitoring などのパッケージが将来想定)

---

## 設計上のポイント・注意事項

- ルックアヘッドバイアス回避:
  - 日時計算や DB クエリで target_date 未満 / 以前を明示し、外部の現在時刻参照を最小化しています。
- 冪等性:
  - J-Quants から取得したデータは save_* 関数で ON CONFLICT を使い上書きして再実行を安全にしています。
- セキュリティ対策:
  - RSS 収集は URL 正規化、トラッキングパラメータ除去、SSRF 防止、受信サイズ制限、defusedxml による XML パースなどを実装しています。
- フェイルセーフ:
  - LLM/API の一時的な失敗はリトライや代替値（例: macro_sentiment=0）で継続処理する設計です。

---

## 開発 / 貢献

- コードはテストしやすいように外部 API 呼び出し箇所を差し替え可能（関数に注入 / モジュール内の _call_openai_api をモック等）。
- 新しい機能追加やバグ修正は、既存の ETL/品質チェック設計哲学（冪等性・ロギング・フェイルセーフ）に沿って実装してください。

---

質問や追加して欲しい使用例があれば教えてください。README に含めるサンプルコマンドやシェルスクリプト、初期スキーマ作成スクリプトなども作成できます。