# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（データ基盤・リサーチ・AI・監査ログ・ETL・J-Quants クライアント等を含む）

---

## プロジェクト概要

KabuSys は、日本株のデータ収集・ETL、ニュースセンチメント解析（LLM 利用）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などの機能を提供する Python モジュール群です。  
主に以下の用途を想定しています。

- J-Quants API を利用した時系列データ（株価・財務・マーケットカレンダー）の差分取得と DuckDB への保存
- RSS からのニュース収集と LLM による銘柄別センチメントスコア生成
- マクロセンチメントとETF（1321）200日移動平均乖離を組み合わせた市場レジーム判定
- ファクター計算／特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注／約定に関する監査ログスキーマの初期化と運用サポート
- 環境変数管理（.env 自動読み込み機能を持つ）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証・ページネーション・レートリミット・保存ユーティリティ）
  - pipeline: 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - news_collector: RSS 収集・前処理・raw_news 保存
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - stats: 汎用統計ユーティリティ（Zスコア正規化等）
- ai/
  - news_nlp: ニュースを銘柄ごとに LLM でスコアリング（gpt-4o-mini を想定）
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- research/
  - factor_research: モメンタム、ボラティリティ、バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等
- config.py: 環境変数 / .env 読込・Settings API（自動 .env ロード、必須変数チェック）
- 監視・実行関連（execution, monitoring 等）はパッケージ公開用の __all__ に含まれる（コードベースに拡張できる設計）

設計上のポイント：
- ルックアヘッドバイアス対策（内部で date.today()/datetime.today() を直接参照しない設計）
- 冪等保存（DuckDB 側で ON CONFLICT DO UPDATE 等を使用）
- OpenAI / J-Quants 呼び出しに対するリトライ・バックオフ・フェイルセーフ処理
- テスト容易性（内部 API 呼び出しをモックしやすい構造）

---

## セットアップ手順

※以下はプロジェクト最小セットアップの例です。実環境では各自の仮想環境・パッケージ管理に合わせてください。

1. Python の準備
   - 推奨: Python 3.10 以降

2. リポジトリをチェックアウトしパッケージをインストール
   - 開発インストール（プロジェクトルートに pyproject.toml 等がある前提）
     ```bash
     pip install -e .
     ```
   - 依存パッケージ（例）
     - duckdb
     - openai
     - defusedxml
     - など（環境により追加が必要）

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると無効化可能）。
   - 主な環境変数（必要に応じて設定）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合は必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知等で利用
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB 等（デフォルト data/monitoring.db）
     - KABUSYS_ENV: `development` / `paper_trading` / `live`（環境選択）
     - LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`

   - Settings は kabusys.config.settings からアクセスできます。

4. データディレクトリ作成
   - DUCKDB_PATH の親ディレクトリが自動で作られる場合が多いですが、権限等に応じて事前に作成してください（例: data/）。

---

## 使い方（主要な例）

以下は最小の Python からの呼び出し例です。実行前に環境変数や DuckDB の接続先を設定してください。

- 共通準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコア生成（指定日）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {written} codes")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（監査用 DuckDB を作成）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions 等が作成されます
  ```

- J-Quants API を直接使ってデータを取得する（デバッグ用途）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  from kabusys.config import settings

  token = get_id_token()  # settings.jquants_refresh_token を利用
  records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))
  ```

- 研究用途（ファクター計算）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

テスト時のポイント：
- OpenAI API 呼び出し内部はモジュール内の _call_openai_api を patch して差し替え可能（unittest.mock.patch）。
- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用。

---

## ディレクトリ構成（抜粋）

以下は `src/kabusys` 以下の主要ファイルと概要です。

- __init__.py
  - パッケージエクスポート（data, strategy, execution, monitoring など）
- config.py
  - Settings クラス（環境変数取得、.env 自動ロード、必須チェック）
- ai/
  - __init__.py — score_news の再エクスポート
  - news_nlp.py — ニュースを銘柄別に LLM（gpt-4o-mini）でスコアリングする主要ロジック
  - regime_detector.py — ETF 1321 の MA200 とマクロニュースを組み合わせて市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - news_collector.py — RSS 収集・前処理
  - calendar_management.py — 市場カレンダー管理（営業日判定、calendar_update_job）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログスキーマの DDL／初期化ユーティリティ
  - stats.py — Zスコア等の統計ユーティリティ
  - etl.py — ETLResult の公開再エクスポート
- research/
  - __init__.py — 研究用 API のエクスポート（calc_momentum 等）
  - factor_research.py — モメンタム・バリュー・ボラティリティの計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- その他（strategy, execution, monitoring のモジュール群はパッケージ内で運用を想定）

---

## 注意事項 / 運用メモ

- セキュリティ
  - news_collector は SSRF を防ぐためスキーム検査・プライベートホストチェック・リダイレクト時の検査を行います。
  - .env ファイルには API トークン等の機密情報が含まれるため、git 管理での扱いに注意してください（.env は通常 .gitignore に含めます）。

- リトライ・フェイルセーフ
  - J-Quants・OpenAI 呼び出しはリトライロジックを持ち、特定の失敗時はスコアを 0.0 にフォールバックする等の安全設計がされています。運用上の閾値設定やログ監視を併用してください。

- ルックアヘッドバイアス対策
  - モジュールは Look-ahead bias を避ける設計です（target_date 未満のデータのみを使用、内部で現在時刻を直接参照しない等）。

- テスト
  - 外部 API 呼び出しはモック可能な設計です。OpenAI と通信する関数は内部の _call_openai_api を patch してテストできます。
  - 自動 .env 読み込みはテストで不要な場合に無効化できます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## 補足

- ここに記載した使用例はライブラリとしての呼び出し例です。実際に自動売買を運用する場合は、十分なバックテスト・リスク管理・運用監視（ログ/死活監視・kill flag 等）を実装してください。
- README にない細かいパラメータや関数の動作はソースコード内の docstring コメントをご参照ください。

---

さらに記載してほしいセクション（例: 開発フロー、テスト手順、CI 設定例、API 仕様の詳細など）があれば教えてください。