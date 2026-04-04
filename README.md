# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
DuckDB を用いたデータプラットフォーム、J-Quants / OpenAI を利用したニュース NLP と市場レジーム判定、ファクター研究ユーティリティ、ETL パイプライン、監査ログ用スキーマなどを提供します。

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（ETL）
- RSS ニュース収集と OpenAI を用いた銘柄ごとのニュースセンチメント算出
- ETF（1321）を使った市場レジーム判定（移動平均乖離 + マクロニュース）
- ファクター計算（モメンタム／バリュー／ボラティリティ）および研究用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマ初期化
- DuckDB を中心としたデータ保存と冪等的な保存ロジック

パッケージ名: `kabusys`  
バージョン（現状）: `0.1.0`（src/kabusys/__init__.py）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - pipeline: 日次 ETL（カレンダー・株価・財務）と品質チェック。ETLResult を返却
  - news_collector: RSS フィード取得・前処理・raw_news 保存（SSRF / サイズ制限対策あり）
  - audit: 監査ログテーブル DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - calendar_management: JPX カレンダー管理と営業日ロジック（is_trading_day / next_trading_day 等）
  - quality: データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - stats: zscore_normalize 等の汎用統計関数
- ai/
  - news_nlp.score_news: OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント算出と ai_scores への書き込み
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書き込み
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - Settings クラス：環境変数読み込み（自動で .env/.env.local をプロジェクトルートから読み込む。無効化可）

---

## 前提（推奨環境）

- Python 3.10+（typing 構文などを利用）
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - typing-extensions（必要に応じて）
- J-Quants / OpenAI の API キー、kabu API パスワード等の環境変数

（実際の requirements はプロジェクトの package / requirements ファイルを参照してください）

---

## セットアップ手順

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用）

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（news / regime 呼び出し時に必要）
   - その他（任意／デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|...)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）

5. .env の例（プロジェクトルート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（代表的な利用例）

以下はライブラリの代表的な呼び出し方法の例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続の準備（ファイル DB を使う例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を None にすると今日（os date）が使われます
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores に保存
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム（market_regime）を算出
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査ログ DB 初期化（監査専用 DB を作る）
  ```python
  from pathlib import Path
  from kabusys.data.audit import init_audit_db

  db_path = Path("data/audit.duckdb")
  audit_conn = init_audit_db(db_path)
  ```

- ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  results = calc_momentum(conn, target_date=date(2026,3,20))
  # results は [{'date': ..., 'code': ..., 'mom_1m': ..., ...}, ...]
  ```

- 設定オブジェクトの利用
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## 実装上の注意点 / 動作ポリシー

- Look-ahead バイアス防止:
  - score_news / score_regime / ETL の各処理は内部で datetime.today() を直接参照しない設計（API 等から取得する window は target_date を明示して計算）。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定した JSON Mode を利用。API の失敗やパースエラー時はフェイルセーフでスコアにフォールバック（0.0 等）して継続する実装があります。
- J-Quants API:
  - RateLimiter、再試行、401 時の自動トークンリフレッシュ等の堅牢な処理を有します。
- .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を起点）を自動検出して `.env` / `.env.local` をロードします。既存 OS 環境変数は保護されます。テスト時に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要モジュールとディレクトリ構成

概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch/save）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult 再エクスポート
    - news_collector.py     — RSS ニュース収集
    - calendar_management.py— 営業日・カレンダーの管理
    - quality.py            — データ品質チェック
    - stats.py              — 汎用統計（zscore_normalize）
    - audit.py              — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリー 等

---

## 開発上のヒント

- テスト時は OpenAI / HTTP の呼び出しをモックすることを推奨（モジュール内の _call_openai_api / _urlopen 等を patch 可能）。
- DuckDB のバージョンによっては executemany の空リストがサポートされないため、呼び出し側で空チェックがされています。これは DB の互換性対策です。
- 多くの関数は「冪等」を前提に設計されています（INSERT ... ON CONFLICT 等）。

---

## 連絡・貢献

この README はコードベース（src/kabusys）から読み取れる仕様をまとめたものです。実際に導入・運用する際は、プロジェクトの CI / packaging / requirements ファイルや運用ドキュメントを合わせて参照してください。

バグ報告や機能要望、パッチ提案はリポジトリの Issues / PR をご利用ください。