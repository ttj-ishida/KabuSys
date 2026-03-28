# KabuSys

日本株向け自動売買プラットフォームのライブラリ（KabuSys）。  
市場データの ETL、ニュース収集と LLM ベースのニュースセンチメント、ファクター計算、マーケットカレンダー管理、監査ログ管理などを含むモジュール群を提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（.env）例
- 使い方（簡易例）
- 主要 API の説明
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株自動売買システム向けのデータプラットフォーム / 研究 / AI / 監査ログ機能を提供する Python パッケージです。  
主に以下を目的としています：
- J-Quants API からの株価・財務・カレンダー等の差分取得（ETL）
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント評価（銘柄単位・マクロ）
- ファクター算出、将来リターン・IC 計算などの研究ユーティリティ
- DuckDB を用いたデータ保持と監査ログスキーマ管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、ルックアヘッドバイアス回避や冪等性（DB 書き込みの ON CONFLICT / DELETE→INSERT の方針）、API 呼び出しのリトライ・レート制御等に配慮しています。

---

## 機能一覧
主な機能（モジュール単位）
- kabusys.config: 環境変数管理と自動 .env 読み込み（プロジェクトルート探索）
- kabusys.data:
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline / etl: 日次 ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS 取得・前処理・raw_news 保存
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化 / 監査テーブル（signal_events, order_requests, executions）
  - stats: 汎用統計ユーティリティ（Z スコア正規化）
- kabusys.ai:
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュース（LLM）を合成して市場レジームを判定、market_regime に保存
- kabusys.research:
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等

設計方針の例:
- DuckDB 接続を受け取り SQL と Python を組み合わせて処理（副作用を最小化）
- OpenAI / J-Quants 呼び出しはリトライ・バックオフを実装
- 可能な限り外部状態（現在時刻等）を直接参照しない（ルックアヘッド防止）

---

## 必要条件
- Python 3.10 以上（型注釈に PEP 604 の '|' を使用）
- 推奨ライブラリ（実行に必要な代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）
- 環境変数（下記参照）または .env ファイルの配置

---

## セットアップ手順（ローカル開発向け）
1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクト配布パッケージがあれば）pip install -e .

3. 環境変数設定（.env ファイルをプロジェクトルートに置くと自動読み込みされます）
   - 下記の「環境変数（.env）例」を参照

4. DuckDB 等の準備
   - デフォルトでは data/kabusys.duckdb を使用します（DUCKDB_PATH を変更可）
   - 監査用 DB 初期化例は後述

備考:
- config モジュールはプロジェクトルート（.git または pyproject.toml）を基に .env を自動読み込みします。テストなどで自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（.env）例
必須（本番的に必要なもの）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- OPENAI_API_KEY=...

任意 / デフォルト値あり
- KABUSYS_ENV=development | paper_trading | live  (デフォルト: development)
- LOG_LEVEL=INFO
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

簡易 .env 例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

注意:
- config.Settings は必須環境変数が未設定だと ValueError を投げます。
- .env の書式は一般的な KEY=VAL に対応し、export プレフィックスやクォート、インラインコメント等の扱いにも配慮されています。

---

## 使い方（簡易例）
以下はライブラリの主要な使い方の抜粋例です（実行前に環境変数を設定してください）。

1) DuckDB に接続して日次 ETL を回す
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄単位）の計算
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests や executions の挿入/検索を行う
```

5) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list of dict with mom_1m, mom_3m, mom_6m, ma200_dev ...
```

---

## 主要 API と説明（要点）
- run_daily_etl(conn, target_date, ...): 日次 ETL（カレンダー・株価・財務・品質チェック）
- run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL ジョブ
- jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: J-Quants API 取得
- jquants_client.save_*: DuckDB へ冪等保存（ON CONFLICT）
- news_collector.fetch_rss, preprocess_text: RSS 取得と前処理
- news_nlp.score_news(conn, target_date, api_key=None): 銘柄ごとのニュースAIスコアを ai_scores に書き込む
- regime_detector.score_regime(conn, target_date, api_key=None): 市場レジーム（bull/neutral/bear）を market_regime に書き込む
- data.quality.run_all_checks(conn, ...): データ品質チェックをまとめて実行
- data.audit.init_audit_schema / init_audit_db: 監査ログスキーマの初期化

各関数は docstring に詳細な挙動、例外・フォールバックポリシー、フェイルセーフ（API 失敗時の挙動）を記載しています。特に LLM 呼び出しはリトライやパース失敗時に安全にフォールバックする実装です。

---

## ディレクトリ構成（主要ファイル）
以下はパッケージ内の主要なファイル・モジュール構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py
      - etl.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
      - factor_research.py
      - feature_exploration.py

（上記は本リポジトリに含まれる主要なモジュールの一覧です。実装の詳細や追加モジュールはソースを参照してください。）

---

## 運用上の留意点
- 環境変数管理: Settings は必須値未設定で例外を投げます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して自動 .env 読み込みを無効化できます。
- DB 書き込みは冪等性を重視していますが、ETL を本番で運用する際はバックアップと監視を行ってください。
- OpenAI API 呼び出しにはコストが発生します。バッチサイズや呼び出し頻度は適切に制御してください。
- ネットワーク／API エラーはライブラリ側でリトライ・フォールバックしますが、重大な異常はログと監査で必ず把握するようにしてください。

---

必要であれば README を拡張して、コマンドラインツールの使い方、より詳細な .env.example、CI/CD・デプロイ手順、テストの実行方法等を追加します。どの部分を詳しく追記しましょうか？