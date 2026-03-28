# KabuSys

日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。  
J-Quants / RSS / OpenAI 等の外部データを取り込み、ETL・品質チェック・ニュースセンチメント・市場レジーム判定・ファクター計算・監査ログ機能を提供します。

---

## 主要な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの株価日足（OHLCV）、財務データ、JPXカレンダー取得（差分取得・ページネーション対応）
  - ETL パイプライン（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - DuckDB へ冪等保存（ON CONFLICT / upsert 相当）

- データ品質管理
  - 欠損データ、スパイク（急変）、重複、日付不整合の検出（quality モジュール）
  - 品質チェックの集約実行（run_all_checks）

- ニュース収集・NLP
  - RSS フィード取得と前処理（SSRF/サイズ/トラッキング除去対策）
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（news_nlp）
  - 銘柄ごとの ai_scores 生成（バッチ・リトライ・JSON 検証）

- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（bull/neutral/bear）
  - フェイルセーフ／リトライ実装（regime_detector）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルとインデックスを初期化するヘルパー（init_audit_schema / init_audit_db）
  - 発注フローの UUID 連鎖でトレーサビリティ確保

- 研究・因子計算
  - モメンタム、ボラティリティ、バリュー等の因子計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）、Zスコア正規化などのユーティリティ

---

## 必要条件（依存）

- Python 3.9+（typing 機能を多用）
- pip パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

（プロジェクト化されている場合は setup.cfg/pyproject.toml の依存を参照してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトの requirements.txt / pyproject を利用:
   pip install -e .
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成すると自動で読み込まれます（但し KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 最低限設定する環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=your_slack_token
     - SLACK_CHANNEL_ID=your_slack_channel
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development  # development | paper_trading | live
     - LOG_LEVEL=INFO

   例（.env の最小例）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   DUCKU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（クイックスタート）

以下は主な機能のプログラム的な利用例です。DuckDB 接続にはパス（settings.duckdb_path）を利用するのが便利です。

- ETL（日次パイプライン）の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア生成（ai_scores 書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {written} codes")
  ```

- 市場レジーム判定（market_regime への書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を env に設定している場合 None 可
  ```

- 監査ログ DB 初期化（監査用 DuckDB を新規作成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査テーブルを操作できます
  ```

- 設定取得（settings）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live, settings.log_level)
  ```

注意点:
- OpenAI への呼び出しは API キー（OPENAI_API_KEY）を必要とします。api_key 引数を明示的に渡すことも可能です。
- DuckDB のテーブルスキーマはプロジェクトの初期化手順（別モジュール）で用意する必要があります。ETL 実行前に適切なスキーマが存在していることを確認してください（初期化ユーティリティがある場合はそれを使用）。

---

## よくある操作・ヒント

- 自動 env ロードを無効にする:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  テスト時などで .env の自動読み込みを抑制する場合に使用します。

- OpenAI 呼び出しのテスト:
  - モジュール内の _call_openai_api を unittest.mock.patch で差し替えてテスト可能です（news_nlp/regime_detector 共に設計済み）。

- J-Quants 認証:
  - get_id_token() が refresh token を使って id token を取得します。通常は settings.jquants_refresh_token を .env で設定します。

- ニュース RSS の安全対策:
  - レスポンスサイズ上限、SSRF（プライベートアドレス）チェック、gzip の解凍上限など安全性考慮が組み込まれています。

---

## ディレクトリ構成（主なファイル・モジュール解説）

リポジトリ内の主なパッケージは `src/kabusys` 配下です。主要モジュールの概要を示します。

- src/kabusys/
  - __init__.py               - パッケージエントリ（__version__ 等）
  - config.py                 - 環境変数 / 設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py             - ニュースセンチメントバッチ処理（score_news）
    - regime_detector.py      - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       - J-Quants API クライアント・DuckDB への保存
    - pipeline.py             - ETL パイプライン（run_daily_etl 等）
    - etl.py                  - ETLResult の再公開
    - news_collector.py       - RSS ニュース収集・前処理
    - calendar_management.py  - 市場カレンダー（営業日判定・更新ジョブ）
    - quality.py              - 品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py                - 監査ログスキーマ初期化 / init_audit_db
    - stats.py                - 汎用統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py      - モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  - 将来リターン・IC・統計サマリー
  - monitoring/ (パッケージとして __all__ にあるが詳細はコード参照)
  - strategy/, execution/, monitoring/  - 上位 API のための名前空間（実装に応じて拡張）

各モジュールは関数ごとに docstring が充実しており、Look-ahead バイアス回避や冪等性、フェイルセーフ設計が随所に反映されています。

---

## ライセンス・貢献

- ライセンス・貢献方針はリポジトリのトップレベル文書（LICENSE / CONTRIBUTING）を参照してください（本サンプルコードには明記されていません）。

---

何か特定の導入手順（CI、テーブルスキーマ初期化、外部サービス連携例など）を README に追記したい場合は、利用シーンを教えてください。具体例を追加してドキュメントを拡張します。