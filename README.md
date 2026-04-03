# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）→ DuckDB による時系列データ管理、ニュースNLP（OpenAI）による銘柄センチメント、リサーチ向けファクター計算、監査ログ（発注/約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主要機能

- データ ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル・ページネーション・リトライ実装
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付整合性チェック
- ニュース収集 / 前処理
  - RSS から記事収集、URL正規化、SSRF 防止、前処理
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを LLM でスコア化して `ai_scores` に保存（gpt-4o-mini, JSON mode）
  - マクロニュースから市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリ、Zスコア正規化
- 監査ログ（発注・約定トレース）
  - signal_events / order_requests / executions を含む監査テーブルの初期化・管理

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（代表）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, logging, datetime など

（実際の開発・運用環境では pyproject.toml / requirements.txt を参照してください）

---

## 環境変数（主なもの）

プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

主に利用する環境変数の例:

- J-Quants / ETL
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
- kabuステーション（発注など）
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- システム
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- DBパス
  - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
  - SQLITE_PATH: 監視用 sqlite データベース（デフォルト `data/monitoring.db`）

設定は `kabusys.config.settings` からアクセスできます。

---

## セットアップ手順（開発環境向け例）

1. レポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 最低限:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発インストール（プロジェクトに setuptools/poetry が用意されていれば）
     ```bash
     pip install -e .
     ```

4. `.env` を作成（`JQUANTS_REFRESH_TOKEN` など必須値を設定）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

5. DuckDB ファイル用ディレクトリ作成（必要であれば）
   ```bash
   mkdir -p data
   ```

---

## 基本的な使い方（コード例）

以下はライブラリをインポートして主要機能を呼ぶサンプルです。実行には上記の環境変数や DuckDB のスキーマ（テーブル）が揃っている必要があります。

- DuckDB 接続の作成例:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると today が使われます
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア付与（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数で設定されているか、api_key を渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書込み銘柄数:", written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DuckDB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査テーブルへ書き込み可能
  ```

- カレンダー更新ジョブ（J-Quants から取得）
  ```python
  from datetime import date
  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

注意:
- OpenAI 呼び出しには `OPENAI_API_KEY` が必要です（関数に `api_key=` で渡してもよい）。
- 多くの関数は DuckDB の特定のテーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, prices_daily, market_calendar 等）を前提とします。テーブル定義（スキーマ）や初期化処理はプロジェクト内別モジュール／ドキュメントで管理されます。

---

## 開発メモ / 実装上の注意

- .env 自動読み込み
  - `src/kabusys/config.py` はプロジェクトルート（.git または pyproject.toml のある場所）から `.env` / `.env.local` を自動ロードします。
  - 自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに便利です）。

- Look-ahead バイアス対策
  - LLM スコアや各種時系列処理は内部で target_date 未満のデータのみを参照するなど、ルックアヘッドバイアスに配慮した実装になっています。バックテストや再現性の面でも意識して使用してください。

- リトライ / フェイルセーフ
  - J-Quants API や OpenAI 呼び出しはリトライ戦略（指数バックオフ）を備え、致命的な API エラー時はフェイルセーフ（スコアを 0.0 にフォールバック 等）で継続する設計です。

- テストとモック
  - OpenAI 呼び出し部分やネットワークアクセスはモックしやすいように分離された関数（例: `_call_openai_api`, `_urlopen`）になっています。ユニットテストではこれらを patch して副作用を制御してください。

---

## ディレクトリ構成（主要ファイルの説明）

（root: `src/kabusys/` 配下）

- __init__.py
  - パッケージ公開内容とバージョン定義

- config.py
  - 環境変数の自動読み込み / Settings クラス（アプリ設定取得）

- ai/
  - news_nlp.py: ニュースを LLM（OpenAI）でスコアリングして `ai_scores` に書き込むロジック
  - regime_detector.py: ETF 1321 の MA200 とマクロニュースセンチメントを組み合わせて市場レジーム判定

- data/
  - jquants_client.py: J-Quants API クライアント（取得・保存ロジック含む）
  - pipeline.py: ETL パイプライン（run_daily_etl / run_*_etl 等）
  - calendar_management.py: 市場カレンダー管理 / 営業日判定
  - news_collector.py: RSS 取得・前処理・raw_news への保存サポート
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py: 共通統計ユーティリティ（z-score 正規化 等）
  - audit.py: 監査ログ（signal_events / order_requests / executions）テーブル初期化
  - etl.py: pipeline.ETLResult の再エクスポート

- research/
  - factor_research.py: モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py: 将来リターン / IC / ステータス集計 等
  - __init__.py: 研究向けユーティリティ公開

- ai/__init__.py, research/__init__.py, data/__init__.py
  - 各サブパッケージの公開 API

---

## よくある質問 / トラブルシューティング

- OpenAI の JSON Mode が期待した JSON を返さない場合
  - 実装側はレスポンスの JSON パース失敗時にフォールバックしてスコア 0.0 を使うようになっています。テスト時はモックで安定した出力を与えることを推奨します。

- DuckDB の executemany に空リストを渡してエラーになる
  - 一部の処理は空リストを渡さないようにガードしています。自前の呼び出しでも空の書き込みを避けてください。

---

## ライセンス・貢献

本 README はコードベースから生成された概要ドキュメントです。実際のライセンス・貢献フロー（CONTRIBUTING.md、CODE_OF_CONDUCT 等）はレポジトリルートの該当ファイルを参照してください。

---

以上。導入や実行に際して、具体的なスキーマ（DuckDB のテーブル定義）や運用手順（cron / バッチ設定、ログ収集、監視）は別途運用ドキュメントを用意することを推奨します。必要であればそのドキュメントも作成しますので教えてください。