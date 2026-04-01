# KabuSys

KabuSys は日本株の自動売買 / 研究プラットフォーム向けライブラリです。  
J-Quants からの市場データ取得・ETL、ニュースの収集と LLM による NLP スコアリング、ファクター計算、監査ログ（注文トレース）、市場カレンダー管理などを備え、運用・研究の両フェーズで利用できるモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗時に継続）」で、安全にバッチ運用・研究解析を行えるようになっています。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPXカレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集 / NLP
  - RSS から記事を収集して raw_news に保存（SSRF対策、URL正規化、トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別・マクロニュースのセンチメント評価（JSON Mode）
  - ai_scores, market_regime 等への書き込み（冪等）
- 市場レジーム判定
  - ETF (1321) の 200日MA乖離とマクロニュースセンチメントを組合せて日次で 'bull'/'neutral'/'bear' 判定
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、Zスコア正規化等
- 監査ログ / トレーサビリティ
  - signal_events / order_requests / executions 等の監査用テーブルを DuckDB に作成・初期化
  - 発注の冪等キー（order_request_id）や created_at（UTC）を用いた追跡
- 市場カレンダー管理
  - market_calendar を元に営業日判定・next/prev_trading_day 等を提供
- 設定管理
  - .env / .env.local / OS 環境変数から設定を自動ロード（プロジェクトルートを .git / pyproject.toml で検出）

---

## 必要条件

- Python 3.10+
- DuckDB
- openai（OpenAI Python SDK）
- defusedxml
- その他標準ライブラリ（urllib 等）

（プロジェクト依存パッケージはパッケージング／requirements.txt に合わせて導入してください。例は下記）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージ配布設定があれば
# pip install -e .
```

---

## 環境変数（主な一覧）

KabuSys は環境変数（または .env / .env.local）から設定を読み込みます。自動ロードはデフォルトで有効です。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主なキーと意味:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で未指定時に参照）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視用設定
- KABUSYS_ENV: environment ('development' | 'paper_trading' | 'live')（デフォルト development）
- LOG_LEVEL: 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'（デフォルト INFO）

README とは別に .env.example を用意して必要なキーを示すことを推奨します。

---

## セットアップ手順（例）

1. リポジトリをチェックアウト
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # 開発用に extras / requirements を用意している場合はそれに従う
   # pip install -e .
   ```

4. 環境変数を設定（.env または OS 環境に）
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）が自動検出され、.env が存在すれば自動読み込みされます。
   - .env.local があれば .env を上書きします（OS 環境変数 > .env.local > .env の順で優先）。

5. DuckDB ファイルの用意
   - デフォルトでは `data/kabusys.duckdb` に接続します。存在しない場合は自動で作成されます（init スクリプト実行時など）。

---

## 使い方（主な API と例）

以下は Python コードから直接モジュールを使う例です。実行は仮想環境有効化済みかつ必要な環境変数が設定されている前提です。

- ETL（日次ETL 実行）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境で設定されていれば api_key 引数は不要
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブル等が作成されます
  ```

- RSS 取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意:
- OpenAI 呼び出しは API レート・課金が発生します。テスト時は各モジュール内の _call_openai_api をモックする設計になっています（unittest.mock.patch 等）。
- 多くの関数は API キーを引数で渡せるようにしており、テストや運用で環境変数に依存しない実行が可能です。

---

## よく使うユーティリティ / 公開 API の一覧（抜粋）

- kabusys.config.settings — 環境変数を読み込む設定オブジェクト
- kabusys.data.pipeline.run_daily_etl — 日次 ETL パイプライン
- kabusys.data.jquants_client — J-Quants からの取得/保存関数（fetch_*/save_*）
- kabusys.data.news_collector.fetch_rss — RSS フィード取得・前処理
- kabusys.ai.news_nlp.score_news — 銘柄別ニュースセンチメント生成
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定
- kabusys.research.* — ファクター計算・特徴量探索ユーティリティ
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化

---

## 動作上の注意点

- ルックアヘッドバイアス対策: 多くの処理は内部で date 引数を受け取り、datetime.today() を直接参照しない設計になっています。バックテストや再現性のため、target_date を明示的に与えることを推奨します。
- 冪等性: ETL の保存処理は ON CONFLICT DO UPDATE / INSERT … DO UPDATE など冪等設計になっていますが、外部からの手動操作時は注意してください。
- API 失敗時の挙動: OpenAI / J-Quants コールではリトライ・フォールバックが組まれています。例えば LLM の失敗時はスコアを 0.0 にフォールバックする実装が多く、処理継続を優先します。
- テスト: OpenAI 呼び出しやネットワーク IO 部分は関数をモック可能な実装になっています（例: news_nlp._call_openai_api を patch）。

---

## ディレクトリ構成（主要ファイル）

以下はライブラリの主要モジュール一覧（src/kabusys 配下）。実ファイルの分割により責務が整理されています。

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
    - etl.py (ETL 公開インターフェース)
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - audit (DB 初期化用関数)
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/factor_research.py
  - research/feature_exploration.py
  - others: execution, monitoring, strategy 等のパッケージを __all__ に含める設計（実装はプロジェクト内を参照）

（実際のリポジトリではさらに細かいモジュールやヘルパーが含まれます。上は主要な機能の位置を示した抜粋です。）

---

## 開発・拡張のヒント

- テスト時は環境変数の自動ロードを無効化できます:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しは各モジュールでリトライや JSON 検証を行っているため、モックして安定した単体テストを書くことが容易です。
- DuckDB のスキーマ変更・マイグレーションは、DDL 管理用の init スクリプトにまとめると安全です（audit.init_audit_schema の設計を参照）。

---

この README はライブラリの概要と主要な使い方・設計方針を簡潔にまとめたものです。より詳細な内部仕様（DataPlatform.md / StrategyModel.md 等）や運用手順はプロジェクト内ドキュメントを参照してください。必要であれば、サンプルスクリプトや CI/CD 用の runner 例、requirements.txt / pyproject.toml に基づくインストール手順を追記します。