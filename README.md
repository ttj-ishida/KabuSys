# KabuSys

日本株向けのデータプラットフォーム＋リサーチ／AI支援／監査・ETL機能を備えたライブラリ群です。  
主に J-Quants / kabuステーション 等のデータソースと連携し、日次ETL、ニュースセンチメント、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）を提供します。

---

## 主要な特徴（機能一覧）

- 環境変数管理
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を手掛かり）から自動読込（無効化可）
  - 必須設定は Settings 経由で取得（未設定時はエラー）

- データ取得・ETL
  - J-Quants API クライアント（差分取得、ページネーション、リトライ、IDトークン自動更新）
  - ETL パイプライン（市場カレンダー、株価日足、財務データ）をまとめて実行する `run_daily_etl`
  - ETL 結果を表す `ETLResult` データクラス

- ニュース収集 & NLP
  - RSS フィードからのニュース収集（SSRF対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント `score_news`
  - マクロニュース＋ETF MA乖離を用いた市場レジーム判定 `score_regime`

- リサーチ / ファクター処理
  - Momentum / Value / Volatility 等のファクター計算（DuckDB SQL と Python 組合せ）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ、Zスコア正規化

- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付不整合の検出と QualityIssue の返却

- 監査（Audit）テーブル
  - signal_events / order_requests / executions といった監査用スキーマの初期化・管理
  - 監査DB初期化ユーティリティ `init_audit_db`

---

## セットアップ手順

前提
- Python 3.9+（typing の型表記・match等を使わない場合は 3.8 でも動く箇所あり）
- 推奨: 仮想環境（venv, pipenv, poetry 等）

1. リポジトリをクローン（あるいはソースを配置）
2. 仮想環境作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール（最低限）
   - pip install duckdb openai defusedxml

   ※ 実運用では logging 等の整備や追加ライブラリ（slack クライアント等）を導入してください。  
   ※ package 化されている場合は pip install -e . で開発インストール可能です。

4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動読み込みされます（ただしテスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...
   - 任意 / デフォルト
     - KABUSYS_ENV=development|paper_trading|live  (default: development)
     - LOG_LEVEL=INFO
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動ロードを抑制可能

例: .env.example（プロジェクトに同梱されている想定）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単なコード例）

以下は基本的な利用パターン例です。DuckDB 接続を作成し、ETL / NLP / レジーム判定等を呼び出します。

- DuckDB 接続の作成例
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores テーブルへ書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
# OPENAI_API_KEY は環境変数に設定されていることを前提
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {written}")
```

- 市場レジーム判定を実行して market_regime テーブルへ書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（例: モメンタム）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list of dict with keys date, code, mom_1m, mom_3m, mom_6m, ma200_dev
```

- 監査DB 初期化
```python
from kabusys.data.audit import init_audit_db
db_conn = init_audit_db("data/audit.duckdb")
# テーブルとインデックスが作成され、UTC timezone がセットされます
```

- 設定値の取得
```python
from kabusys.config import settings
print(settings.duckdb_path)         # Path オブジェクト
print(settings.is_live)            # True/False
print(settings.jquants_refresh_token)  # 必須: 未設定だと ValueError
```

注意点:
- 各モジュールは look-ahead bias を避ける設計になっており、内部で datetime.today() を直接参照しない関数が多くあります。テストやバッチ実行の際は target_date を明示的に渡してください。
- OpenAI 呼び出しは API 例外に対してフォールバックやリトライを実装していますが、APIキーの設定・料金・レートは各自で管理してください。

---

## 自動 .env 読み込みの挙動

- 起点: このパッケージの config モジュールは __file__ を基点に上位ディレクトリを順に探索してプロジェクトルートを特定します。プロジェクトルートは .git または pyproject.toml の存在で判定します。
- 読込順序: OS 環境変数 > .env.local > .env
- 上書きポリシー:
  - .env は既存 OS 環境変数を上書きしない（override=False）。
  - .env.local は上書きする（override=True）が、最初に取得した OS 環境変数は保護されます。
- 自動読込を無効にする:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップします（テスト用途に便利）。

---

## ディレクトリ構成（主要ファイルと概要）

（パッケージルート: src/kabusys）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / Settings 管理、.env 自動読み込みロジック
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py
      - ニュースを銘柄ごとにまとめ、OpenAI に送って ai_scores に書き込む
    - regime_detector.py
      - ETF(1321) の MA200 乖離とマクロセンチメントを合成して market_regime を更新
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch / save / 認証 / レート制御 / リトライ）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
      - ETLResult 定義
    - calendar_management.py
      - market_calendar を使った営業日判定・更新ジョブ
    - news_collector.py
      - RSS 収集、前処理、raw_news への保存補助
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ用テーブル定義と初期化ユーティリティ
    - etl.py
      - ETL インターフェース（ETLResult の再エクスポート）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum, Value, Volatility, Liquidity などのファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリ、ランク関数

---

## 運用上の注意

- データベース
  - デフォルトの DuckDB ファイルパスは settings.duckdb_path（デフォルト data/kabusys.duckdb）。バックアップやファイルロックに注意してください。
  - audit 用 DB は init_audit_db で初期化可能（":memory:" も可）。

- OpenAI
  - API レート、料金、モデルの互換性に注意。レスポンス検証は行っていますが、生データは必ず確認してください。

- J-Quants API
  - レート制限（例: 120 req/min）を守るために内部で RateLimiter を用いています。大量取得時は適切な間隔にしてください。

- テスト
  - OpenAI / ネットワーク呼び出しはモックしやすいように設計されています（内部の _call_openai_api 等を patch 可能）。
  - 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できます。

---

## さらに詳しく

各モジュールの docstring に設計方針や処理フローが詳しく記載されています。実装や拡張を行う際はモジュール内コメントを参照してください。

---

不明点や README に追記してほしい内容（例: サンプル .env.example ファイル、CI / デプロイ手順、追加の依存関係ファイル等）があれば教えてください。