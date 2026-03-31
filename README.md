# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集と LLM によるニュースセンチメント分析、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（注文→約定トレース）など、実運用を想定した機能を提供します。

---

## 主要な目的・概要

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL。
- RSS によるニュース収集と、OpenAI（gpt-4o-mini）を利用したニュースごとのセンチメント解析（銘柄別 ai_score）。
- マクロセンチメントと ETF（1321）のMA乖離を組み合わせた市場レジーム判定（bull / neutral / bear）。
- 研究用途のファクター計算（モメンタム／バリュー／ボラティリティ）と特徴量解析ユーティリティ。
- データ品質チェック（欠損・スパイク・重複・日付不整合）と監査ログテーブル（シグナル→発注→約定のトレース）。
- kabuステーション API 用設定、Slack 通知など運用に必要な設定周りをサポート。

---

## 機能一覧（抜粋）

- 環境変数・.env 自動ロード（settings）
- J-Quants クライアント（取得・保存・トークン自動リフレッシュ・レート制御）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- Data 品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- ニュース収集（RSS → raw_news、SSRF / Gzip / トラッキング除去 対策）
- ニュース NLP（銘柄別センチメント score_news）
- 市場レジーム判定（score_regime）
- 研究用ユーティリティ（calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / zscore_normalize 等）
- 監査ログ初期化（init_audit_db / init_audit_schema）
- DuckDB 保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10 以上（PEP 604 の union 演算子 `|` を使用）
- DuckDB や OpenAI クライアントを利用します。

1. 仮想環境を作成・有効化（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 依存パッケージをインストール  
   （プロジェクトの requirements.txt / pyproject.toml がある想定ですが、ない場合は主要パッケージを個別にインストール）
   ```
   pip install duckdb openai defusedxml
   ```
   追加の依存がある場合はプロジェクトの manifest を参照してください。

3. 環境変数を設定（.env 推奨）  
   プロジェクトルートの `.env` または `.env.local` を自動で読み込みます（自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。主なキー:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabu API パスワード（注文連携などで使用）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack ボットトークン（通知連携）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: environment (development|paper_trading|live) （デフォルト: development）
   - LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DuckDB の初期テーブルや監査テーブルを作成  
   アプリからスキーマ初期化関数（例えば監査ログ）を呼ぶ例:

   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")  # :memory: も可
   # これで監査用テーブルが作成されます
   ```

---

## 使い方（主要な例）

- DuckDB 接続の準備:

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行（J-Quants トークンは settings から取得される）:

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュースのスコアリング（銘柄別 ai_score を ai_scores テーブルへ書き込む）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須
print(f"書き込み銘柄数: {count}")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースで判定）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須
```

- 研究用ファクター計算・正規化例:

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize

records = calc_momentum(conn, target_date=date(2026, 3, 20))
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

- 監査スキーマ初期化（別 DB を作る）:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

---

## よくある運用上の注意

- Look-ahead バイアス防止:
  - モジュールの設計はバックテストに配慮しており、内部で datetime.today() を参照しない関数が多く、target_date を明示的に渡すことを推奨します。
- OpenAI API:
  - API 呼び出しはリトライ・エラーハンドリングを行いますが、キーの設定（OPENAI_API_KEY）を忘れないでください。
- .env 自動読み込み:
  - プロジェクトルートは .git または pyproject.toml に基づき検出します。自動ロードを無効化したいときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany の挙動:
  - DuckDB の一部バージョンでは executemany に空リストを渡すとエラーになるため、このライブラリは空チェックを行ってから実行します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・.env の自動ロードと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリング（score_news）
    - regime_detector.py — マクロセンチメント + MA で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save 関数、トークン管理、レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py — ETLResult の公開エイリアス
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py — RSS 収集・前処理・安全対策
    - quality.py — データ品質チェック（各種チェックと run_all_checks）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログテーブル定義と初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — モメンタム／ボラティリティ／バリュー等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

---

## ライセンス・貢献

- この README はコードベースの説明用です。実際のライセンス表記・貢献ガイドラインがプロジェクトにある場合はそちらを参照してください。

---

必要であれば、README に以下を追加できます：
- CI / テストの実行方法（pytest 等）
- 詳しい .env.example（テンプレート）
- デプロイ / 運用（systemd / cron ジョブ例）
- Slack / kabu ステーション連携の具体例

どの情報を追記しますか？