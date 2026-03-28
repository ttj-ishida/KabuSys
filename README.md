# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
ETL（J-Quants からの株価・財務・カレンダー収集）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、リサーチ用ファクター計算、監査ログ（発注→約定トレーサビリティ）などの主要機能を提供します。

バージョン: 0.1.0 (src/kabusys/__init__.py の __version__)

---

## 主要特徴（機能一覧）

- データ取得・ETL
  - J-Quants API 経由で株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存（kabusys.data.pipeline / jquants_client）。
  - 差分取得・バックフィル・品質チェックを備えた日次 ETL（run_daily_etl）。

- データ品質チェック
  - 欠損、重複、日付不整合、スパイク検出（kabusys.data.quality）。

- カレンダー管理
  - market_calendar を参照する営業日判定 / 前後営業日取得 / 期間の営業日リスト（kabusys.data.calendar_management）。

- ニュース収集 / 前処理
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、raw_news への冪等保存（kabusys.data.news_collector）。

- ニュース NLP（OpenAI）
  - 銘柄ごとの記事群をまとめて LLM に投げてセンチメントを算出（kabusys.ai.news_nlp）。
  - マクロニュース + ETF MA200乖離から市場レジーム（bull/neutral/bear）判定（kabusys.ai.regime_detector）。

- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（kabusys.research）。
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化。

- 監査ログ（トレーサビリティ）
  - シグナル → 発注要求 → 約定 の UUID ベース監査スキーマと初期化ユーティリティ（kabusys.data.audit）。

- 設定管理
  - .env / 環境変数自動読み込み（kabusys.config）。自動ロードは無効化可能。

---

## 必要条件 / 推奨環境

- Python 3.10+
- 主な依存ライブラリ（最低限、プロジェクト内で参照されているもの）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, logging, datetime, hashlib 等

※ 実行環境に合わせた requirements.txt / packaging を用意して pip install してください。ここで挙げたのはコード内で明示的に使用している主要パッケージです。

---

## セットアップ手順

1. リポジトリをクローン（またはソースを配置）して作業ディレクトリへ移動。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。）

4. 環境変数 / .env の用意  
   必須の環境変数（少なくとも実運用で必要なもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード（使う場合）
   - SLACK_BOT_TOKEN       : Slack ボットトークン（通知用）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector で使用）
   - その他: DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL などはオプション（kabusys.config でデフォルトあり）

   例 .env（プロジェクトルートに配置）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=CXXXXXXX
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

   自動 .env ロードについて:
   - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）で `.env` / `.env.local` を自動読み込みします。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

5. データディレクトリを準備（必要に応じて）
   - デフォルトの DuckDB ファイル: data/kabusys.duckdb
   - 監査ログ DB デフォルト例: data/audit.duckdb

---

## 使い方（簡易例）

以下はライブラリを使う際の代表的な操作例です。実際はスクリプトやジョブから呼び出して運用します。

- DuckDB 接続の準備:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア作成（OpenAI API キーは環境変数 OPENAI_API_KEY を参照）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026, 3, 20))
  print("scored codes:", count)
  ```

- 市場レジーム判定（ETF 1321 + マクロニュース）:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

  note: 両関数とも api_key を引数で渡すこともできます（api_key=None の場合は環境変数 OPENAI_API_KEY を使用）。

- 監査ログ DB 初期化（監査専用 DB を新規作成）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- カレンダー関連ヘルパー:
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 研究用ファクター計算:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  recs = calc_momentum(conn, date(2026, 3, 20))
  ```

---

## 主要モジュール / ディレクトリ構成

（ソースは src/kabusys 以下に配置されています）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env の読み込み・Settings 管理
  - ai/
    - __init__.py
    - news_nlp.py
      - 銘柄ごとのニュースをまとめて OpenAI でスコアリング、ai_scores テーブルへ書き込み
    - regime_detector.py
      - ETF(1321)の200日MA乖離 + マクロニュースセンチメントで市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py
      - market_calendar 管理・営業日判定・カレンダー更新ジョブ
    - etl.py
      - ETLResult の再エクスポート
    - pipeline.py
      - 日次 ETL の実装（run_daily_etl 等）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査テーブル定義・初期化（signal_events/order_requests/executions）
    - jquants_client.py
      - J-Quants API クライアント（取得／保存のユーティリティ）
    - news_collector.py
      - RSS 収集・前処理・raw_news への保存
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン / IC / 統計サマリー 等の分析ユーティリティ

---

## 設定項目（主な環境変数）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー
- KABU_API_PASSWORD — kabuステーション API のパスワード（利用時）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

---

## テスト / 開発時の補足

- 自動 .env ロードを無効化する:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、パッケージインポート時の .env 自動読み込みをスキップします（ユニットテストで便利）。

- OpenAI 呼び出しやネットワークアクセスは外部依存のため、ユニットテストでは各モジュールの内部 API 呼び出しヘルパー（例: kabusys.ai.news_nlp._call_openai_api、kabusys.data.news_collector._urlopen 等）をモックしてください。コード内でテスト差替えを想定した設計になっています。

---

## ライセンス / 謝辞

この README はソースコードから自動生成した概要です。実際の運用時はセキュリティ（API キー管理、ネットワークアクセス制限）、レート制限、エラーハンドリング、監査要件を十分に検討してください。

もし追加で README に含めたい実行スクリプト例やデプロイ手順（Systemd / Docker / Airflow ジョブ等）があれば教えてください。必要に応じて具体的な運用手順や例を追記します。