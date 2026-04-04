# KabuSys

日本株向け自動売買 / データ基盤ライブラリ（KabuSys）。  
ETL、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログなどを備えたモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリです。主な目的は次のとおりです。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集して raw_news に保存、銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（ai_scores）および市場レジーム（market_regime）スコア評価
- ファクター計算（モメンタム・バリュー・ボラティリティなど）と特徴量解析（前方リターン・IC・統計サマリー）
- 監査ログ（シグナル→注文→約定のトレーサビリティ）用テーブル定義と初期化ユーティリティ
- 各種データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴：
- DuckDB を用いた軽量で高速なローカルデータレイヤ
- Look-ahead bias を避ける実装（内部で date.today()/datetime.today() を直接参照しない）
- 冪等性を重視した DB 書き込み（ON CONFLICT / 明確なトランザクション処理）
- 外部 API 呼出し（J-Quants / OpenAI）はリトライ・レート制御を備える

---

## 機能一覧

- 環境設定読み込み（.env 自動ロード、環境変数優先）
- J-Quants クライアント（価格・財務・カレンダー等の取得、DuckDB への保存）
- ETL パイプライン：run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- ニュース収集：RSS 取得、前処理、raw_news への冪等保存（news_collector.fetch_rss 等）
- ニュースNLP：銘柄別ニュースを LLM で評価して ai_scores に書き込み（ai.news_nlp.score_news）
- 市場レジーム判定：ETF 1321 の MA とマクロニュースの LLM 評価を合成（ai.regime_detector.score_regime）
- 研究用ユーティリティ：ファクター計算（momentum/value/volatility）、forward returns、IC、統計サマリー
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ初期化ユーティリティ（init_audit_db / init_audit_schema）
- マーケットカレンダー管理（is_trading_day / next_trading_day / calendar_update_job）

---

## セットアップ手順

前提：
- Python 3.10+（typing | union operator が使われているため）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール  
   （このコードベースに requirements.txt は付属していませんが、主な依存例）
   ```
   pip install duckdb openai defusedxml
   ```
   必要に応じてプロジェクトの setup.py / pyproject.toml に従ってインストールしてください:
   ```
   pip install -e .
   ```

4. 環境変数の設定  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込み無効化）。主に必要な環境変数：

   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY         : OpenAI API キー（ai.* の機能を使う際に必須）
   - KABU_API_PASSWORD      : kabuステーション API のパスワード（使用する場合）
   - KABU_API_BASE_URL      : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知連携に使う（任意）
   - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START : 実行監視関連
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視閾値
   - KABUSYS_ENV            : development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL              : DEBUG | INFO | WARNING | ERROR | CRITICAL

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易例）

以下は Python REPL やスクリプトから各機能を呼び出す例です。

- DuckDB 接続の作成（config の設定を利用）
  ```python
  from kabusys.config import settings
  import duckdb

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（target_date を指定可能）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニューススコアリング（OpenAI が必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None だと OPENAI_API_KEY を参照
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  val = calc_value(conn, date0)
  vol = calc_volatility(conn, date0)
  ```

- マーケットカレンダー周り
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  is_trading = is_trading_day(conn, date(2026,3,20))
  nxt = next_trading_day(conn, date(2026,3,20))
  ```

注意点：
- OpenAI 呼び出しは料金とレート上限が発生します。API キーを安全に管理してください。
- J-Quants API は認証トークン管理・レート制御を実装済みですが、プロダクション利用時は API 利用規約を遵守してください。
- ETL 実行や AI 処理は I/O と API 呼び出しを伴うため適切なログ監視とリトライ設計が必要です。

---

## ディレクトリ構成（主要ファイル）

以下はコードベースの主要モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings（アプリ設定）
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news → ai_scores 書き込み（OpenAI 使用）
    - regime_detector.py
      - ETF 1321 の MA と macro news を合成して market_regime を書き込み
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、取得・保存ユーティリティ
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
      - ETLResult データクラス
    - calendar_management.py
      - マーケットカレンダーの判定・更新ロジック
    - news_collector.py
      - RSS 取得・前処理・保存
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）DDL と初期化
    - etl.py
      - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank

（上記は主要モジュールの抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 注意事項・運用上のポイント

- 環境変数自動ロード
  - プロジェクトルートに .env / .env.local がある場合、OS 環境変数未設定のキーは自動で読み込まれます。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI / J-Quants
  - OPENAI_API_KEY と JQUANTS_REFRESH_TOKEN は外部サービスのキーなので厳重に管理してください。
  - OpenAI 呼び出しはレスポンスの不確実性を考慮し、失敗時は安全側（スコア 0.0 等）にフォールバックする実装になっています。

- Look-ahead bias
  - 多くの関数はバックテスト・研究での look-ahead bias を避けるよう実装されています（target_date 未満のデータのみ参照する等）。

- テスト・モック
  - AI / ネットワーク呼び出し部分はユニットテストで差し替え可能な設計（内部の _call_openai_api などを patch）になっています。

---

## ライセンス・貢献

（このテンプレートにはライセンスファイル記載がありません。実運用では LICENSE を追加してください。）  
貢献・バグ報告・機能提案はリポジトリの Issue / Pull Request を利用してください。

---

README で足りない箇所や、具体的な導入・運用（例：cron ジョブで run_daily_etl を回す、監視用の systemd unit のテンプレ等）について知りたい場合は、どの運用パターンを想定しているか教えてください。具体例を追加して説明します。