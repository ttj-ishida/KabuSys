# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（データ取得・ETL・リサーチ・AI ニュース分析・監査ログ等のユーティリティを含む）です。本リポジトリは DuckDB を中心としたローカルデータ基盤と、J-Quants / OpenAI 等の外部 API を組み合わせて、運用可能なデータパイプラインと研究用ツール群を提供します。

バージョン: 0.1.0

---

## 概要

主な設計方針・特徴

- DuckDB をデータレイヤーに採用し、株価・財務・ニュース・カレンダー等をローカル保存して分析可能。
- J-Quants API を使った差分 ETL（株価、財務、JPX カレンダー）を提供。冪等保存・リトライ・レート制御を実装。
- ニュース記事を収集して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを生成する機能（news_nlp）。
- マクロニュースと ETF（1321）の MA200 乖離を組み合わせて市場レジームを判定する機能（regime_detector）。
- 研究用にファクター計算 / 将来リターン / IC（Information Coefficient）計算等のユーティリティを提供。
- データ品質チェック（欠損・スパイク・重複・日付不整合）と監査ログ用スキーマを備える。
- .env（プロジェクトルート）を自動ロードする仕組みを提供（テスト時は無効化可能）。

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・リトライ・レート制御）
  - ニュース収集（RSS）と前処理（SSRF 対策・トラッキングパラメータ除去）
  - カレンダー管理（営業日判定・次営業日 / 前営業日・calendar_update_job）
  - データ品質チェック（missing / spike / duplicates / date_consistency）
  - 監査ログテーブル初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp: ニュースの銘柄別センチメントスコア生成（OpenAI JSON Mode を利用）
  - regime_detector: ETF の MA200 乖離とマクロセンチメントを合成して市場レジーム判定
- research
  - factor_research: momentum / value / volatility 等の定量ファクター計算
  - feature_exploration: forward returns / IC / 統計サマリー 等
- config
  - 環境変数管理 (.env 自動ロード、必須キー検査、設定ラッパー)

---

## セットアップ手順

前提: Python 3.10+（typing の | 記法や __future__ アノテーションを利用）。実運用では最新の安定版 Python を推奨します。

1. リポジトリをクローン
   ```
   git clone <このリポジトリの URL>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   （requirements.txt があればそれを使ってください。なければ最低限の依存を例示します）
   ```
   pip install duckdb openai defusedxml
   ```
   - duckdb: データベース
   - openai: OpenAI クライアント（news_nlp / regime_detector で使用）
   - defusedxml: RSS/XML の安全パース
   その他、ロガーやテスト用のパッケージを追加する場合があります。

4. 環境変数（.env）を用意
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定すると自動読み込みを無効化できます）。

   主要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に必要）
   - KABU_API_PASSWORD: kabuステーション API を使う場合のパスワード
   - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知連携用（任意）
   - DUCKDB_PATH: デフォルト data/kabusys.duckdb
   - SQLITE_PATH: 監視用 sqlite データベース（data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）
   - PID_FILE_PATH / KILL_FLAG_PATH など監視関連パス

   例（.env の一部）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は最小限の Python スクリプト例です。実行前に環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）を設定してください。

- DuckDB に接続して日次 ETL を実行:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメントを作成（news_nlp）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数にセットされている前提
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {n_written} scores")
  ```

- 市場レジームスコアを計算（regime_detector）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで監査用テーブルが作成されます
  ```

注意点:
- OpenAI 呼び出しを行う関数（news_nlp / regime_detector）は API 呼び出しの失敗に対してフェイルセーフ（スコア 0 にフォールバック）を組み込んでいますが、API キーは必須です。テスト時は関数内の _call_openai_api をモックしてください。
- ETL 実行中は J-Quants API のレート制御・リトライ・トークンリフレッシュが自動で行われます。

---

## ディレクトリ構成

主要なファイルとモジュールの概要（リポジトリのルートは `src/kabusys/` を想定）:

- src/kabusys/
  - __init__.py
  - config.py
    - .env の自動読み込み、settings (Settings) オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースの銘柄別センチメント生成（OpenAI）
    - regime_detector.py   — ETF MA200 とマクロセンチメントで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult の再エクスポート
    - news_collector.py    — RSS 収集と前処理（SSRF 対策・正規化）
    - calendar_management.py — 市場カレンダー（営業日判定・更新ジョブ）
    - quality.py           — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py             — zscore_normalize 等の統計ユーティリティ
    - audit.py             — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py   — momentum / value / volatility ファクター計算
    - feature_exploration.py — forward returns / IC / summary / rank
  - execution/ (発注・ブローカー連携用モジュール想定)
  - monitoring/ (プロセス監視・リソースチェック想定)

（上記はコードベースの主要モジュールを抜粋したものです）

---

## 開発・テスト向けメモ

- .env 自動読み込みは config.py により実装されています。テストから環境を操作する場合は、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。
- OpenAI 呼び出しや外部 HTTP 呼び出しは各モジュール内で専用のラッパー関数を通しているため、ユニットテスト時はそれらを patch / monkeypatch して外部依存を切り離すことが容易です（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- DuckDB 接続は ":memory:" を使ってインメモリ DB を作成できます。監査 DB 初期化関数 init_audit_db は ":memory:" をサポートします。

---

## よくある質問 / 注意事項

- Q: .env はどこに置くべきですか？
  - A: リポジトリのプロジェクトルート（.git または pyproject.toml がある階層）に置くと自動で読み込まれます。必要に応じて .env.local を使ってローカル上書きが可能です。

- Q: バックテストでのルックアヘッドバイアス対策はどうなっていますか？
  - A: 多くの機能（news_nlp, regime_detector, pipeline 等）は target_date を明示的に受け取り、内部で date.today() を直接参照しない設計になっています。DB クエリでは date < target_date 等の排他条件を使い、ルックアヘッドを防止しています。

- Q: J-Quants / OpenAI の API キー管理は？
  - A: 環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY）で管理してください。J-Quants の ID トークンはモジュール内でキャッシュ・自動リフレッシュされます。

---

## 連絡 / 貢献

バグ報告や機能追加提案、プルリクエストはリポジトリの Issue / PR を利用してください。技術的な議論や設計方針の改善も歓迎します。

---

README は以上です。必要であれば、セットアップ用の requirements.txt、サンプル .env.example、簡易 CLI（ETL 実行スクリプト）の追加例も作成します。どれを優先して欲しいか教えてください。