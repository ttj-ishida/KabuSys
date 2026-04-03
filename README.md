# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys のリポジトリ用 README。

このドキュメントはプロジェクトの概要、主要機能、セットアップ手順、簡単な使い方とディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株に特化した自動売買システムとデータプラットフォームのコアライブラリです。  
主に以下を目的としています。

- J-Quants API を用いた市場データ／財務データの差分 ETL と品質チェック
- ニュースの収集・NLP による銘柄センチメントスコア算出（OpenAI を利用）
- 市場レジーム判定（ETF の MA とマクロニュース合成）
- 研究用ファクター計算・特徴量解析ユーティリティ
- 発注から約定までを追跡する監査ログ（DuckDB ベース）の初期化・操作ユーティリティ
- 簡易な設定管理（.env の自動読み込み、環境変数経由）

設計上の特徴として、ルックアヘッドバイアス防止（日時の直接参照抑止）、フェイルセーフ動作（API 失敗時の適切なフォールバック）、および DuckDB を用いたローカル永続化といった点に配慮しています。

---

## 主な機能一覧

- data
  - J-Quants クライアント（fetch / save / 認証・レート制御・リトライ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（z-score 正規化）
- ai
  - ニュース NLP（score_news: 銘柄ごとの AI スコア取得）
  - 市場レジーム判定（score_regime: ETF MA とマクロセンチメント合成）
  - OpenAI 呼び出しは gpt-4o-mini を前提（JSON Mode を利用）
- research
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config
  - settings オブジェクト経由で設定値／環境変数を取得
  - .env 自動読み込み（プロジェクトルート検出）

---

## 要件

- Python 3.10+
- 主要依存ライブラリ（少なくとも次をインストールしてください）:
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI API 利用時）

（パッケージ化ファイルや pyproject.toml がある場合はそちらに依存関係が記載されます。ローカルでの開発時は仮想環境を推奨します。）

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jq 認証用）
  - KABU_API_PASSWORD : kabuステーション API を使う場合のパスワード
- 任意 / 推奨
  - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime に必要）
  - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
  - KABUSYS_ENV : environment ('development' / 'paper_trading' / 'live')（デフォルト development）
  - LOG_LEVEL : ログレベル（DEBUG/INFO/...）
- 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

参考として README に .env.example を置いておく想定ですが、`.env` を作成して必要な値を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれを使ってください）

3. 環境変数設定
   - プロジェクトルートに `.env` を作成し、必要なキーを追加します。
   - 例（最小）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxx...
     KABU_API_PASSWORD=your_kabu_password

4. データディレクトリ作成（必要に応じて）
   - mkdir -p data

5. DuckDB 初期化（監査ログ DB を使う場合）
   - Python スクリプトから init_audit_db を呼ぶ（下記「使い方」を参照）

---

## 使い方（例）

以下はライブラリ関数を直接呼び出す最小例です。実運用ではログ設定や例外ハンドリングを追加してください。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）:

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")  # デフォルトパスは設定で変更可
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとの AI スコア）を実行:

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム評価（market_regime テーブルへ書き込む）:

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ DB（別 DB）を初期化する:

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成されます
  ```

- 設定値へのアクセス（アプリ内で）:

  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注: OpenAI を使う関数は api_key 引数を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。J-Quants は JQUANTS_REFRESH_TOKEN を settings 経由で参照します。

---

## よくある運用ポイント

- .env の自動読み込みはプロジェクトルート検出に依存するため、スクリプトをどのディレクトリから実行しても動作するように設計されています。テスト等で自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB に対する複数トランザクション操作や大規模挿入は executemany を利用しています。DuckDB のバージョン差異により空の executemany がエラーになる場合があるため（コード内で配慮済み）注意してください。
- OpenAI 呼び出しはリトライ・バックオフが実装されていますが、API 利用料やレートに注意して運用してください。
- ニュース収集では SSRF 対策・XML パースの安全化（defusedxml）・読み込みバイト上限を実装しています。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl など）
    - etl.py                        — ETLResult の再エクスポート
    - calendar_management.py        — 市場カレンダー関連ユーティリティ
    - news_collector.py             — RSS ニュース収集・保存
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ初期化 / DB 初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/vol）
    - feature_exploration.py        — 将来リターン / IC / summary 等
  - ai/、data/、research/ パッケージはそれぞれ関連機能を提供します。

---

## 開発・拡張のヒント

- テスト時は外部 API 呼び出しをモックしてください（jquants_client._request、news_nlp/_call_openai_api、regime_detector の OpenAI 呼び出し等）。
- DuckDB を用いたデータ操作は SQL と Python の組み合わせで行われます。既存の SQL を参考に新しいクエリ関数を実装してください。
- ルックアヘッドバイアスを避ける設計思想がコード全体にあるため、日時関係の関数は引数で基準日を渡す設計を踏襲してください。

---

もし README に追加したいサンプルスクリプトや運用手順（cron / systemd 用の実行例）、CI 設定などあれば教えてください。必要に応じて追記します。