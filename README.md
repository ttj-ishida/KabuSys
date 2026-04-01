# KabuSys

日本株向け自動売買／データ基盤ライブラリ KabuSys の README。

このリポジトリは、J-Quants / JPX をソースとしたデータ ETL、ニュース収集・NLP、研究用ファクター計算、監査ログ、ならびに市場レジーム判定などの機能を提供します。バックテストや自動売買システムの基盤コンポーネントとして設計されています。

---

## プロジェクト概要

- 目的：J-Quants API 等から日本株データを差分で取得し、DuckDB に保存・品質チェックを行うデータパイプライン、ニュース収集と LLM を用いたセンチメントスコアリング、ファクター計算・探索、監査ログ（発注〜約定のトレーサビリティ）など、売買システムの基礎機能を提供する。
- 設計方針の特徴：
  - ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を直接参照しない設計が多い）
  - DuckDB を中心としたローカル DB
  - J-Quants API や OpenAI（gpt-4o-mini）を利用する箇所はリトライ／バックオフやフェイルセーフを備える
  - 冪等性（ON CONFLICT / idempotent 保存）を重視

---

## 主な機能一覧

- データ ETL
  - 差分取得・差分保存（株価、財務、JPX カレンダー）
  - 品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - ETL 結果を表す ETLResult クラス
- J-Quants クライアント（jquants_client）
  - 認証（refresh token → id token）
  - fetch / save 機能（株価、財務、上場情報、カレンダー）
  - レートリミッタ、リトライ、トークン自動更新
- ニュース収集（news_collector）
  - RSS フィード取得、前処理、SSRF 対策、トラッキングパラメータ除去、raw_news への冪等保存
- ニュース NLP（ai.news_nlp）
  - OpenAI を用いた銘柄ごとのセンチメントスコアリング（チャンク／バッチ処理、結果バリデーション、DuckDB へ保存）
- レジーム判定（ai.regime_detector）
  - ETF (1321) の 200 日移動平均乖離 + マクロニュース LLM センチメントを合成して日次レジーム判定（bull/neutral/bear）
- 研究用モジュール（research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー、Zスコア正規化ユーティリティ
- 監査ログ（data.audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ（DuckDB）
  - 監査証跡のためのテーブル設計・初期化関数
- 設定管理（config）
  - .env 自動ロード（プロジェクトルートを探索）と Settings クラス経由で環境変数を取得
  - 自動ロード無効化フラグあり（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## 必要環境 / 依存パッケージ

想定される最低限の依存パッケージ（実際の pyproject/requirements に依存してください）：

- Python 3.10+
- duckdb
- openai
- defusedxml

（上記に加え、標準ライブラリのみで多くが実装されています）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```

   実プロジェクトでは pyproject.toml / requirements.txt があればそちらを利用してください：
   ```bash
   pip install -r requirements.txt
   # or
   pip install -e .
   ```

4. 環境変数を設定
   プロジェクトルートに `.env`（もしくは `.env.local`）を配置すると自動で読み込まれます（configモジュールが .git または pyproject.toml を起点に探索します）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（config.Settings 参照）：
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API のパスワード（発注等で使用）
   - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必要な場合）
   - SLACK_CHANNEL_ID — Slack チャンネル ID
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime を実行する際）
   - その他（任意・デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — 実行モード
     - LOG_LEVEL (DEBUG|INFO|...)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

   簡単な .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡易サンプル）

以下は Python REPL / スクリプトでの利用例です。DuckDB の接続は `duckdb.connect()` を使います。

- ETL（1日分のデータを取得して品質チェックまで行う）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアリング（ai.news_nlp.score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定しておく
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # もしくは既存の接続に対して init_audit_schema(conn)
  ```

- J-Quants の直接利用（テストや詳細取得）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  # id_token を自動取得して利用可能
  records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
  ```

注意:
- OpenAI API 呼び出しはコストとレート制限があるため、本番での取り扱いに注意してください。
- ETL / save 系関数は DuckDB のスキーマに依存します。運用前にスキーマ（テーブル）を準備してください。

---

## 主要ファイル / ディレクトリ構成

（ルート: src/kabusys を起点に主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py        — 市場レジーム判定（1321 MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（fetch/save, 認証, rate limiter）
    - pipeline.py               — ETL パイプライン / run_daily_etl 等
    - etl.py                    — ETL 公開インターフェース（ETLResult エクスポート）
    - news_collector.py         — RSS ニュース収集・前処理・SSRF 対策
    - quality.py                — 品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py                  — z-score 正規化など共通統計ユーティリティ
    - calendar_management.py    — JPX カレンダー管理 / 営業日判定
    - audit.py                  — 監査ログ DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py        — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py    — 将来リターン / IC / summary / rank
  - monitoring/ (存在が暗示されるが詳細はソース参照)

（各ファイルは詳細な docstring / コメントを備えており、関数単位での挙動と設計思想が明記されています）

---

## 開発上の注意点 / 運用メモ

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml の所在）を基準に行われます。CI/CD やテスト時に自動ロードを防ぎたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI への呼び出し部分はリトライやフェイルセーフ（失敗時は 0.0 を返す等）を備えていますが、API のコスト・レートに注意して運用してください。
- jquants_client は 120 req/min のレート制限に合わせた内部制御（固定間隔スロットリング）を実装しています。
- DuckDB の executemany は空リストを受け付けないバージョン依存の制約があるため、コード内で空チェックが行われています。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT）。運用時のバックアップやアーカイブポリシーを検討してください。

---

## ライセンス / 貢献

本 README 内にはライセンス情報が含まれていません。実際のリポジトリに LICENSE ファイルや CONTRIBUTING.md がある場合はそれに従ってください。

---

問題点の報告や改善提案があれば、リポジトリの Issue に記載してください。README の追記やサンプルスクリプト等を追加していくと使いやすくなります。