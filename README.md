# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）のリポジトリ向け README。

このドキュメントはプロジェクトの概要、主要機能、セットアップ手順、簡単な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants 経由）、ETL、データ品質チェック、ニュース収集・NLP（LLM を利用したセンチメント）、市場レジーム判定、監査ログ（発注→約定のトレーサビリティ）等を統合したライブラリです。主な用途は次のとおりです。

- データ基盤（株価、財務、マーケットカレンダー、ニュース）の差分取得と DuckDB 保存（ETL）
- データ品質チェック（欠損／重複／スパイク／日付整合性）
- ニュース収集と LLM による銘柄センチメントスコア付与
- マクロセンチメントとテクニカル指標を組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー）と探索ツール
- 発注 — 約定に至る監査ログスキーマ（監査用 DuckDB 初期化ユーティリティ）
- J-Quants API を使った堅牢なクライアント実装（レート制御、リトライ、トークン自動リフレッシュ）

設計方針としては「ルックアヘッドバイアスを避ける」「ETL/DB 操作は冪等（idempotent）」「外部 API 呼び出しはリトライ + フェイルセーフ」などが採用されています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（差分取得、保存、品質チェック）
  - J-Quants API クライアント（取得・保存関数）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news、SSRF 対策、前処理）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - 統計ユーティリティ（Zスコア正規化）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ai/
  - news_nlp: ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）でスコア化
  - regime_detector: ETF（1321）の MA とマクロニュースの LLM スコアを合成して市場レジーム判定
- research/
  - factor_research: モメンタム・ボラティリティ・バリューの計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー、ランク変換
- config
  - 環境変数 / .env 自動ロード（プロジェクトルート探索、.env/.env.local）

その他、堅牢な HTTP リクエスト、レートリミット（固定間隔スロットリング）、JSON パースの回復ロジックなど。

---

## 前提（推奨環境）

- Python 3.10 以降（typing の新しい構文、型ヒントの使用のため）
- 必須パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI API）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - プロジェクトに requirements.txt がない場合は最小セットをインストールします。
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 開発用に editable install（パッケージ構成に応じて）:
   ```bash
   pip install -e .
   ```

4. 環境変数設定
   プロジェクトルート（.git のあるディレクトリ）に `.env` または `.env.local` を作り、必要な環境変数を設定します。自動で読み込まれます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - KABU_API_PASSWORD=<kabu_api_password>
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 必要に応じて
   - SLACK_BOT_TOKEN=<slack_token>
   - SLACK_CHANNEL_ID=<channel_id>
   - OPENAI_API_KEY=<openai_api_key>
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development | paper_trading | live
   - LOG_LEVEL=INFO | DEBUG | WARNING | ERROR

   例（.env の一部）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. DB ディレクトリ作成
   DuckDB ファイルの親ディレクトリを作成しておきます（init_audit_db 内でも自動作成されますが事前準備推奨）。
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単なサンプル）

以下はライブラリの代表的な利用例です。スクリプト内で Python API を呼び出して使います。

- DuckDB 接続を作成して日次 ETL を実行する（J-Quants から差分取得して保存・品質チェック）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースをスコアリングして ai_scores テーブルへ書き込む（OpenAI API key 必須）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"written scores: {written}")
  ```

- 市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ書き込む:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用の DuckDB を初期化（テーブル作成）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成
  ```

- Research 用ファクター計算の例:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026,3,20)
  mom = calc_momentum(conn, d)
  vol = calc_volatility(conn, d)
  val = calc_value(conn, d)
  ```

注意:
- score_news / score_regime は OpenAI を呼びます。APIキー（OPENAI_API_KEY）を `.env` に設定するか引数で渡してください。
- 日付の扱いは「ルックアヘッドバイアス防止」を重視しており、target_date を明示的に渡す設計です。内部で date.today() に依存しない処理が多くあります。

---

## 自動環境変数読み込みについて

- pakage の起点（この module の config）はプロジェクトルートを .git または pyproject.toml から探索し、そのルートにある `.env` / `.env.local` を自動読み込みします。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テスト用途等）。

---

## ディレクトリ構成（主なファイル）

以下は `src/kabusys` 配下の主要ファイル一覧です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースセンチメント計算（OpenAI）
    - regime_detector.py          — 市場レジーム判定（ETF + マクロ）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント + 保存関数
    - pipeline.py                 — ETL パイプライン
    - etl.py                      — ETLResult 再エクスポート
    - calendar_management.py      — 市場カレンダー管理
    - news_collector.py           — RSS 収集と前処理
    - quality.py                  — データ品質チェック
    - stats.py                    — 統計ユーティリティ（zscore_normalize）
    - audit.py                    — 監査ログ（DDL / init）
  - research/
    - __init__.py
    - factor_research.py          — Momentum, Volatility, Value 計算
    - feature_exploration.py      — forward returns, IC, summary, rank
  - monitoring/ (存在が示唆されるが省略)
  - strategy/ (戦略モジュール領域、実装はプロジェクト次第)
  - execution/ (注文実行・ブローカー連携領域)

---

## 注意事項 / 運用上のポイント

- OpenAI 呼び出しは有料 API を使用するためコストに注意ください。開発時はモック化ができるように設計されています（内部呼び出し関数を patch して差し替え可能）。
- J-Quants API のレート制限や認証フロー（refresh token → id token）が組み込まれています。refresh token は安全に管理してください。
- ETL / DB 書き込みは冪等性を意識した実装（ON CONFLICT や個別 DELETE → INSERT の戦略）です。部分失敗時のデータ保護を考慮しています。
- 本ライブラリは「バックテストループ内での直接 API 呼び出し」を想定していません。バックテスト用途では事前に ETL でデータを取り込み、そこから読み込む形で使用してください（Look-ahead Bias を防ぐため）。

---

## 追加情報 / 拡張

- 監視・アラート（Slack 通知）や実際の発注実行は別モジュール（execution / monitoring）に実装する想定です。SLACK_BOT_TOKEN / SLACK_CHANNEL_ID は通知に利用されます。
- strategy/ 層にはシグナル生成やリスク管理ロジックを実装し、監査テーブルへシグナル・発注を記録してから実行系へ渡すワークフローが推奨されます。

---

この README はコードの現状コメントと公開 API をもとに作成しています。実際の運用・デプロイ時には .env.example の整備、requirements.txt / pyproject.toml の依存明記、CI やテストスイートの整備を推奨します。必要があれば README の CLI 操作例や詳細な環境変数一覧、テーブルスキーマの説明を追記します。