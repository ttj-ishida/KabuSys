# KabuSys

日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。  
データのETL、ニュースの自然言語処理による銘柄スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（オーディット）スキーマなどを含んでいます。

主な設計方針
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を不用意に参照しない）
- DuckDB を主要な分析用 DB として利用
- J-Quants / OpenAI / RSS からのデータ取得を想定した堅牢なリトライ／サニティチェック
- ETL・品質チェック・監査ログを含むデータ運用向け機能群

---

## 機能一覧

- 環境設定管理
  - .env ファイル（プロジェクトルート）を自動読み込み（必要に応じて無効化可能）
  - 必須設定は Settings 経由で取得・検証

- データプラットフォーム（kabusys.data）
  - J-Quants API クライアント（fetch / save / pagination / retry / rate limit 対応）
  - ETL パイプライン（prices / financials / market calendar の差分取得・保存）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - マーケットカレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS -> raw_news、SSRF対策、前処理）
  - 監査ログスキーマ初期化（signal / order_request / executions 等）
  - 監査DBの初期化ユーティリティ（DuckDB）

- AI / NLP（kabusys.ai）
  - ニュースをまとめて OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores へ書込む（score_news）
  - マクロニュースと ETF（1321）の MA200乖離を合成して市場レジームを日次判定・保存する（score_regime）
  - API 呼び出しは堅牢なリトライ・フェイルセーフ実装

- リサーチツール（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）算出、ファクター統計サマリ
  - z-score 正規化ユーティリティ（kabusys.data.stats から提供）

---

## セットアップ手順

前提
- Python 3.10 以上
- Git

1. リポジトリをクローンし、作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（推奨）
   - Unix/macOS
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール
   - 開発環境に合わせて必要な依存をインストールしてください。主要な依存例:
     ```
     pip install duckdb openai defusedxml
     ```
   - パッケージ化されている場合:
     ```
     pip install -e .
     ```

4. 環境変数を設定
   - プロジェクトルートの `.env` または OS 環境変数で指定します。自動読み込みはデフォルトで有効です。
   - 自動Envロードを無効にするには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. サンプル `.env`（例）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=your_openai_api_key

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # LINE通知（任意）
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な例）

※ 以下はライブラリ API を直接呼ぶ例です。プロダクション用途ではラッパースクリプトやジョブスケジューラから呼び出してください。

1. DuckDB に接続して ETL を実行する（日次 ETL）
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュースのセンチメントをスコア化して ai_scores テーブルへ書き込む
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"書き込み銘柄数: {written}")
   ```
   - OpenAI API キーは `OPENAI_API_KEY` 環境変数で指定。`api_key` 引数からも注入可能。

3. 市場レジーム判定（score_regime）
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

4. 監査ログ（オーディット）DB の初期化
   ```python
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")
   # conn は DuckDB 接続。テーブルが生成されています。
   ```

5. 環境設定をコード内で参照
   ```python
   from kabusys.config import settings

   print(settings.duckdb_path)
   print(settings.env, settings.log_level)
   ```

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

必須のもの（未設定時は Settings が ValueError を投げます）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD（発注周りを使う場合）
- OPENAI_API_KEY（AI 機能を使う場合）

---

## ディレクトリ構成

リポジトリは src パッケージ配下にライブラリを配置する構成です（例: src/kabusys）。

主要ファイル/ディレクトリ
- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の自動読み込み・Settings クラス
- src/kabusys/ai/
  - news_nlp.py: ニュースのセンチメントスコアリング（score_news）
  - regime_detector.py: マクロ + ETF MA200 による市場レジーム判定（score_regime）
- src/kabusys/data/
  - jquants_client.py: J-Quants API client（fetch/save）
  - pipeline.py: ETL 実行ロジック（run_daily_etl 等）
  - quality.py: データ品質チェック
  - calendar_management.py: 市場カレンダー管理・営業日判定
  - news_collector.py: RSS 取得・前処理・保存
  - audit.py: 監査ログ（DDL / 初期化）
  - etl.py: ETLResult の公開 re-export
  - stats.py: z-score 正規化等の統計ユーティリティ
- src/kabusys/research/
  - factor_research.py: ファクター計算（momentum/volatility/value）
  - feature_exploration.py: forward returns / IC / factor summary / rank
- src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py
  - 主要関数を再エクスポート

---

## 注意事項 / 運用上のポイント

- OpenAI や J-Quants は有料 API である場合があります。API キーの管理・利用コストに注意してください。
- ETL・API 呼び出しはリトライとレート制御を実装していますが、長時間の障害や継続的な失敗は運用で監視してください。
- DuckDB に対する executemany の空リストは一部バージョンで問題となるためコードで対処済みです。
- テストや CI で .env の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監査ログのスキーマは冪等的に初期化され、UTC タイムゾーンでの記録を期待します。

---

## 貢献・拡張

- ニュースソースの追加 → data/news_collector.py の DEFAULT_RSS_SOURCES に追加
- 新しいファクターの追加 → research/factor_research.py に実装し、research パッケージで公開
- 発注・実行周りは execution モジュール（プロジェクト内に存在する想定）と連携して利用してください

---

この README はコードベースの主な使い方・構成をまとめたものです。詳細な API 使用方法や運用手順は該当モジュールの docstring（コード内コメント）を参照してください。必要であればサンプルスクリプトや CI 設定のテンプレートを追加しますのでご指示ください。