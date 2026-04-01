# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータパイプライン、ファクター計算、AI によるニュースセンチメント評価、監査ログなどを含む自動売買システムのライブラリ群です。本 README はコードベースの概要、セットアップ方法、主要な使い方、ディレクトリ構成をまとめたものです。

重要: この README はリポジトリ内の実装（src/kabusys）に基づいた開発者向けドキュメントです。実際の運用（特に実口座での発注）を行う場合は十分な検証とリスク管理を行ってください。

## プロジェクト概要
- 日本株データの ETL（J-Quants 経由）
- Raw データ（prices / financials / news / calendar）管理（DuckDB 想定）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュースの収集と NLP（OpenAI を使ったセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース）
- ファクター計算（モメンタム／ボラティリティ／バリュー等）
- 監査ログ（Signal → Order → Execution をトレースするテーブル群）
- 各モジュールはルックアヘッドバイアス回避を意識して設計済み

## 主な機能一覧
- data.jquants_client: J-Quants API との通信、差分フェッチ、DuckDB への冪等保存
- data.pipeline: 日次 ETL（calendar → prices → financials）と品質チェック
- data.news_collector: RSS 取得／前処理／raw_news への保存（SSRF 対策、サイズ制限）
- ai.news_nlp: 銘柄ごとのニュースをまとめて LLM に投げてセンチメントを ai_scores に保存
- ai.regime_detector: ETF 1321 の MA200 乖離とマクロセンチメントから market_regime を算出
- research: ファクター計算（momentum / volatility / value）と特徴量解析ユーティリティ
- data.audit: 監査用テーブル定義・初期化（signal_events / order_requests / executions）
- data.quality: データ品質チェックの各種ルール
- config: .env / 環境変数の自動読込と Settings API

## 必要条件（推奨）
- Python 3.10+
- 主要 Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで多くの処理を行う設計ですが、OpenAI クライアントや DuckDB はインストールが必要です。

例（最低限のインストール）:
```
pip install duckdb openai defusedxml
```

（実プロジェクトでは requirements.txt / poetry / pyproject.toml を用意してください）

## 環境変数 / .env の例
config.Settings が参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN    # J-Quants リフレッシュトークン
- KABU_API_PASSWORD        # kabuステーション API パスワード（発注機能利用時）
- SLACK_BOT_TOKEN          # Slack 通知用トークン
- SLACK_CHANNEL_ID         # Slack チャンネル ID
- OPENAI_API_KEY           # OpenAI API キー（score_news / regime_detector）

任意（デフォルト値あり）:
- KABU_API_BASE_URL        # kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH              # DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH              # 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH            # 実行監視用 PID ファイルパス
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV              # development / paper_trading / live（デフォルト development）
- LOG_LEVEL                # DEBUG/INFO/…（デフォルト INFO）

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_pw
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

自動ロード:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml のある親）を探索して `.env` / `.env.local` を自動で読み込みます。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。

## セットアップ手順（開発者向け）
1. リポジトリをクローンして作業ディレクトリに移動
2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
4. 必須環境変数を設定（または .env を作成）
5. DuckDB 用ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```
6. （オプション）監査ログ DB を初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

## 使い方（主要 API と実行例）

- 日次 ETL（データ取得 → 保存 → 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  conn.close()
  ```

- ニュースセンチメントのスコア付け（ai_scores に書き込む）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  conn.close()
  ```

- 市場レジーム判定（market_regime に書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  conn.close()
  ```

- ファクター計算・特徴量解析（research モジュール）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  conn.close()
  ```

- 監査ログスキーマの初期化（個別 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 必要に応じて conn を利用して監査ログに書き込み
  conn.close()
  ```

- カレンダー関連ユーティリティ例
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026,3,20)))
  print(next_trading_day(conn, date(2026,3,20)))
  conn.close()
  ```

注意点:
- OpenAI 呼び出しはモデル `gpt-4o-mini` を想定（JSON mode を使用）。API レート／課金に注意してください。
- J-Quants API は認証トークン管理とレートリミッティング（120 req/min）を行います。
- DuckDB の executemany に関する互換性（空リスト不可）に配慮した実装になっています。

## ディレクトリ構成（主なファイル）
以下は src/kabusys 以下の主要モジュール・ファイル一覧（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                          — 環境変数 / Settings 管理
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュースセンチメント評価（LLM 呼び出し）
    - regime_detector.py                — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント + 保存ロジック
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - etl.py                            — ETLResult 再エクスポート
    - news_collector.py                 — RSS ニュース取得・前処理（SSRF 対策）
    - calendar_management.py            — マーケットカレンダー管理と営業日判定
    - stats.py                          — 汎用統計ユーティリティ（zscore_normalize 等）
    - quality.py                        — データ品質チェック
    - audit.py                          — 監査ログ（DDL・初期化）
  - research/
    - __init__.py
    - factor_research.py                — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py             — 将来リターン、IC、統計サマリーなど

（実際のリポジトリには追加ファイルやユーティリティ群が含まれる可能性があります）

## 開発・テストのヒント
- 自動環境変数読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- OpenAI/API 呼び出し部分はユニットテストでモック化しやすいように設計されています（モジュール内の _call_openai_api をパッチする等）。
- DuckDB は簡単にファイル DB を作成できるため、テスト時は `:memory:` や一時ファイルを使うと便利です。
- news_collector は defusedxml を使用して XML 攻撃対策を実施、さらに SSRF 防止ロジックを持っています。

## 注意事項（安全と運用）
- 実口座での発注機能を組み込む場合は、risk control / position sizing / 冗長な監査ロギングなどを必ず導入してください。
- 外部 API キー（OpenAI、J-Quants、Slack 等）は安全に保管し、ログや VCS に含めないでください。
- LLM のレスポンスは必ずバリデーション（JSON パースや値域チェック）を行う実装になっていますが、運用では追加の監査を推奨します。

---

この README はコードの設計意図や主要な使い方をまとめたものです。詳細な API ドキュメントや運用手順、CI 設定、依存関係の固定はプロジェクトに応じて追加してください。必要であれば各モジュールの関数単位の簡易参照（引数・戻り値の一覧）を別途作成します。