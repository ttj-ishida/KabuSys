# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）・ETL・データ品質チェック・ニュースセンチメント（OpenAI）・市場レジーム判定・研究用ファクター計算・監査ログなどを含むモジュール群を提供します。

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価（日足）・財務・上場銘柄情報・市場カレンダーを差分取得・保存
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE 相当）
  - 日次 ETL パイプライン（run_daily_etl）

- データ品質管理
  - 欠損チェック / 重複チェック / 将来日付・非営業日チェック / スパイク検出
  - 品質チェックの結果を QualityIssue オブジェクトで返却

- ニュース収集・NLP（OpenAI）
  - RSS からニュース収集（SSRF 対策・トラッキング除去・前処理）
  - OpenAI（gpt-4o-mini）による銘柄別センチメントスコアリング（score_news）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（score_regime）

- 研究 / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（research モジュール）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- 監査ログ（Traceability）
  - シグナル→発注→約定の監査テーブル定義と初期化（DuckDB）
  - order_request_id を冪等キーとして二重発注防止

- 設定管理
  - .env または環境変数から設定を自動読み込み（プロジェクトルート検出）
  - 必要な環境変数のラッパー（kabusys.config.settings）

---

## 必要条件

- Python 3.10 以上（PEP 604 の型記法 `X | Y` を使用）
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

プロジェクト側の requirements.txt がある場合はそちらを参照してください。最小限の例:

pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt もしくは個別インストール
4. パッケージのインストール（開発モード）
   - pip install -e .

※ 自動で .env を読み込む仕様です（プロジェクトルートは .git または pyproject.toml で検出）。自動ロードを無効にする場合は環境変数を設定します:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 環境変数（主なもの）

以下は本プロジェクトで参照される主な環境変数です（.env を作成して管理できます）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注連携を行う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先のチャンネルID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時）

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する（1 を設定）

例 (.env):
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（代表的な呼び出し例）

以下は Python インタプリタやスクリプトから利用する基本例です。DuckDB 接続は duckdb.connect() で取得して関数に渡します。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None => 環境変数 OPENAI_API_KEY を参照
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（別 DB に監査テーブルを作る例）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブル等が作成されます
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の mom_1m, mom_3m, mom_6m, ma200_dev を含む dict のリスト
```

---

## 主要 API（モジュール概要と用途）

- kabusys.config
  - settings: 環境変数ラッパー（jquants_refresh_token, kabu_api_password, slack_bot_token 等）

- kabusys.data
  - jquants_client.py: J-Quants API クライアント（取得 + DuckDB 保存関数）
  - pipeline.py / etl.py: 日次 ETL パイプラインとジョブ
  - news_collector.py: RSS 取得・前処理・raw_news 保存
  - calendar_management.py: 市場カレンダー管理（営業日判定・更新ジョブ）
  - quality.py: データ品質チェック（check_missing_data, check_spike, ...）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査（signal/order/execution）テーブル定義と初期化ユーティリティ

- kabusys.ai
  - news_nlp.py: OpenAI を使った銘柄別ニュースセンチメント（score_news）
  - regime_detector.py: ETF MA とマクロニュースを組み合わせた市場レジーム判定（score_regime）

- kabusys.research
  - factor_research.py: Momentum / Volatility / Value 計算（calc_momentum, calc_volatility, calc_value）
  - feature_exploration.py: 将来リターン算出 / IC / 統計サマリー 等

---

## ディレクトリ構成（概要）

src/
  kabusys/
    __init__.py
    config.py                # 環境変数・設定管理
    ai/
      __init__.py
      news_nlp.py            # ニュースNLP スコアリング
      regime_detector.py     # 市場レジーム判定
    data/
      __init__.py
      jquants_client.py      # J-Quants API クライアント + 保存ロジック
      pipeline.py            # ETL パイプライン
      etl.py                 # ETL インターフェース（ETLResult など）
      news_collector.py      # RSS ニュース収集
      calendar_management.py # 市場カレンダー管理
      quality.py             # データ品質チェック
      stats.py               # 統計ユーティリティ
      audit.py               # 監査ログ初期化・ヘルパ
      (その他モジュール...)
    research/
      __init__.py
      factor_research.py     # ファクター計算
      feature_exploration.py # 特徴量探索・IC 等
    monitoring/               # （監視系のモジュールが入る想定）
    strategy/                 # （戦略/モデル関連）
    execution/                # （発注/ブローカ連携）

（実際のファイル構成はリポジトリのツリーをご確認ください）

---

## ロギング / 実行モード

- LOG_LEVEL でログレベルを指定（例: INFO, DEBUG）
- KABUSYS_ENV により実行モードを区別（development / paper_trading / live）
  - settings.is_live / is_paper / is_dev が利用可能

---

## テストとモック

- OpenAI 呼び出しや外部 HTTP 呼び出しはモジュール内でラップされており、テスト時は該当関数を patch / monkeypatch してモック可能です（例: kabusys.ai.news_nlp._call_openai_api, kabusys.data.news_collector._urlopen など）。

---

## 注意事項（設計上の留意点）

- 「ルックアヘッドバイアス」回避が設計方針として一貫しており、各モジュールは target_date 引数を受け取るか、DB クエリで date < target_date のように先読みを防ぐ実装になっています。
- OpenAI API 呼び出しは失敗時にフェイルセーフ（0.0 にフォールバック）する箇所があるため、完全成功を保証しません。運用上はログと監視を併用してください。
- DuckDB のバージョン依存や executemany の空パラメータ制約など実装上の考慮があります。運用時は使っている DuckDB のバージョンに注意してください。

---

必要であれば、README にサンプル .env.example、より詳細な CLI/cron の実行例、開発向けのデバッグ手順や既知の制約事項を追加できます。どの部分を詳細化したいか教えてください。