# KabuSys

日本株向けのデータ基盤・研究・自動売買ユーティリティ群です。  
ETL（J-Quants）→ データ品質チェック → ニュースセンチメント（OpenAI） → 市場レジーム判定 → 監査ログ（発注トレーサビリティ）といったワークフローをサポートします。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API から株価 / 財務 / 市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- 収集データの品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース記事の収集・前処理と LLM ベースのセンチメントスコアリング（gpt-4o-mini を想定）
- マーケットレジーム（bull / neutral / bear）判定（ETF の MA200 乖離とマクロニュースを合成）
- 研究用ファクター計算・特徴量探索ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマ作成ユーティリティ

設計上のポイント:
- ルックアヘッドバイアスを避けるために datetime.today() の直接参照を最小化
- DuckDB を中心としたローカル永続化（ON CONFLICT による冪等保存）
- OpenAI / J-Quants API 呼び出しに対するリトライ・バックオフ・フェイルセーフを実装
- セキュリティ配慮（RSS の SSRF 対策、XML の defusedxml 利用 等）

---

## 主な機能一覧

- データ取得・保存（J-Quants）
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - ETL 結果を ETLResult オブジェクトで返却
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- ニュース収集・前処理
  - fetch_rss, preprocess_text, URL 正規化・SSRF 対策
- ニュース NLP（OpenAI）
  - score_news: 銘柄ごとの ai_score を ai_scores テーブルへ書込
  - gpt-4o-mini の JSON mode を想定した堅牢な検証・リトライ実装
- マーケットレジーム判定
  - score_regime: ETF（1321）MA200 乖離とマクロニュースセンチメントを合成して market_regime に書込
- 研究用ユーティリティ
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 監査ログ初期化
  - init_audit_schema / init_audit_db: signal_events, order_requests, executions の DDL とインデックスを作成

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の X|Y 構文を使用）
- Git 等でコードを取得済みで、プロジェクトルートに pyproject.toml 等があることを想定

1. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   最低限必要な外部依存:
   - duckdb
   - openai
   - defusedxml

   例:
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があれば、それを使って下さい）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数 / .env の準備
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（詳細は kabusys.config）。
   重要な環境変数例（.env 例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=your_openai_api_key
   - KABU_API_PASSWORD=... (kabu API がある場合)
   - SLACK_BOT_TOKEN=... (通知用)
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   自動ロードを無効化する場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（簡単なコード例）

以下はモジュールの代表的な呼び出し例です。実行前に DuckDB のスキーマ / テーブルが作成されていることを確認してください（別途 schema 初期化処理を用意することを想定）。

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が対象になります
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（OpenAI API キーを環境変数 OPENAI_API_KEY に設定）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} scores")
```

- レジーム判定の実行
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化（専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して監査ログを書き込めます
```

- 研究系ユーティリティ
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)

normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

注意:
- OpenAI 呼び出しは API 使用料が発生します。テストではモックを利用してください（コード内で patch しやすいよう設計されています）。
- J-Quants API の id_token は自動リフレッシュされますが、呼び出し頻度には注意してください（レート制限実装あり）。

---

## 環境変数一覧（主要）

必須（実稼働／多くの機能で必要）:
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
- OPENAI_API_KEY - OpenAI API キー（score_news / regime_detector で使用）
- SLACK_BOT_TOKEN - Slack 通知が必要な場合
- SLACK_CHANNEL_ID - Slack チャンネル ID

任意/デフォルトあり:
- KABU_API_PASSWORD - kabu API のパスワード
- KABU_API_BASE_URL - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH - SQLite（監視用 DB）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV - development / paper_trading / live（デフォルト development）
- LOG_LEVEL - ログレベル（DEBUG/INFO/...）

---

## ディレクトリ構成 (主なファイル・モジュール)

- src/kabusys/
  - __init__.py
  - config.py — 環境変数の読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメントの LLM スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save 系）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult（再エクスポートあり）
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー・営業日判定
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（QualityIssue, run_all_checks）
    - audit.py — 監査ログ（DDL / init_audit_db）
    - news_collector.py — RSS 収集・正規化・前処理
  - research/
    - __init__.py
    - factor_research.py — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
  - ai/ and research/ は研究・分析・戦略検討に有用な関数群を提供

---

## 開発・テストのヒント

- 環境変数自動読み込みは config._find_project_root() にてプロジェクトルートを探索します。テスト時は
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  を設定して自動ロードを無効化し、必要に応じて os.environ を直接パッチしてください。
- OpenAI 呼び出しは内部で _call_openai_api をラップしています。ユニットテストではこの関数を patch して擬似レスポンスを返すと便利です。
- RSS フェッチや HTTP 周りは _urlopen や _SSRFBlockRedirectHandler をモックできます。
- DuckDB を使った関数群は接続オブジェクトを引数で受け取るため、:memory: 接続でのテストが容易です。
  - duckdb.connect(":memory:")

---

必要であれば、README に以下を追加します:
- スキーマ定義（テーブル DDL をまとめたドキュメント）
- 具体的な .env.example ファイル
- CI / テスト実行方法（pytest など）
- デプロイ（paper/live）時の運用注意点（安全な発注フロー、監査ログのバックアップ 等）

他に追記したい情報（例: 使用している外部 API のレート制限運用ポリシーやテーブルスキーマの詳細）があれば教えてください。README をそれに合わせて拡張します。