# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。データ取得・ETL、ニュースNLP（OpenAI）、市場レジーム判定、ファクター算出、データ品質チェック、監査ログなど、取引システムを構成するコア機能を提供します。

主な設計方針：
- ルックアヘッドバイアス防止（内部で datetime.today()/date.today() を直接参照しない設計）
- DuckDB をコアデータストアに利用（冪等性を考慮した保存）
- 外部API呼び出しにはレート制御とリトライを実装
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価機能
- セキュリティ考慮（RSS収集時のSSRF対策など）

---

## 機能一覧

- 環境設定読み込み（.env / .env.local、環境変数優先）
- J-Quants API クライアント（株価、財務、マーケットカレンダー取得、トークン自動リフレッシュ、レート制御、リトライ）
- ETL パイプライン（差分取得・保存・品質チェックを含む日次 ETL）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS → raw_news、URL正規化、SSRF対策、圧縮対応）
- ニュースNLP（OpenAI で銘柄別センチメントを算出し ai_scores に保存）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース LLM スコアを合成）
- 研究用モジュール（モメンタム・ボラティリティ・バリュー等のファクター算出、将来リターン、IC 計算、Zスコア正規化）
- 監査ログ（signal_events / order_requests / executions のスキーマ定義と初期化ユーティリティ）
- ユーティリティ（統計ユーティリティ、カレンダー管理、その他）

---

## セットアップ手順

前提
- Python 3.10+ を想定（型注釈に union 表記などを使用）
- DuckDB を利用（pip インストール可能）
- OpenAI API を利用する場合は OpenAI の API キーが必要
- J-Quants のリフレッシュトークンが必要

1. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（例）
   requirements.txt がない場合は少なくとも以下をインストールしてください：
   ```bash
   pip install duckdb openai defusedxml
   ```
   他にテスト用・運用用に必要なパッケージがあれば適宜追加してください。

3. 環境変数（または .env）を準備
   プロジェクトルート（.git または pyproject.toml のある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   主要な環境変数（Settings クラスに対応）：
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注系で使用）
   - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

   例 `.env`（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース初期化（監査ログなど）
   監査用テーブルを初期化する例：
   ```python
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db(settings.duckdb_path)  # ファイルを作成して接続を返す
   ```

---

## 使い方（主要な API と実行例）

以下はライブラリの主要機能を呼び出す最小例です。実際はログ設定やエラーハンドリングを追加してください。

- DuckDB 接続の取得
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に保存
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（MA200 と マクロニュースの LLM 評価を合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマを既存接続に適用
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注意点：
- OpenAI 関係の関数は api_key 引数で明示的にキーを渡すことが可能（渡さない場合は環境変数 `OPENAI_API_KEY` を使用）。
- ETL / API 呼び出しはネットワークや外部依存があるため、例外処理を行ってください。
- DuckDB の executemany は空リストを渡せないバージョンがあるため、関数側でチェック済みです（実装参照）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主なモジュールと役割）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数と設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事を統合して銘柄単位のセンチメント（ai_scores）を算出
      - OpenAI 呼び出し、リトライ、レスポンスバリデーション
    - regime_detector.py
      - ETF(1321) の MA200 乖離とマクロニュース LLM スコアを合成して market_regime を書き込み
  - data/
    - __init__.py
    - calendar_management.py
      - JPX カレンダー管理・営業日判定・next/prev_trading_day 等
    - etl.py
      - ETLResult 再エクスポート
    - pipeline.py
      - run_daily_etl、個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - audit.py
      - 監査ログテーブルの DDL と初期化ユーティリティ
    - jquants_client.py
      - J-Quants API クライアント（認証、取得、保存関数）
    - news_collector.py
      - RSS 収集、前処理、SSRF/サイズ制限、raw_news/ news_symbols への保存ロジック
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム・ボラティリティ・バリュー等のファクター計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー

（詳細はソース内の docstring を参照してください。各関数に設計方針・入出力・例外の説明があります）

---

## 運用上の注意・設計ノート

- 自動環境読み込みの挙動：config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動読み込みします。テストや外部環境で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Look-ahead バイアス対策：AI スコアや各種計算は「対象日以前のデータのみ」を参照するように実装されています。バックテストでの使用時は ETL の取得時刻や fetched_at を考慮してください。
- 冪等性：J-Quants の保存関数や ETL は ON CONFLICT DO UPDATE などを使い冪等にデータを保存する設計です。
- エラー処理：外部 API 呼び出しはリトライやフォールバック（例：LLM が失敗した場合 macro_sentiment=0）を行います。重大な DB 書き込み失敗は例外として上位に伝播します。
- セキュリティ：news_collector では URL 正規化、トラッキングパラメータ除去、SSRF 対策、受信サイズ上限などを実装しています。

---

## テスト・開発

- 単体テストでは外部 API 呼び出し（OpenAI、J-Quants、ネットワーク）をモックすることを推奨します。実装内で外部呼び出しを分離しているため差し替えが容易です（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB のインメモリ接続（":memory:"）を使うとテストが速くなります。

---

必要であれば、README に含める具体的な .env.example や requirements.txt の推奨内容、docker-compose / systemd ユニット例、運用に関する追加ドキュメント（監視、ログローテーション、CI/CD）も作成します。どの情報を追加しますか？