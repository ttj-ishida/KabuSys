# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（部分実装）

このリポジトリは、日本株のデータ取得・ETL、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ管理、研究用ファクター計算などを行うコンポーネント群を提供します。DuckDB を主なデータ格納先とし、J-Quants API / OpenAI（gpt-4o-mini）等と連携する設計です。

## 主要な特徴（機能一覧）

- 環境設定管理
  - .env ファイルおよび OS 環境変数から設定を自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得のラッパー（未設定時に明示的な例外を発生）

- データ ETL / DataPlatform
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - 差分 ETL（取得範囲自動算出・バックフィル対応）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS）と保存（SSRF 対策、トラッキングパラメータ削除、前処理）

- AI（OpenAI）連携
  - ニュース NLP スコアリング（銘柄ごとのセンチメントを ai_scores テーブルへ）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロ記事の LLM センチメントを合成）
  - API 安定化のためのリトライ・フェイルセーフ実装

- リサーチ用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ / トレーサビリティ
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 発注フローを UUID 連鎖でトレース可能にする DDL・インデックスを備える

## 必要条件（推奨）

- Python 3.10+
  - （コードは PEP 604 の `X | Y` 型注釈を使用しています）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（AI 機能を使う場合）
- defusedxml（RSS パーサの安全対策）
- その他標準ライブラリ以外の依存：urllib／json 等は標準

簡易な requirements（例）:
- duckdb
- openai
- defusedxml

※ 実際の `pyproject.toml` / `requirements.txt` がある場合はそちらを参照してください。

## セットアップ手順

1. リポジトリをクローン / ダウンロード

2. Python 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（例）
   ```
   pip install duckdb openai defusedxml
   # ローカルで editable インストールする場合
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動読み込みされます（ただし、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すれば自動ロードを無効化できます）。
   - 主な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI を使う場合に必要
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABUSYS_ENV — development / paper_trading / live（default: development）
     - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（default: INFO）

   例 `.env` の中身（サンプル）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

## 使い方（簡単な利用例）

以下は Python スクリプトや REPL からの簡単な呼び出し例です。

- 設定読み込み
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続と日次 ETL の実行
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は Path
  result = run_daily_etl(conn)  # target_date を指定しないと今日が対象
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI API キーが環境変数で設定されていること）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数 OPENAI_API_KEY
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（研究）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  recs = calc_momentum(conn, date(2026, 3, 20))
  # recs は [{"date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]
  ```

注意点:
- AI / OpenAI 呼び出しは外部 API コールのため料金とレート制限に留意してください。実装側でリトライ・フェイルセーフが組まれていますが、API キーの管理は適切に行ってください。
- news_collector.fetch_rss は SSRF 対策やレスポンスサイズ制限等の安全策を持っています。

## 自動ロード動作について

- kabusys.config はパッケージの位置を基準にプロジェクトルートを探索し、`.env` / `.env.local` を自動で読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` の上書きとして読み込まれます。
- 自動ロードを無効化する場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

## 主なモジュール（ディレクトリ構成の要約）

パッケージルート: src/kabusys/

- kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM を用いた銘柄別センチメント評価（ai_scores への書き込み）
    - regime_detector.py — ETF 1321 の MA200 とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — JPX カレンダー管理 / 営業日判定
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - jquants_client.py — J-Quants API クライアント（fetch / save / auth）
    - news_collector.py — RSS 取得と raw_news への保存（SSRF 対策等）
    - quality.py — データ品質チェック
    - stats.py — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログテーブル定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

（上記は主要ファイルのみ抜粋）

## 実運用上の注意事項

- OpenAI / J-Quants API キーの管理（権限・ローテーション・課金）に注意してください。
- 設計上、バックテストやリサーチでのルックアヘッドバイアス防止に配慮した実装になっています（内部で date.today() などを直接参照しない等）。これを守るため、呼び出し側で `target_date` を明示的に指定することを推奨します。
- DuckDB のバージョンや SQL 構文の互換性に注意してください（コメントに DuckDB 0.10 の挙動対処が含まれています）。
- ETL / API 呼び出しは外部ネットワークを利用するため、適切な監視・リトライ設定・エラーハンドリングを行ってください。

---

不明点や README に追加してほしい項目（例: CI / テスト手順、より詳しい例、`.env.example` のテンプレート等）があれば教えてください。必要に応じて README を拡張します。