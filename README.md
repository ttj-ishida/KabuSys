# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants / OpenAI / kabuステーション連携などを含むモジュール化されたコードベースです。

---

## プロジェクト概要

KabuSys は以下を目的とする Python モジュール群です。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得して DuckDB に保存する ETL パイプライン
- RSS を用いたニュース収集と前処理、ニュースと銘柄の紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別）およびマクロセンチメントを用いた市場レジーム判定
- ファクター（モメンタム、バリュー、ボラティリティ等）計算と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 発注・約定までを追跡可能にする監査ログテーブル初期化ユーティリティ
- kabuステーションや LINE 通知等の設定を扱う環境設定管理

設計上の特徴として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT）、堅牢なリトライ/フェイルセーフ、外部依存の明確化を重視しています。

---

## 主な機能一覧

- ETL
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（fetch / save 系）とレートリミッタ、認証自動リフレッシュ（kabusys.data.jquants_client）
- ニュース
  - RSS 取得・前処理・SSRF 対策・ID 生成（kabusys.data.news_collector）
  - AI による銘柄別ニューススコア（score_news, kabusys.ai.news_nlp）
  - マクロセンチメント + ETF MA による市場レジーム判定（score_regime, kabusys.ai.regime_detector）
- 研究（Research）
  - ファクター計算（momentum / value / volatility）（kabusys.research.factor_research）
  - 将来リターン計算、IC、統計サマリー（kabusys.research.feature_exploration）
- データ品質
  - 欠損・スパイク・重複・日付整合性チェック（kabusys.data.quality）
- 監査ログ（Audit）
  - signal_events / order_requests / executions の DDL 定義と初期化ユーティリティ（kabusys.data.audit）
- 設定管理
  - 環境変数 / .env 自動ロード、Settings オブジェクト（kabusys.config）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repository-url>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 開発環境用に extras や requirements.txt を用意している場合はそちらを利用してください。上記は本コードベースで参照されている主要パッケージです。

4. プロジェクトルートに .env を配置（任意）
   - settings はプロジェクトルート（.git または pyproject.toml を含むディレクトリ）にある `.env` / `.env.local` を自動で読み込みます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：ETL 実行時）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時）
   - KABU_API_PASSWORD: kabuステーション API パスワード（kabu 連携時）
   - （任意）DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（監視 DB）、LOG_LEVEL、KABUSYS_ENV

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

---

## 使い方（主要な関数・サンプル）

※ 例は Python REPL / スクリプト内での使用例です。

- 基本的な準備（設定と DuckDB 接続）
  ```python
  import os
  import duckdb
  from kabusys.config import settings

  # settings は環境変数から値を取得します
  db_path = settings.duckdb_path  # Path オブジェクト
  conn = duckdb.connect(str(db_path))
  ```

- 日次 ETL を走らせる（市場カレンダー -> 株価 -> 財務 -> 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースをスコアリングして ai_scores に保存する
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数に設定しておくか api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジームを判定して market_regime に書き込む
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用の DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査関連テーブルにアクセス可能
  ```

- 設定値の参照
  ```python
  from kabusys.config import settings
  print(settings.kabu_api_base_url)
  print(settings.is_live)
  ```

---

## 主要な環境変数一覧

- JQUANTS_REFRESH_TOKEN (必須 for J-Quants)
  - J-Quants のリフレッシュトークン。ETL 実行・fetch に必要。
- OPENAI_API_KEY (必須 for AI)
  - OpenAI API キー。news_nlp / regime_detector を使う場合に必要。
- KABU_API_PASSWORD
  - kabuステーションの API パスワード（発注連携等で使用）。
- DUCKDB_PATH (任意)
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)
  - 監視等で使う SQLite DB のパス（デフォルト: data/monitoring.db）
- LOG_LEVEL
  - ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_ENV
  - 実行環境（development / paper_trading / live）
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定すると .env 自動読み込みを無効化（テスト用）

---

## トラブルシューティングと注意点

- OpenAI / J-Quants の API 呼び出しはネットワーク障害やレート制限に対する再試行ロジックがありますが、API キーの設定を事前に確認してください。
- NewsCollector は SSRF 対策・最大レスポンスサイズ制限・XML パースの安全処理を実装しています。フィード追加時は URL のスキーム（http/https）とアクセス可能性を確認してください。
- DuckDB の executemany はバージョン依存の挙動があるため（空リスト渡し不可等）、関数内で適切に保護されています。
- 監査スキーマ初期化時に transactional=True を指定すると BEGIN/COMMIT を使って原子的に作成します。ただし DuckDB のトランザクション制限を理解した上で使用してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索します。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py          # 銘柄別ニューススコアリング（score_news）
  - regime_detector.py   # 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py    # J-Quants API client（fetch/save）
  - pipeline.py          # ETL パイプライン（run_daily_etl 等）
  - etl.py               # ETLResult の再エクスポート
  - news_collector.py    # RSS 収集・前処理
  - calendar_management.py  # 市場カレンダー管理
  - quality.py           # 品質チェック
  - stats.py             # 共通統計ユーティリティ（zscore_normalize）
  - audit.py             # 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py   # モメンタム/バリュー/ボラティリティ等
  - feature_exploration.py  # 将来リターン / IC / summary
- research/... (ユーティリティのエクスポート)

各モジュールは docstring と注釈により、期待される入力テーブル（DuckDB 上のテーブル名）・出力・設計上の挙動が明記されています。

---

## 付録 — 推奨パッケージ（参考）

最低限必要となる主要パッケージ（バージョンは運用ポリシーに合わせて固定してください）:

- python >= 3.10
- duckdb
- openai
- defusedxml

その他、運用環境に合わせて logging / monitoring 用のパッケージを追加してください。

---

必要であれば README に実行例の詳細（Docker, systemd サービス定義、CI ワークフロー、.env.example のテンプレート等）を追記します。どの情報を優先して追加しますか？