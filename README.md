# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。ETL、ニュースセンチメント（LLM 経由）、ファクター計算、監査ログ、JPX カレンダー管理など、自動売買システムを構築するためのユーティリティ群を提供します。

この README はリポジトリ内のコード構成（src/kabusys 以下）を基に日本語でまとめた利用手引きです。

---

## 目次

- プロジェクト概要
- 主な機能一覧
- 動作条件 / 必要要件
- 環境変数（.env）
- セットアップ手順
- 使い方（主要 API / 実行例）
- ディレクトリ構成（抜粋）
- 設計上の注意点 / 補足

---

## プロジェクト概要

KabuSys は日本株の自動売買や研究・データ基盤に必要な共通機能をまとめたライブラリです。主に以下をカバーします。

- J-Quants API を使った株価・財務・マーケットカレンダーの ETL（DuckDB 保存）
- RSS を用いたニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価（銘柄別 / マクロ）
- 市場レジーム判定（ETF とマクロセンチメントの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution の追跡テーブル）初期化ユーティリティ

設計上、バックテスト時のルックアヘッドバイアス回避や、API 呼び出しのフェイルセーフ・リトライ・レート制御、DuckDB への冪等保存などに配慮されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証、ページネーション、保存関数）
  - pipeline: 日次 ETL パイプライン（run_daily_etl, run_prices_etl 等）
  - news_collector: RSS 収集・前処理
  - news_nlp: ニュースを LLM で銘柄別にスコアリング（score_news）
  - regime_detector: ETF（1321）MA200 とマクロニュースを合成して市場レジーム判定（score_regime）
  - calendar_management: JPX カレンダー管理・営業日判定
  - quality: データ品質チェック（欠損/スパイク/重複/日付不整合）
  - audit: 監査ログテーブルの初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- ai/
  - news_nlp.score_news
  - regime_detector.score_regime
- config: 環境変数の自動読み込み（.env / .env.local）と settings オブジェクト

---

## 動作条件 / 必要要件

- Python 3.10 以上（typing の `X | None` などを使用）
- 主な依存ライブラリ（プロジェクトの requirements.txt を参照してください、代表例）:
  - duckdb
  - openai (OpenAI Python SDK v1 系)
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）
- 任意で kabuステーションへの接続情報（発注機能を組み合わせる場合）

（環境によって追加パッケージが必要となる場合があります）

---

## 環境変数（.env）

config.Settings が参照する主な環境変数例:

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
  - OPENAI_API_KEY (必須 for LLM 機能) — OpenAI API キー（score_news / score_regime）
  - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携時）
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- データベース / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PID_FILE_PATH / KILL_FLAG_PATH 等（監視用）

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml がある場所）を自動検出し、.env → .env.local の順で読み込みます。既存の OS 環境変数を上書きしない仕様です。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml があれば `pip install -e .` や `pip install -r requirements.txt` を使用）

4. .env を作成（.env.example があれば参照）
   ```
   cp .env.example .env
   # またはエディタで環境変数を設定
   ```

5. DuckDB ファイル保管ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（代表的 API と実行例）

以下はライブラリをインポートして直接呼び出す例です。実運用では呼び出しをラッパーにまとめて cron / scheduler で実行します。

注意: 各関数は DuckDB 接続（duckdb.connect() の戻り値）を受け取ります。

- DuckDB 接続の作成
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行 (run_daily_etl)
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=None)  # target_date=None は今日
  print(result.to_dict())
  ```

- ニュースの LLM スコア（銘柄別）を作成 (score_news)
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY が必要
  print(f"書込み銘柄数: {written}")
  ```

- 市場レジーム判定 (score_regime)
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY が必要
  ```

- 監査DB 初期化（監査テーブルを新規 DB に作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit を使って監査ログを操作
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

- JPX カレンダー関連
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

---

## ディレクトリ構成（主要ファイル抜粋）

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py                   # score_news（銘柄別ニュースセンチメント）
    - regime_detector.py            # score_regime（市場レジーム判定）
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント + 保存関数
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - news_collector.py             # RSS 収集と前処理
    - calendar_management.py        # 市場カレンダー管理、営業日判定
    - quality.py                    # データ品質チェック
    - stats.py                      # zscore_normalize 等
    - audit.py                      # 監査ログスキーマ初期化
    - etl.py                        # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py            # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py        # calc_forward_returns / calc_ic / factor_summary / rank
  - execution/ (発注/実行関連: ここには発注ラッパー等が入る想定)
  - monitoring/ (監視・プロセス管理用モジュール等)

---

## 設計上の注意点 / 補足

- ルックアヘッドバイアス防止:
  - news_nlp と regime_detector は内部で datetime.today() を直接参照しない設計です。target_date を明示的に与えて実行することでバックテストでのバイアスを防ぎます。
  - prices_daily 等のクエリは date < target_date（排他）や lead/lag の利用で未来情報を参照しないよう配慮されています。

- 冪等性:
  - J-Quants からの保存関数は ON CONFLICT DO UPDATE を利用し冪等性を確保しています。
  - audit の order_request_id や executions の broker_execution_id は冪等キーとして扱う設計です。

- フェイルセーフ / リトライ:
  - OpenAI や J-Quants API 呼び出しはリトライ・バックオフを実装しています。LLM の失敗時はゼロスコアやスキップで継続する設計です（致命的例外は上位へ伝播）。

- セキュリティ:
  - news_collector は SSRF 対策、XML の安全パース（defusedxml）、受信サイズ制限、トラッキングパラメータ除去を実装しています。

---

## よくある運用フロー（例）

1. 毎朝（あるいは深夜） run_daily_etl を実行して株価・財務・カレンダーを更新
2. ETL 完了後に品質チェックを実行して問題を検知
3. ニュース収集（RSS） → score_news を実行して ai_scores を更新
4. regime_detector.score_regime を実行して market_regime を更新
5. Strategy レイヤでファクターデータ・ai_scores・market_regime を参照してシグナル生成
6. 監査ログ（signal_events, order_requests, executions） を使ってトレーサビリティを保持

---

問題や追加のドキュメント化を希望する箇所があれば教えてください。例えば: インストール用の requirements.txt の推定内容、より具体的な .env.example、cron / systemd での運用例、テスト戦略（ユニットテストの差し替えポイント）などを追加できます。