# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログなどの機能を含みます。

主な目的は「バックテスト・リサーチ環境」と「実運用（発注含む）環境」を支えるデータ基盤と分析ユーティリティの提供です。

---

## 概要

- 言語: Python (>= 3.10)
- 主な依存: duckdb, openai, defusedxml（RSS処理用）など
- 機能群をモジュール化しており、ETL / データ品質 / ニュースNLP / レジーム判定 / ファクター計算 / 監査ログ初期化 等を提供します。
- 環境変数（`.env` / `.env.local` / OS 環境）から設定を自動読み込みします（自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

---

## 機能一覧

- 設定管理
  - `kabusys.config.Settings`：環境変数を集中管理（J-Quants トークン、OpenAIキー、DBパス、監視閾値等）
  - 自動 `.env` / `.env.local` のロード（プロジェクトルート検出）

- データ ETL / Data Platform
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動更新を含む）
  - 差分 ETL / 日次パイプライン `run_daily_etl`（prices / financials / calendar）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS）と前処理
  - 監査ログ（signal / order_request / executions テーブル）初期化ユーティリティ

- 研究（Research）
  - ファクター計算：Momentum / Value / Volatility 等
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Zスコア正規化ユーティリティ

- AI
  - ニュースセンチメントスコアリング（`score_news`）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースによる LLM 判定 -> `score_regime`）

---

## セットアップ手順

前提: Python >= 3.10, pip

1. リポジトリをクローンしてプロジェクトルートに移動
   - pip editable インストール（ローカル開発向け）
     ```
     pip install -e .
     ```

2. 必要な依存パッケージ（最低限の例）
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt があればそれを使ってください）

3. 環境変数の設定
   - プロジェクトルートに `.env` を作成することで自動読み込みされます（`.env.local` を上書き用に使えます）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を利用する場合）
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - その他（PID ファイルパス、閾値等）は `kabusys.config.Settings` を参照してください

   - 自動読み込みをテスト等で無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. データベース初期化（監査ログ用例）
   - 監査ログ DB を初期化する例（DuckDB）:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な例）

ここではいくつかの主要機能の呼び出し例を示します。日付は Python の datetime.date を使用します。

- DuckDB に接続して日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア取得（AI）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を明示的に渡すことも可能（env OPENAI_API_KEY を使う場合は省略可）
  n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {n} symbols")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログスキーマ作成（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算（例: Momentum）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(momentum), "rows")
  ```

注意:
- AI 呼び出し（OpenAI）は API レート・課金が発生します。`api_key` を直接渡すか `OPENAI_API_KEY` 環境変数を設定してください。
- `run_daily_etl` は J-Quants API への接続が必要です（JQUANTS_REFRESH_TOKEN を設定してください）。

---

## 設定（主要環境変数）

主なキーと説明（必要に応じて `.env` に記述）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視用
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

---

## ディレクトリ構成

主要ファイルとモジュール（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                          -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       -- ニュース NLP / score_news
    - regime_detector.py                -- 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py                 -- J-Quants API クライアント & DuckDB 保存
    - pipeline.py                       -- ETL パイプライン実装（run_daily_etl 等）
    - etl.py                            -- ETLResult 再エクスポート
    - quality.py                         -- データ品質チェック
    - stats.py                           -- 統計ユーティリティ（zscore_normalize）
    - news_collector.py                  -- RSS 取得 / 前処理 / 保存ロジック
    - calendar_management.py             -- 市場カレンダー管理（trading_day 判定 等）
    - audit.py                           -- 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py                -- Momentum/Value/Volatility の計算
    - feature_exploration.py            -- 将来リターン, IC, rank, summary
  - research/...（その他ユーティリティ）
  - monitoring (参照はあるが実装は別途)

付属ドキュメント参照:
- 各モジュールの docstring に設計方針・処理フロー・注意事項が詳細に記載されています。実装の利用前に該当ファイルの docstring を参照してください。

---

## 運用上の注意

- 本ライブラリは「実運用（ライブ注文）」を想定した設計要素を含みます（監査ログ、冪等キー、設定で live/paper 環境判定 等）。ライブ環境で利用する場合は設定・権限・テストを十分に行ってください。
- OpenAI / J-Quants の API キーは安全に管理してください（公開リポジトリに含めない、CIシークレットに登録する等）。
- DuckDB のスキーマは ETL / audit 関数が作成する前提です。既存 DB と競合しないように注意してください。
- ニュース収集では外部 HTTP を扱うため SSRF/サイズ上限/XML攻撃等に対する保護処理が実装されていますが、運用前にソース設定やネットワークポリシーを確認してください。

---

## 参考 / 開発ヒント

- テスト / 開発中は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って環境を明示的に制御できます。
- OpenAI 呼び出し部分は内部で呼び出し関数を差し替えられる設計（ユニットテスト用にモックしやすい）。
- DuckDB による SQL 実装は SQL の理解があるとカスタマイズしやすい設計です（OVERVIEW: 多くの集計/ウィンドウ処理を SQL で実行）。

---

必要であれば、セットアップ用の `requirements.txt` の推奨内容、具体的な SQL スキーマやサンプル `.env.example` を作成します。どの部分を優先して補足しましょうか？