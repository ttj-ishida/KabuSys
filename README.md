# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤ライブラリ（KabuSys）。  
DuckDB をデータストアに利用し、J-Quants / RSS / OpenAI 等と連携してデータ収集・品質チェック・AI スコアリング・研究用ファクター計算・監査ログ管理を行うモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の領域をカバーする Python パッケージです。

- J-Quants API による株価 / 財務 / 市場カレンダーの差分 ETL（ページネーション・レート制御・リトライ対応）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・テキスト前処理）
- OpenAI を用いたニュース NLP（銘柄ごとのセンチメント）およびマクロセンチメントを合成した市場レジーム判定
- Research 用のファクター計算（モメンタム・バリュー・ボラティリティ）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）と初期化ユーティリティ
- 環境変数管理（`.env` の自動読み込み／保護）

設計上の共通方針として「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API失敗で処理中断しない）」などが採用されています。

---

## 主な機能一覧

- data/
  - ETL：run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント：取得・保存（raw_prices, raw_financials, market_calendar 他）
  - カレンダー管理：is_trading_day / next_trading_day / get_trading_days 等
  - ニュース収集：RSS を取得して raw_news に保存（SSRF対策／トラッキング削除）
  - データ品質チェック：check_missing_data / check_spike / check_duplicates / check_date_consistency
  - 監査ログ：init_audit_schema / init_audit_db（監査スキーマの作成）
  - 統計ユーティリティ：zscore_normalize
- ai/
  - news_nlp.score_news：銘柄ごとのニュースセンチメントを ai_scores へ書き込み
  - regime_detector.score_regime：ETF（1321）MA とマクロニュースを合成して市場レジームを market_regime に書き込み
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数管理（.env 自動ロード、settings オブジェクト）

---

## 前提条件 / 依存パッケージ

最低限の依存（実行に必要な主要パッケージ）例：

- Python 3.9+
- duckdb
- openai
- defusedxml

（プロジェクト用途に応じて追加ライブラリや実行環境の整備が必要です。kabu API と Slack 連携などは別途ネイティブ/外部ライブラリや設定を要する場合があります。）

インストール例（venv を推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

必要に応じて他のパッケージを追加してください。

---

## 環境変数 / 設定

config.Settings（`from kabusys.config import settings`）が利用する主要環境変数:

必須（未設定時は ValueError を送出します）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL の認証に使用）
- KABU_API_PASSWORD : kabu ステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN : Slack ボットトークン（通知）
- SLACK_CHANNEL_ID : Slack チャンネル ID（通知）

任意／デフォルトあり
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 環境（development / paper_trading / live。デフォルト development）
- LOG_LEVEL : ログレベル（DEBUG/INFO/...。デフォルト INFO）

AI 関連（OpenAI）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で利用）

その他
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定するとプロジェクトルートの `.env` / `.env.local` の自動ロードを無効化します（テスト時などに利用）。

自動的に `.env` / `.env.local` をプロジェクトルートから読み込みます（OS 環境変数が優先されます）。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索します。

例（.env）:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-name>
   ```

2. 仮想環境作成・依存パッケージのインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   ```

3. 環境変数の準備
   - プロジェクトルートに `.env` を作成するか、環境変数を直接設定してください。
   - 自動読み込みが不要な場合は `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. DuckDB データベースや監査 DB の初期化（必要に応じて）
   - 例: 監査用 DB を初期化
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - プロジェクトで使用する DuckDB は `settings.duckdb_path` を参照して作成・接続できます。

---

## 使い方（主要ユースケース）

以下はライブラリ関数の利用例です。各関数は duckdb 接続（duckdb.DuckDBPyConnection）を前提にしています。

- DuckDB 接続準備例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は Path
  ```

- 日次 ETL（データ収集・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースのAIスコアリング（対象日）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数に設定されている前提
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote scores for {written} codes")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（既存接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn, transactional=True)
  ```

- ファクター算出（研究用途）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))
  volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
  ```

- データ品質チェック実行
  ```python
  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意点:
- OpenAI 呼び出し（news_nlp/regime_detector）は API キーを必要とします（引数で渡すことも可能）。
- DuckDB に対する INSERT/UPDATE はモジュール側で行われるため、適切なスキーマが存在することを前提とします（初期スキーマの作成手順はプロジェクト内の別モジュールや管理スクリプトを参照してください）。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数・設定管理（Settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュースを銘柄ごとに集約し OpenAI でセンチメント算出、ai_scores へ書き込み
  - regime_detector.py — ETF（1321）の MA とマクロニュース（LLM）を合成して market_regime を作成
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
  - etl.py — ETLResult の公開
  - pipeline.py — 日次 ETL の本体（差分取得・保存・品質チェック）
  - stats.py — zscore_normalize など統計ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログ（DDL・初期化）
  - jquants_client.py — J-Quants API クライアント（取得・保存関数）
  - news_collector.py — RSS 収集・前処理・保存（SSRF 対策等）
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

（上記は主要ファイルのみ抜粋。実際のコードベースにはさらに詳細な実装とヘルパーが含まれます。）

---

## 注意事項 / 推奨運用

- 本プロジェクトは市場データ・AI・発注等に関わるため、本番運用時は必ず paper_trading モードや適切なテスト環境で検証してください（KABUSYS_ENV）。
- OpenAI や J-Quants などの外部 API 呼び出しはコストやレート制限があります。設定とレート制御（モジュール実装）を確認してください。
- DuckDB スキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, 監査テーブル等）が必要です。初期スキーマ作成手順は別途ドキュメント/スクリプトを用意してください。
- .env の自動読み込みはプロジェクトルートを基準に行われます。CI / テスト環境で挙動を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

もし README に追記したい具体的な使用例（実際の ETL スケジュール設定、監査ログの運用例、DB スキーマ定義全文など）があれば、用途に合わせてセクションを追加します。必要な部分を教えてください。