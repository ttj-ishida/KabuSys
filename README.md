# KabuSys

日本株向けのデータパイプライン・リサーチ・自動売買基盤の一部実装です。  
ETL、ニュース収集・NLP、マーケットレジーム判定、ファクター計算、監査ログなど、アルゴリズムトレーディングに必要な基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を提供します。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたデータ保存（冪等保存／更新）
- ニュース収集（RSS）と LLM を用いたニュースセンチメント評価
- 市場レジーム判定（ETF MA とマクロニュースの複合）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース可能化）

設計上の特徴：
- ルックアヘッドバイアスを避けるため、target_date ベースで処理（date.today() の乱用を避ける）
- DuckDB を中心に SQL と最小限の Python で効率的に処理
- 外部 API 呼び出しに対するリトライ・レート制御・フェイルセーフ設計
- 冪等性を重視した保存ロジック

---

## 主な機能一覧

- data/jquants_client: J-Quants からの差分フェッチ、ページネーション、保存（raw_prices, raw_financials, market_calendar 等）
- data/pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL（run_prices_etl 等）
- data/news_collector: RSS 取得・前処理・raw_news 保存（SSRF/サイズ制限等に配慮）
- data/quality: データ品質チェック（欠損/スパイク/重複/日付不整合）
- data/calendar_management: 市場カレンダーの判定・補間（is_trading_day / next_trading_day 等）
- data/audit: 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
- ai/news_nlp: ニュースを銘柄別に集約して LLM でセンチメントを算出し ai_scores に保存（score_news）
- ai/regime_detector: ETF（1321）200日 MA とマクロニュース LLM を合成して市場レジーム判定（score_regime）
- research: ファクター計算（momentum/value/volatility）、将来リターン、IC / 統計サマリ、正規化ユーティリティ

---

## 動作要件（推奨）

- Python 3.10+
  - 理由: 型注釈（| 演算子）や modern typing を使用しているため
- 主要依存パッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- その他標準ライブラリのみで多くの処理を実装していますが、実行環境に合わせてパッケージを追加してください。

例（pip）:
pip install duckdb openai defusedxml

プロジェクト全体の依存は pyproject.toml / requirements.txt にまとめてください（本リポジトリに未提供の場合は上記を参考にインストール）。

---

## 環境変数

主要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知用チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ('development' / 'paper_trading' / 'live')（デフォルト: development）
- LOG_LEVEL: ログレベル（'DEBUG','INFO','WARNING','ERROR','CRITICAL'）

.env 自動読み込み:
- パッケージ起点のルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env` → `.env.local` の順で自動読み込みされます（OS 環境変数より下位）。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意: 必須変数未設定時は Settings プロパティ（kabusys.config.settings）で ValueError が発生します。

---

## セットアップ手順

1. Python 3.10+ の仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements や pyproject があればそれに従ってください）

3. リポジトリをチェックアウトして開発インストール（任意）
   - git clone <repo>
   - cd <repo>
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、シェル環境で変数をエクスポートしてください。
   - 例 `.env`（簡易）
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...

---

## 使い方（簡単なコード例）

以下は主要ユースケースのサンプルです。DuckDB 接続は duckdb.connect(path) を用います。

- 日次 ETL の実行（run_daily_etl）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を指定しない場合は今日が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア付け（score_news）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されている前提
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み件数: {written}")
```

- 市場レジーム判定（score_regime）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB 初期化:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

- 研究用ファクター計算:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

- データ品質チェックの実行:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- score_news / score_regime は OpenAI API を呼びます。OPENAI_API_KEY を設定してください（引数で上書きも可能）。
- J-Quants API 呼び出しには JQUANTS_REFRESH_TOKEN が必要です。get_id_token / fetch_* 系で使用されます。

---

## 主要モジュールとディレクトリ構成

（抜粋。詳細はソースコードを参照してください）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数設定、Settings クラス、自動 .env 読み込み
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM ベースセンチメント算出（score_news）
    - regime_detector.py  — 市場レジーム判定ロジック（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch / save / token）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult の再エクスポート
    - news_collector.py   — RSS 収集・正規化・保存
    - quality.py          — データ品質チェック
    - calendar_management.py — 市場カレンダー関連ユーティリティ
    - audit.py            — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ等
  - その他: strategy / execution / monitoring 等（パッケージ公開用 __all__）

各モジュールはドキュメント文字列に設計方針・前提・エラーハンドリングを明記しています。実運用時には DB スキーマ（テーブル定義）に合わせて DuckDB を初期化し、必要なテーブルを作成してください（audit.init_audit_schema 等のユーティリティを利用可能です）。

---

## 注意事項 / 運用上のヒント

- OpenAI / J-Quants 呼び出しには API レートとコストが伴います。バッチサイズやリトライ設定、ログ出力を調整してください。
- ETL は冪等性を意識して設計されていますが、バックアップと監査ログは必ず保持してください。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして .env の自動読み込みを抑制できます。
- DuckDB の executemany に空リストを渡すと問題になるバージョン（0.10 系）に配慮した実装になっています。DuckDB バージョンと互換性に注意してください。

---

もし README に追加してほしい具体的な実行例（cron ジョブ例、Dockerfile、pyproject 依存定義など）があれば教えてください。必要に応じて追記します。