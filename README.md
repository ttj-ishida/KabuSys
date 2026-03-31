# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得・品質チェック）、ニュース収集・NLP、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）などをモジュール化して提供します。

## 概要

KabuSys は日本株のデータ収集・前処理・研究・運用に必要な主要コンポーネントを揃えたライブラリです。  
主に以下を目的としています。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- RSS によるニュース収集と LLM（OpenAI）を用いた記事／銘柄ごとのセンチメント算出
- マーケットレジーム判定（ETF + マクロニュースの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と探索用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- DuckDB をメインのデータ格納として想定

## 機能一覧

- data
  - jquants_client: J-Quants API 取得 / 保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）エントリポイント
  - news_collector: RSS 収集、前処理、raw_news 保存（SSRF 対策、サイズ制限など）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 営業日判定、next/prev trading day、カレンダー更新ジョブ
  - audit: 監査ログ（テーブル作成・初期化 helper）
  - stats: 汎用統計（Z スコア正規化）
- ai
  - news_nlp: ニュースを銘柄ごとにまとめ、OpenAI でセンチメントを取得して ai_scores に保存
  - regime_detector: ETF（1321）200日移動平均乖離とマクロニュース（LLM）を合成して市場レジーム判定
- research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー等
- config: 環境変数管理（.env 自動読み込み機構、必須チェック）
- audit / execution / strategy / monitoring 等の公開 API（パッケージ __all__）

設計上の注記:
- ルックアヘッドバイアス防止のため、内部関数は date.today()/datetime.today() 等を直接参照せず呼び出し側から target_date を受け取る設計です。
- OpenAI 呼び出しにはリトライ・フォールバックロジックを組み込んでいます。API 失敗時は安全側のデフォルト（0.0等）で継続します。

## 要件

- Python 3.10 以上（PEP 604 の型記法（|）等を使用）
- 必要なパッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib 等を多用しているため外部 HTTP クライアントは必須ではありません。

推奨インストール例:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

（実プロジェクトでは requirements.txt を用意して pip install -r で管理してください）

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix
   .venv\Scripts\activate.bat  # Windows
   ```
3. 依存ライブラリをインストール
   ```bash
   pip install -r requirements.txt
   # または必要なパッケージを個別に
   pip install duckdb openai defusedxml
   ```
4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（config.Settings でチェックされるもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（注文系を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack 通知を使う場合
   - 任意 / デフォルトあり:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - OpenAI API キーはモジュール関数に直接渡すか環境変数 OPENAI_API_KEY を設定してください（OpenAI キーは config.Settings では管理していません）。  

5. データベース準備（必要に応じて）
   - DuckDB を使う場合、接続を作成してスキーマ初期化や監査テーブルの初期化を行います（例を下記参照）。

## 環境変数（.env.example）

以下は最小構成の例です（プロジェクトルートに `.env` として保存）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabu API（発注を行う場合）
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

# OpenAI は通常 OPENAI_API_KEY 環境変数で指定するか、関数引数で渡す
# OPENAI_API_KEY=sk-...
```

自動ロードについて:
- config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` を自動で読み込みます。
- テスト等で自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## 使い方（サンプル）

以下はいくつかの代表的な利用例です。実際は適切なエラーハンドリングやロギングを追加してください。

- DuckDB に接続して日次 ETL を実行する（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントをスコアして ai_scores に保存する（OpenAI API キー必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数で設定するか、api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written: {written}")
```

- 市場レジームを算出して market_regime に保存する（OpenAI API キー必要）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB を初期化する（監査専用の DuckDB ファイルを作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

- 研究用ファクター計算、IC 計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

# conn, target_date を用意してから呼び出す
```

注意:
- score_news / score_regime など OpenAI を使う処理は API キーが必要です。関数に api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL・保存処理は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, ai_scores, market_regime 等）が前提です。運用前にスキーマ作成（DDL）を用意してください。

## ディレクトリ構成（抜粋）

パッケージは src/kabusys 以下に配置されています。主要ファイルは次の通りです。

- src/kabusys/
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
    - quality.py
    - calendar_management.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
  - その他: strategy, execution, monitoring などのサブパッケージ（package __all__ に含まれる）

（実際のリポジトリにはさらにサポート系モジュールやテストがある場合があります。上は主要機能にフォーカスした抜粋です。）

## 開発・テストのヒント

- 自動環境読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。CI 環境やテストで外部環境変数に影響されるのが嫌な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部は内部で _call_openai_api を抽象化しているため、unittest.mock.patch によってモックしやすく設計されています（テストで外部 API を呼ばないようにできます）。
- DuckDB に対する executemany の挙動やバージョン差異に注意してください（コード内に互換性対策のコメントあり）。
- ニュース収集では defusedxml を利用し XML 攻撃を防いでいます。RSS フィードの取り扱いは SSRF 対策を施しているため、テスト時に HTTP レスポンスをモックすることを推奨します。

## ライセンス

（ここにプロジェクトのライセンスを明記してください）

---

以上が README のサンプルです。必要があれば、利用シナリオ別の具体的なコード例（運用フロー、Slack 通知、kabu ステーション発注フロー等）や DB スキーマ（DDL）全文、requirements.txt の推奨内容、CI 用の設定例を追加します。どの項目を詳しく載せたいか教えてください。