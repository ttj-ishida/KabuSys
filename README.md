# KabuSys

日本株向けのデータプラットフォーム・リサーチ・自動売買補助ライブラリ群です。  
DuckDB を中心に J-Quants（市場データ）・RSS（ニュース）・OpenAI（ニュースNLP）などを組み合わせ、ETL、品質チェック、ファクター計算、ニュースセンチメント、監査ログの初期化・管理などを提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0 (src/kabusys/__init__.py)

## 主要機能（概要）

- data
  - ETL パイプライン（prices / financials / market calendar）の差分取得・保存（J-Quants 経由）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS → raw_news）
  - J-Quants クライアント（認証・レートリミット・リトライ・保存ユーティリティ）
  - 監査ログ（signal / order_request / executions）テーブルの初期化ユーティリティ
  - 汎用統計ユーティリティ（Zスコア正規化など）
- ai
  - ニュースセンチメント（news_nlp.score_news）: OpenAI を用いて銘柄別スコアを ai_scores に書き込む
  - 市場レジーム判定（regime_detector.score_regime）: ETF（1321）のMA乖離とマクロニュースを組み合わせて market_regime に書き込む
- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、rank 等

## 必要条件 / 推奨環境

- Python >= 3.10（PEP 604 の型表記を使用）
- 必要な Python パッケージ（主なもの）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS）

依存関係はプロジェクトの配布方法によるため、pyproject.toml / requirements.txt がある場合はそちらを参照してインストールしてください。

例:
```
python -m pip install duckdb openai defusedxml
```

（パッケージ化している場合は `pip install -e .`）

## 環境変数（必須 / 例）

このライブラリは環境変数または .env ファイルから設定を読み込みます（src/kabusys/config.py）。自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して .env → .env.local の順で読みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 実行時に必要）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注関連で使用）
- SLACK_BOT_TOKEN — Slack 通知用トークン（オプションだが config では必須扱い）
- SLACK_CHANNEL_ID — Slack チャンネルID（オプションだが config では必須扱い）

データベースパス（デフォルトあり）:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト `data/monitoring.db`）

ローカル開発用の .env（例）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（簡易）

1. リポジトリをクローン / 配布パッケージを取得
2. Python 環境を準備（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject があればそれを使用）
3. プロジェクトルートに `.env` を作成（.env.example を参考に）
4. DuckDB ファイル用ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```
5. （任意）監査用 DB を初期化:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/monitoring.db")
   conn.close()
   ```

## 使い方（主要 API / 実行例）

※ すべての操作は適切な DuckDB 接続（duckdb.connect(...)）を渡して行います。

- DuckDB 接続例:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（データ取得・保存・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # conn: DuckDB 接続
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 株価日足 ETL のみ:
  ```python
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  ```

- ニュースセンチメントスコア（銘柄別）を生成して ai_scores に保存
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査ログスキーマ初期化（既存 conn に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- 設定 (settings) の取得
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意:
- OpenAI の呼び出しは API 制限やネットワーク失敗に備えてリトライ等の保護が入っていますが、API キーは必ず正しく設定してください。
- ETL / AI モジュールはいずれも Look-ahead bias を避ける設計（target_date 未満のみ参照する等）を意識しています。

## ディレクトリ構成（主要ファイルと説明）

（パッケージルート: src/kabusys）

- __init__.py
  - パッケージエクスポート（version 等）
- config.py
  - 環境変数ロード・設定管理（Settings クラス）
- data/
  - __init__.py
  - pipeline.py — ETL のメイン実装（run_daily_etl 等）
  - etl.py — ETL 結果型のエクスポート（ETLResult）
  - jquants_client.py — J-Quants API クライアント（取得/保存）
  - news_collector.py — RSS 取得・前処理・保存ロジック
  - calendar_management.py — 市場カレンダー管理・営業日ロジック
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ（テーブル DDL / init ）ユーティリティ
- ai/
  - __init__.py
  - news_nlp.py — ニュースを batched に LLM 評価して ai_scores に保存
  - regime_detector.py — ETF の MA とマクロニュースを組み合わせた市場レジーム判定
- research/
  - __init__.py
  - factor_research.py — momentum / value / volatility の計算
  - feature_exploration.py — 将来リターン・IC・統計要約など

（その他）
- data/ 以下に DuckDB 実データファイル（デフォルト data/kabusys.duckdb）を置く想定
- monitoring.db 等の監査用 DB（デフォルト data/monitoring.db）

## 実運用時の留意点

- 認証情報・トークンは安全に管理してください（.env を Git で共有しない）。
- J-Quants のレート制限と OpenAI の利用料に注意してください。jquants_client と AI モジュールにはリトライ／レート制御が実装されていますが、運用規模により追加制御が必要です。
- ETL の実行順序や calendar の先読み等のパラメータは pipeline.run_daily_etl の引数で調整できます。
- DuckDB のスキーマ（テーブル定義）はプロジェクトのスキーマ初期化機能（別ファイルにある可能性）で作成するか、運用前に必要テーブルを作成してください。

## 開発＆テスト時のヒント

- 自動 .env 読み込みを無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- OpenAI / ネットワーク呼び出しをユニットテストでモックするため、内部の _call_openai_api や news_collector._urlopen などを patch する設計になっています。

---

問題点や追加したい機能（推奨）:
- CLI / スケジューララッパー（cron / Airflow 用の thin runner）
- スキーマ初期化スクリプト（全テーブル DDL のエントリポイント）
- 詳細な README のコマンド例（Docker / CI 設定）

必要であれば、導入手順の詳細（Dockerfile / Makefile / CI 設定例）や、テーブルスキーマ一覧、よく使う SQL クエリ例などを追記します。どの情報を優先して追加しますか？