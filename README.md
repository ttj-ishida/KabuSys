# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。J-Quants / DuckDB を中心にデータ収集・品質管理・ファクター計算・ニュースNLP・市場レジーム判定・監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の研究・ETL・監視・自動売買パイプライン構築を支援するライブラリ群です。主な目的は次のとおりです。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に冪等保存する（ETL パイプライン）
- 取得データの品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース記事の収集と LLM（OpenAI）によるセンチメント評価（銘柄別 ai_score）
- マーケットレジーム判定（ETF とマクロニュースの組み合わせ）
- 研究用ファクター（モメンタム・バリュー・ボラティリティ等）計算
- 発注／約定のトレーサビリティを担保する監査ログスキーマ（DuckDB）

設計方針として、ルックアヘッドバイアスの回避、冪等性、フェイルセーフ性、外部サービス（OpenAI, J-Quants）へのリトライ・レート制御等を重視しています。

---

## 機能一覧

- データ収集（J-Quants）
  - 株価日足（OHLCV）、財務諸表、上場情報、JPX カレンダー
  - ページネーション・401自動リフレッシュ・レート制限対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック、日次ジョブ（run_daily_etl）
- データ品質チェック
  - 欠損データ、スパイク、重複、将来日付／非営業日データ検出
- ニュース収集・NLP
  - RSS から記事取得（SSRF 対策、トラッキング除去）
  - OpenAI を用いた銘柄別センチメント（score_news）
- マーケットレジーム判定
  - ETF(1321)のMA乖離 + マクロニュースセンチメントの合成（score_regime）
- 研究ツール
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC 計測、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events, order_requests, executions の監査テーブルと初期化ユーティリティ

---

## 要件 / 依存関係

- Python 3.10+
- duckdb
- openai
- defusedxml

（開発環境や追加ツールがある場合は requirements.txt / pyproject.toml を参照してください）

例（最低限のパッケージインストール）:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. Python を用意（3.10 以上推奨）。

2. リポジトリをクローン / 取得し、パッケージをインストール（editable 推奨）:
   - pip install -e . もしくは必要パッケージを個別インストール。

3. 環境変数 / .env を用意する
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須となる主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=sk-...
   - 任意 / デフォルト:
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - LOG_LEVEL=INFO

   サンプル .env（例）
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

4. DuckDB データベースファイルの準備
   - デフォルトは data/kabusys.duckdb。ディレクトリがなければ自動作成する処理を使う関数（audit.init_audit_db など）を呼べます。

5. 監査スキーマ初期化（必要に応じて）
   - init_audit_db を使うと監査用 DB を初期化して接続を返します。

---

## 簡単な使い方（コード例）

以下は最小限の利用例です。適宜 logging を設定して実行してください。

- DuckDB 接続を作成して日次 ETL を実行する:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# 日次 ETL を実行（target_date を省略すると本日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニューススコアリング（OpenAI API キーは引数 or 環境変数 OPENAI_API_KEY）:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")

- 市場レジーム判定:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))

- 監査スキーマ初期化（監査用 DB を作成）:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests 等を参照・操作できる

注: 上記関数は DuckDB のテーブルスキーマ前提で動作します。初期スキーマ作成/DDL を別途用意するか、audit.init_audit_schema 等を利用してください。

---

## 実行上の注意点

- OpenAI 呼び出し回数や J-Quants へのリクエストはそれぞれ仕様上レート制限・リトライを行いますが、API鍵の制限や料金に注意してください。
- 本ライブラリはルックアヘッドバイアスを避ける設計が多くの箇所で採用されています（target_date を明示して処理する等）。バックテストでの使用時は target_date を適切に設定してください。
- 自動環境変数読み込みはプロジェクトルート（.git または pyproject.toml）が検出される場合にのみ行われます。CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数・設定管理（settings）
- ai/
  - __init__.py (score_news を公開)
  - news_nlp.py
    - ニュース集約・OpenAI による銘柄別センチメント算出 (score_news)
  - regime_detector.py
    - ETF MA 乖離 + マクロニュースで市場レジーム判定 (score_regime)
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント、保存関数（save_*）
  - pipeline.py
    - ETL パイプラインの実装（run_daily_etl 等）、ETLResult
  - etl.py
    - ETLResult の再エクスポート
  - calendar_management.py
    - JPX カレンダーの管理・営業日判定ユーティリティ
  - news_collector.py
    - RSS 取得・前処理・raw_news 保存
  - quality.py
    - データ品質チェック
  - stats.py
    - zscore 正規化 等の共通統計ユーティリティ
  - audit.py
    - 監査ログスキーマ作成、init_audit_db / init_audit_schema
- research/
  - __init__.py
  - factor_research.py
    - momentum / value / volatility の計算
  - feature_exploration.py
    - calc_forward_returns, calc_ic, factor_summary, rank
- research/* その他の研究系ヘルパー

---

## 開発 / テスト

- 自動環境読み込みを抑止する:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- OpenAI 呼び出し等をユニットテストでモックする設計になっています（内部の _call_openai_api は差し替え可能）。

---

## ライセンス / 貢献

このリポジトリのライセンスや貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

README は以上です。必要であれば「.env.example」の具体的テンプレートや、よく使う CLI スクリプト（ETL cron 例、監視ジョブ起動例）を追記します。どの情報を追加しますか？