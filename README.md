# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買/データプラットフォーム向けライブラリ群です。J-Quants からのデータ取得（ETL）、ニュースの収集と LLM を用いた NLP スコアリング、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注・約定のトレーサビリティ）などの機能を提供します。

主な用途例:
- 日次 ETL による株価・財務・カレンダー取得と保存（DuckDB）
- RSS ニュースの収集と銘柄別センチメント生成（OpenAI）
- マクロニュースと ETF MA を組み合わせた市場レジーム判定
- 研究用ファクター計算および統計解析ユーティリティ
- 発注・約定を追跡する監査テーブルの初期化

---

## 主要機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得 + DuckDB 保存: daily quotes / financials / calendar）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS -> raw_news、SSRF 対策・トラッキング除去）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化（signal_events / order_requests / executions テーブル定義）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄記事をまとめて OpenAI に投げ、銘柄別 ai_score を ai_scores に書込む
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュース LLM を合成し market_regime に書込む
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込み・管理（.env/.env.local の自動読み込みを実装）
  - Settings オブジェクト経由で必要な設定を参照

---

## セットアップ手順

前提:
- Python 3.10+（typing の union 型などを使用）
- DuckDB を利用（pip install duckdb）
- OpenAI SDK（pip install openai）
- defusedxml（RSS の安全なパース用）
- ネットワークアクセス（J-Quants / OpenAI へのアクセス）

1. リポジトリをクローン / パッケージを配置
   - pip editable インストール例:
     ```
     git clone <repo>
     cd <repo>
     pip install -e .
     ```
   - または必要なライブラリを手動でインストール:
     ```
     pip install duckdb openai defusedxml
     ```

2. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと、自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須キー（サンプル）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN : Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID : Slack チャンネル ID
     - KABU_API_PASSWORD : kabuステーション（ブローカー） API パスワード
     - OPENAI_API_KEY : OpenAI 呼び出しに必要（score_news / score_regime を利用する場合）
   - 任意/デフォルト:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/...
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 で自動 .env 読み込みを無効化
     - DUCKDB_PATH : data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH : data/monitoring.db（デフォルト）

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. データベースディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（代表的な呼び出し例）

以下は Python スクリプト / REPL からの利用例です。DuckDB 接続を渡して関数を呼び出します。

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数で
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定を実行して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数で
```

- 監査用 DuckDB を初期化（発注/約定用テーブルの作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests 等の操作が可能
```

- 研究モジュールの利用例（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date": ..., "code": ..., "mom_1m": ..., ...}, ...]
```

- 市場カレンダーの判定
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026, 3, 20)))
print(next_trading_day(conn, date(2026, 3, 20)))
```

注意:
- score_news / score_regime は OpenAI API へアクセスするため OPENAI_API_KEY を環境変数か引数で渡す必要があります。
- settings 内の必須環境変数が未設定の場合、Settings プロパティは ValueError を送出します。

---

## 設定と自動 .env 読み込み

- config.Settings を通じて設定値を参照できます:
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.slack_channel_id, settings.duckdb_path, settings.env, settings.log_level など
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を含む）を起点に `.env` と `.env.local` を自動読み込みします。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効化する場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```
- 必須環境変数が未設定の場合、settings が ValueError を投げます。エラーメッセージに従って .env を作成してください。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（score_news）
  - regime_detector.py — マクロセンチメント + ETF MA による市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py — ETL 結果クラスの再公開
  - news_collector.py — RSS 取得・正規化・保存
  - calendar_management.py — 市場カレンダー操作・カレンダー更新ジョブ
  - quality.py — データ品質チェック（QualityIssue, run_all_checks）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログ（signal_events / order_requests / executions）DDL と初期化
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility ファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
- research/*, ai/* などの各モジュールは DuckDB 接続を受け取り副作用は最小化しています。

---

## 開発上の注意・トラブルシューティング

- DuckDB への executemany に空リストが渡せないバージョンの対応が入っています。操作前にパラメータリストが空でないことを確認してください（pipeline / news_nlp 等で対策済み）。
- OpenAI 呼び出しはリトライ・バックオフが実装されていますが、APIキーやレート制限に注意してください。
- J-Quants API はレート制限と ID トークンのリフレッシュロジックがあります。JQUANTS_REFRESH_TOKEN を正しく設定してください。
- ニュース収集では SSRF・XML Bomb・巨大レスポンス対策を実装しています。外部 RSS を登録する際はソースの検証を行ってください。
- production（実口座）運用時は settings.is_live に応じたガード・テストを必ず行ってください。

---

## ライセンス・貢献

この README はコードベースの説明を目的としています。実利用・公開時は適切なライセンス表記と README の更新を行ってください。貢献の際は PR / Issue を通じて変更点を説明してください。

---

必要であれば、README に含める具体的な例スクリプト（ETL バッチ、ニュース集約ジョブ、レジーム判定 cron 設定例 など）を追記します。どのユースケースの例を追加したいか教えてください。