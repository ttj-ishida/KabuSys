# KabuSys — 日本株自動売買プラットフォーム（README）

このリポジトリは「KabuSys」と名付けられた日本株向けの自動売買 / データプラットフォームです。データ収集（J-Quants、RSS）、ETL、データ品質チェック、監査ログ、研究（ファクター計算）、および LLM を用いたニュースセンチメント評価／市場レジーム判定を含むコンポーネントを備えています。

以下はコードベース（src/kabusys）に基づく README です。

## プロジェクト概要
- データ取得: J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存。
- ニュース収集: RSS フィードを安全に収集し raw_news に保存、銘柄紐付けを行う。
- データ品質: 欠損・重複・スパイク・日付不整合を検出するチェック機能を提供。
- 監査ログ: シグナル → 発注 → 約定までのトレーサビリティを保証する監査スキーマ（DuckDB）。
- 研究機能: ファクター計算（モメンタム・バリュー・ボラティリティ等）や将来リターン／IC 計算。
- AI モジュール: OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai.score_news）と市場レジーム判定（ai.score_regime）。
- 運用モード: 環境変数により `development` / `paper_trading` / `live` を切替可能。

## 主な機能一覧
- data/
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants クライアント（取得・保存・認証・レート制御・リトライ）
  - news_collector（RSS 取得、SSRF 対策、トラッキング除去、前処理）
  - calendar_management（営業日判定・カレンダー更新ジョブ）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - audit（監査テーブル作成・監査 DB 初期化）
  - stats（z-score 正規化ユーティリティ）
- research/
  - factor_research（mom / value / volatility 等のファクター計算）
  - feature_exploration（forward returns, IC, 統計サマリー等）
- ai/
  - news_nlp（銘柄ごとのニュースセンチメント取得）
  - regime_detector（ETF + マクロニュースを組み合わせた市場レジーム判定）
- config.py
  - 環境変数の自動読み込み（`.env` / `.env.local` の優先度制御）と設定ラッパー（settings）

## 必要環境 / 依存
- Python 3.10 以上（PEP 604 型注釈などを使用）
- 主要依存（例）:
  - duckdb
  - openai
  - defusedxml
- 実行環境に応じて追加の依存が必要になる場合があります（本 README はコード内の使用ライブラリに基づく最小限の記載です）。

例: 仮想環境作成と依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# パッケージとして編集可能インストール（setup.py/pyproject があれば）
pip install -e .
```

## 環境変数（主なもの）
config.Settings で参照される主要な環境変数：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 等の SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / ai.score_regime で使用）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)、デフォルトは development
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットするとパッケージ起動時の .env 自動読み込みを無効化

補足:
- パッケージはプロジェクトルートにある `.env` と `.env.local` を自動で読み込みます（OSの環境変数優先）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env のテンプレートは `.env.example` を参照してください（config._require のエラーメッセージでも案内あり）。

## セットアップ手順（簡易）
1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに `.env`（もしくは `.env.local`）を作成し、必要な環境変数を設定
5. DuckDB ファイルのディレクトリを作成（settings.duckdb_path の親ディレクトリが自動生成される関数もありますが、手動で準備しておくと安心）
6. 監査 DB を初期化（任意だが推奨）

監査 DB 初期化例（Python）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# 生成された conn を監査ログ操作に使用できます
```

## 基本的な使い方（コード例）
以下は最小限の利用例です。実運用ではロギングやエラーハンドリングを適切に追加してください。

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env)  # development / paper_trading / live
```

- DuckDB 接続を開いて日次 ETL を実行
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date は省略で今日（内部で営業日補正あり）
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定か api_key 引数を指定
print(f"scored {count} symbols")
```

- 市場レジームを判定して market_regime に書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究モジュール（ファクター計算）利用例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

## 注意点 / 設計上のポイント
- ルックアヘッドバイアス防止:
  - AI モジュール・ETL・研究モジュールは内部で datetime.today() を無暗に参照しないよう設計されています。target_date を明示的に渡すことが推奨されます。
- API リクエスト:
  - J-Quants クライアントはレート制御（120 req/min）やリトライ（指数バックオフ）を組み込んでいます。
  - OpenAI 呼び出しはリトライ・パース例外に対してフェイルセーフ（多くの場合スコア 0.0 にフォールバック）を備えています。
- News Collector:
  - SSRF、防御的 XML パース（defusedxml）、レスポンスサイズ制限などセキュリティ対策を実装しています。
- データ保存:
  - DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）です。部分失敗時でも既存データ保護を意識した書き込みを行います。

## よく使うテーブル（コード内参照）
- raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / market_regime
- audit 系: signal_events, order_requests, executions

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下の主要ファイルとモジュール）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py (score_news エクスポート)
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: pipeline・etl・schema 関連)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（上記以外にも strategy / execution / monitoring などの公開は __all__ に準備されていますが、今回の抜粋では data/research/ai が中心です）

## 開発 / テスト
- 環境変数自動読み込みはプロジェクトルートの `.env` と `.env.local` を対象に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効にできます。
- AI 呼び出し箇所や外部 API 呼び出し箇所はユニットテストでモックしやすいように設計されています（モジュール内の _call_openai_api や _urlopen を patch 可能）。

---

この README はコードベース（提示されたファイル群）から抽出した利用方法／設計方針の簡易ガイドです。実運用・デプロイの前に以下を確認してください:
- .env（機密情報）の管理
- OpenAI／J-Quants の利用料・レート制限
- 実行環境の Python / ライブラリバージョン整合性
- DuckDB ファイルのバックアップ・運用ポリシー

必要であれば、README にさらに詳細なセットアップスクリプト例、CI/CD、運用手順（cron ジョブ、ワーカー構成）、および各テーブルのスキーマ一覧を追加できます。どの情報を追加したいか教えてください。