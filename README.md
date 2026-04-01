# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ集

短い説明:
KabuSys は日本株のデータ取得（J‑Quants）、ETL、データ品質チェック、ファクター計算、ニュース NLP、マーケットレジーム判定、監査ログなどを含む内部ライブラリ群です。DuckDB を主データストアに利用し、OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価やリサーチ用ユーティリティを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 簡単な使い方
- 環境変数（必須 / 任意）
- ディレクトリ構成
- 補足・設計上の注意

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J‑Quants API からの株価/財務/カレンダー取得（rate limit・リトライ・トークン自動更新対応）
- DuckDB を用いた ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）とニュースに基づく銘柄センチメント算出（OpenAI 使用）
- 市場レジーム判定（ETF の MA200 とマクロニュースの LLM センチメントを合成）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 監査（audit）テーブルによるシグナル→発注→約定のトレーサビリティ

設計方針のポイント:
- ルックアヘッドバイアスを避ける（内部で date.today() を不用意に参照しない等）
- API 呼び出しはリトライやバックオフ、レートリミット制御を備える
- ETL は差分・バックフィルを行い、品質チェックは Fail‑Fast にならない（問題収集）
- セキュリティ考慮（ニュース取得時の SSRF 対策、defusedxml の使用等）

---

## 主な機能一覧

- data/
  - jquants_client: J‑Quants API とのやり取り（取得 + DuckDB への冪等保存）
  - pipeline: 日次 ETL をまとめるエントリーポイント（run_daily_etl）
  - news_collector: RSS 収集（SSRF 防御・前処理・冪等保存）
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - calendar_management: JPX カレンダー管理・営業日判定
  - audit: 監査ログ（signal_events / order_requests / executions テーブル）初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを LLM でセンチメント化して ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して market_regime に保存
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー 等
- config: .env 自動読み込み・環境変数ラッパー（settings）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型表記（|）などを利用）
- ネットワークアクセス（J‑Quants / OpenAI 等）
- DuckDB を使うため十分なディスク容量

1. リポジトリをクローン
   git clone <repository-url>

2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   pip install -e .    # または requirements.txt があればそれを使用

   主な依存（コード中で使用）:
   - duckdb
   - openai
   - defusedxml
   （実際の requirements はプロジェクトの packaging を参照してください）

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env/.env.local を置くことで自動読み込みされます（config._find_project_root に基づく）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   必須の環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - OPENAI_API_KEY（AI 機能を使用する場合）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB 初期化（監査用 DB など）
   Python REPL で:
   ```
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   これにより監査用テーブルが作成されます。

---

## 使い方（簡単な例）

以下は典型的なワークフローのサンプルです。

- ETL（日次パイプライン）を実行する
  ```
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import datetime

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアを作成する
  ```
  from kabusys.ai.news_nlp import score_news
  import duckdb, datetime
  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=datetime.date(2026, 3, 20))
  print("書込銘柄数:", n_written)
  ```

- 市場レジームをスコア（LLM を使用）
  ```
  from kabusys.ai.regime_detector import score_regime
  import duckdb, datetime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=datetime.date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect(str(settings.duckdb_path))
  recs = calc_momentum(conn, target_date=datetime.date(2026, 3, 20))
  ```

- 監査テーブル初期化（既存 DB に導入）
  ```
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意:
- AI 関連関数は OPENAI_API_KEY を環境変数または api_key 引数で渡す必要があります。
- J‑Quants API 呼び出しには JQUANTS_REFRESH_TOKEN が必要です。jquants_client.get_id_token() で利用されます。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

AI / 任意:
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で利用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

データベース / 監視:
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH: 実行プロセス PID ファイル（デフォルト data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値

システム:
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py            : パッケージ初期化（__version__ 等）
- config.py              : .env 自動読み込み、settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py          : ニュースを LLM でスコア化（score_news）
  - regime_detector.py   : 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py    : J‑Quants API クライアント（取得・保存）
  - pipeline.py          : ETL パイプライン（run_daily_etl 等）
  - pipeline.py (ETLResult)
  - news_collector.py    : RSS 収集・前処理
  - quality.py           : 品質チェック
  - calendar_management.py : 市場カレンダーと営業日ロジック
  - audit.py             : 監査ログスキーマ初期化
  - stats.py             : zscore_normalize 等
  - etl.py               : ETLResult の公開 re-export
- research/
  - __init__.py
  - factor_research.py   : モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py : 将来リターン、IC、統計要約
- research/* 他: ファクター研究用ツール群

（上記は主要モジュールのみ抜粋。実際のリポジトリで完全なツリーを確認してください）

---

## 補足・設計上の注意

- Look‑ahead に関する配慮:
  - 多くのモジュールが内部で datetime.today() を直接参照しないよう設計されています。バックテストや再現性を保つため、target_date を明示的に渡して使用してください。
- API レート制御:
  - J‑Quants クライアントは固定間隔スロットリングでレート制限を遵守します（120 req/min）。
- リトライとフォールバック:
  - OpenAI / J‑Quants の API 呼び出しでは 5xx/429 等に対してエクスポネンシャルバックオフで再試行し、失敗時はフェイルセーフ（ゼロスコア等）を採用する箇所があります。
- セキュリティ:
  - news_collector は SSRF 対策、defusedxml による XML パース防御、応答サイズ制限などを実装しています。
- DuckDB の executemany に関する注意:
  - 一部ロジックは DuckDB のバージョン固有の挙動（executemany の空リスト不可等）に留意して実装されています。
- テスト:
  - 内部の OpenAI 呼び出し等はテスト用に patch 可能な設計になっています（ユニットテストでのモックが容易）。

---

ご不明点・追加で README に載せたい項目（例: CI / テスト実行方法、パッケージ公開手順、具体的な .env.example）などがあれば教えてください。README をプロジェクト用にさらにカスタマイズして作成します。