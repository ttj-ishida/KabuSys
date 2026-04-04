# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群。  
ETL、ニュース収集・AIセンチメント、ファクター計算、監査ログなど、バックテスト・運用に必要な基盤処理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。主な目的は次の通りです。

- J-Quants API からのデータ取得（株価、財務、取引カレンダー）
- DuckDB を用いたデータ格納・ETL パイプライン
- RSS ベースのニュース収集と LLM（OpenAI）を用いたニュースセンチメント評価
- 市場レジーム判定（ETF + マクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー 等）
- データ品質チェック、監査ログ（発注／約定のトレーサビリティ）
- 運用用の設定管理（.env / 環境変数）

設計上の特徴として、バックテスト時のルックアヘッドバイアス回避、API 呼び出しのリトライ・レート制御、冪等な DB 保存を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・保存）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day）
  - ニュース収集（RSS → raw_news、SSRF 対策・トラッキング除去）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news：銘柄ごとのニューススコアを ai_scores に書込）
  - 市場レジーム判定（score_regime：ETF 1321 の MA とマクロニュースを合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- 設定管理
  - 環境変数 / .env 自動ロード、設定値 accessor（kabusys.config.settings）

---

## 要件 (ざっくり)

- Python 3.10 以上（Union 型表記などを利用）
- 必要なパッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS ソース など）

実際の依存パッケージはプロジェクトの packaging / pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリをクローンしてインストール（開発環境向け）
   - pip による開発インストールの例:
     ```
     pip install -e .
     ```

2. Python 環境の準備
   - Python 3.10 以降を使用してください。
   - 必要な依存パッケージをインストールしてください（例: duckdb, openai, defusedxml）。

3. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（および `.env.local`）を置くと、自動でロードされます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector の呼び出しに必要）
   - KABU_API_PASSWORD: kabuステーション API パスワード（運用時に使用）
   - KABUSYS_ENV: environment モード（development / paper_trading / live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH / その他監視設定

   .env の書式はシンプルな KEY=VALUE です。詳細なパース仕様（引用符やコメントの扱い）に対応しています。

4. データベースやディレクトリの作成
   - DuckDB のファイルパスの親ディレクトリを自動作成するユーティリティが一部にありますが、必要に応じて `data/` ディレクトリ等を作成してください。

---

## 使い方（代表的な例）

以下の例は Python REPL / スクリプト内での簡単な使用例です。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN や OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアを生成（OpenAI API キーが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジームスコアを計算して書き込む（OpenAI API キーが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査ログテーブルが作成されていることを確認できます
  ```

- 設定値の取得
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.env)
  ```

注意点:
- score_news / score_regime は OpenAI と通信するため、API キーが必要です（引数で渡すか環境変数 OPENAI_API_KEY を設定）。
- J-Quants API を使う処理は JQUANTS_REFRESH_TOKEN が必要です。
- ETL・API 呼び出しは外部通信を伴うため、エラー時にはログ出力・リトライが行われますが、例外ハンドリングを行って呼び出し側で適切に対処してください。

---

## 設定管理（kabusys.config）

- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索して `.env` / `.env.local` を読み込みます。
  - 読み込み順序: OS 環境変数 > .env.local (上書き) > .env (未設定のみ)
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に利用）。
- settings オブジェクトから必要な設定を参照できます（例: settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.log_level）。

---

## ディレクトリ構成（主なファイル）

プロジェクトは src/kabusys 以下に実装が置かれています。主なモジュールは次の通りです。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/.env 管理
  - ai/
    - __init__.py
    - news_nlp.py  — ニュースセンチメント（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント、保存ユーティリティ
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - etl.py  — ETL 公開インターフェース（ETLResult の再エクスポート）
    - calendar_management.py  — カレンダー管理（is_trading_day 等）
    - news_collector.py  — RSS 収集（fetch_rss 等）
    - quality.py  — データ品質チェック
    - stats.py  — zscore_normalize 等
    - audit.py  — 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py  — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py  — calc_forward_returns / calc_ic / factor_summary / rank
  - research/*（補助モジュール）
  - その他：strategy / execution / monitoring 等の名前は __all__ に含まれていますが、実装はプロジェクト内で段階的に追加されます。

---

## ロギング・実行モード

- 設定: LOG_LEVEL 環境変数で制御（デフォルト: INFO）。
- KABUSYS_ENV=development / paper_trading / live を利用して挙動を分けられます（settings.is_live 等のプロパティで判定可能）。
- 実行プロセス監視用のパス（PID ファイル、kill フラグ）も環境変数で指定可能（PID_FILE_PATH, KILL_FLAG_PATH）。

---

## 注意事項 / ヒント

- DuckDB の executemany に渡すパラメータが空だとバージョン依存でエラーになる点に配慮した実装があるため、直接 SQL を流す場合も注意してください。
- OpenAI API 呼び出しにはリトライ・バックオフ・レスポンスのバリデーション処理が実装されていますが、API ポリシーやレート制限に従ってください。
- ニュース収集は RSS を前提としており、SSRF 対策や URL 正規化（utm 等の除去）をおこなっています。
- テスト時は環境変数自動ロードを無効にしたり、OpenAI / ネットワーク呼び出しをモックして実行してください。

---

## 貢献 / 開発

- バグ報告・機能リクエストは issue を通してください。
- ローカルでの開発: 仮想環境を作成し、`pip install -e .` を行うとソースを編集しながら利用できます。
- テスト用に外部 API 呼び出しをモックするヘルパーが各モジュールに想定されています（例: kabusys.ai.news_nlp._call_openai_api を patch する等）。

---

記載されていない詳細な使用例や運用ルールは各モジュールの docstring を参照してください。README への追加希望や、具体的な運用シナリオ（例: cron による ETL 実行、監視設定）について要望があれば教えてください。