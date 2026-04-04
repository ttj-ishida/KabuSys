# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ニュース収集、LLM を用いたニュースセンチメント評価、ファクター計算、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件（依存関係）
- セットアップ手順
- 環境変数（主な設定）
- 使い方（簡単な利用例）
- ディレクトリ構成 / 主要ファイル
- 開発・テスト時の注意点

---

## プロジェクト概要

KabuSys は、日本株の自動売買システムを構築するためのモジュール群です。主に次を目的としています。

- J-Quants API からの市場データ取得（株価・財務・市場カレンダー）
- ETL（差分取得・保存・品質チェック）
- RSS ベースのニュース収集・前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄単位 / マクロ）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 研究用ファクター計算・特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution のトレース）用 DB 初期化
- データ品質チェック・カレンダー管理等のユーティリティ

設計方針として、バックテストでのルックアヘッドバイアス回避、DuckDB を利用したローカル永続化、API 呼び出しの堅牢化（リトライ・レート制御）等を重視しています。

---

## 機能一覧

主な機能（モジュール単位）

- kabusys.config
  - .env 自動読み込み（.env, .env.local / OS 環境変数優先）
  - 設定アクセス（J-Quants トークン、OpenAI、DB パス、監視閾値など）

- kabusys.data
  - jquants_client: J-Quants API 呼び出し、保存（raw_prices/raw_financials/market_calendar 等）
  - pipeline: 日次 ETL（差分取得、保存、品質チェック）
  - news_collector: RSS 収集、前処理、冪等保存
  - calendar_management: 市場カレンダー管理、営業日判定ユーティリティ
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - stats: Z-score 正規化等の統計ユーティリティ
  - audit: 監査ログ（signal / order_requests / executions）テーブル作成 & 初期化

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを LLM でスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA 乖離とマクロニュースセンチメントを合成して market_regime を更新

- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー等

その他、strategy / execution / monitoring 用のパッケージ構成を想定（パッケージ公開名に含まれます）。

---

## 必要条件（依存関係）

- Python 3.10 以上（型記法: X | Y 等を使用）
- 必須 Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime など）

（プロジェクト配布時は requirements.txt や pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```bash
   git clone <repository-url>
   cd <repository>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストールします（例）。

   ```bash
   pip install duckdb openai defusedxml
   ```

   - 実際の配布では pyproject.toml / requirements.txt を参照してください。

3. 環境変数を設定します。開発時はプロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須の環境変数（例）を設定します（詳細は次節を参照）。

5. DuckDB 等の DB パスはデフォルトで `data/kabusys.duckdb`（settings.duckdb_path）です。必要に応じて `DUCKDB_PATH` を設定してください。

---

## 環境変数（主な設定）

重要な環境変数（settings から取得されるもの）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（get_id_token で利用）
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- OPENAI_API_KEY (推奨)
  - OpenAI API キー。API 呼び出し関数に明示的に渡すことも可能。
- KABUSYS_ENV (任意)
  - 実行環境: "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL (任意)
  - "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
- DUCKDB_PATH (任意)
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)
  - 監視データ用 SQLite パス（デフォルト: data/monitoring.db）
- その他（PID ファイルや閾値など）
  - PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

設定は .env/.env.local に書くと便利です。`.env.example`（存在する場合）を参考にしてください。

---

## 使い方（簡単な利用例）

以下はライブラリの主要機能を簡単に使う例です。実運用ではログや例外処理を適宜追加してください。

- DuckDB 接続と ETL 実行（日次 ETL）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  # DuckDB に接続（settings.duckdb_path は Path）
  conn = duckdb.connect(str(settings.duckdb_path))

  # ETL を実行（target_date を指定、None で today）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（AI）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に設定しておくのが簡単
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", n_written)
  ```

- 市場レジームの判定:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用 DuckDB を作る）:

  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 研究系ユーティリティ（ファクター計算）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

注意:
- OpenAI 呼び出しを行う関数は API キーを引数で渡すこともできます（api_key="..."）。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, ai_scores, market_regime 等）は ETL / 初期化スクリプトで作成する必要があります（プロジェクトの schema 初期化機能を利用してください）。

---

## ディレクトリ構成

主要なファイル・モジュール（抜粋）

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント（銘柄ごと）
  - regime_detector.py  — マーケットレジーム判定
- src/kabusys/data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント & 保存ロジック
  - pipeline.py             — ETL パイプライン
  - news_collector.py       — RSS 収集・前処理
  - calendar_management.py  — 市場カレンダー管理
  - quality.py              — データ品質チェック
  - stats.py                — 統計ユーティリティ（z-score 等）
  - audit.py                — 監査ログ DDL / 初期化
  - etl.py                  — ETLResult の再エクスポート
- src/kabusys/research/
  - __init__.py
  - factor_research.py      — ファクター計算
  - feature_exploration.py  — 将来リターン・IC・サマリー
- （その他）strategy, execution, monitoring 等の名前空間を想定

---

## 開発・テスト時の注意点

- ルックアヘッドバイアス防止:
  - 多くの関数は内部で date.today() や datetime.today() を参照しない実装方針です。テスト時は target_date を明示的に渡してください。
- 環境変数自動読み込み:
  - config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動的に読み込みます。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能です。
- API キーやトークン:
  - J-Quants のリフレッシュトークンは必須（settings.jquants_refresh_token）。OpenAI は関数ごとに api_key を渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- テスト用のモック:
  - OpenAI 呼び出し、HTTP ネットワーク呼び出し等はモックしやすい設計になっています（内部の _call_openai_api, _urlopen 等を patch 可能）。
- DuckDB executemany の空リスト:
  - 一部処理（ai_scores 書き込み等）では DuckDB の executemany に空リストを渡さないよう注意しています。自作スクリプトでも同様の注意を払ってください。

---

必要であれば、以下の追加ドキュメントを作成できます:
- データベーススキーマ（DDL）
- デプロイ手順（systemd / Supervisor を利用した常駐化）
- CI/CD / テスト方針
- API キーの安全な管理方法（Vault / Secret Manager）

ご希望があれば README の拡張（より詳細なコマンド例、docker-compose、schema 初期化手順など）を作成します。