# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
J-Quants からのデータ収集（ETL）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（監査テーブル）など、バックテストや実運用に必要なデータ処理・研究・監査機能を提供します。

---

## 主な特徴（機能一覧）

- データ収集・ETL
  - J-Quants API から株価日足・財務データ・市場カレンダーを差分取得
  - DuckDB へ冪等的に保存（ON CONFLICT / upsert）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集 / 前処理
  - RSS からニュースを収集し raw_news テーブルへ保存
  - URL 正規化、SSRF 対策、XML パースの堅牢処理
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM でセンチメント評価（ai_scores に保存）
  - チャンク・リトライ・レスポンス検証ロジック内蔵
- 市場レジーム判定
  - ETF (1321) の 200MA 乖離 + マクロニュースセンチメントを重み合成して（bull/neutral/bear）判定
  - LLM 呼び出しのフェイルセーフ、冪等書き込み
- 研究用ファクター計算
  - Momentum / Volatility / Value / Liquidity 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査（Audit）
  - シグナル → 発注 → 約定までを追跡する監査テーブルの初期化ユーティリティ
  - order_request_id による冪等性、UTC タイムスタンプ管理
- ユーティリティ
  - 環境変数管理（.env 自動ロード）
  - 統計ユーティリティ（Zスコア正規化 等）

---

## セットアップ手順

前提: Python 3.9+ を想定（実行環境の Python バージョンに合わせてください）。

1. リポジトリをクローン（またはパッケージソースを配置）
   - このプロジェクトは src/ 配下にパッケージが配置されています。

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要な依存パッケージをインストール
   - 例（pip）：pip install duckdb openai defusedxml
   - 開発用に requirements.txt / pyproject.toml を用意している場合はそれを使用してください。

4. 環境変数を設定
   - ルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（.env 例）:
     - JQUANTS_REFRESH_TOKEN=あなたの_jquants_リフレッシュトークン（必須）
     - OPENAI_API_KEY=あなたの OpenAI API キー（score_news / score_regime 実行時に必要）
     - KABU_API_PASSWORD=kabu ステーション API パスワード（必要なら）
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  （デフォルト）
     - LINE_CHANNEL_ACCESS_TOKEN=（通知用、任意）
     - LINE_USER_ID=（通知用、任意）
     - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
     - SQLITE_PATH=data/monitoring.db  （デフォルト）
     - PAPER_FILL_MODE=instant|partial|never|reject（paper_trading の挙動、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KILL_FLAG_CLEAR_ON_START=0 または 1
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視）
     - KABUSYS_ENV=development|paper_trading|live（デフォルト: development）
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
   - 注意: Settings は環境変数未設定時に ValueError を投げるプロパティがあります（必須項目に注意）。

5. パッケージのインストール（任意）
   - pip install -e . などで開発インストール可能（pyproject がある場合）。

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトからの呼び出し例です。各関数は duckdb の接続オブジェクト（duckdb.connect(...)）を受け取ります。

- 基本的な import と設定の参照
  - from kabusys.config import settings
  - settings.duckdb_path でデフォルトの DB パスを取得可能

- DuckDB 接続
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=None)  # target_date=None で今日を使う
  - print(result.to_dict())

  run_daily_etl は市場カレンダー、株価、財務の差分取得 → 保存 → 品質チェックまで行い、ETLResult を返します。

- ニュースの AI スコアリング（銘柄ごとの ai_scores 書込み）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数か api_key 引数で指定
  - print(f"書き込んだ銘柄数: {n}")

  補足: OpenAI への呼び出しは gpt-4o-mini を使用。記事が無ければ LLM 呼び出しは行われません。API エラー時はフェイルセーフでスキップして継続します。

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20))

  ETF 1321 の MA200 乖離とマクロニュース LLM スコアを重み合成して market_regime テーブルへ書き込みます。OpenAI API KEY が必要です。

- 監査テーブルの初期化（注文監査用 DB を作る）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - これで監査用テーブル（signal_events, order_requests, executions）とインデックスが作成されます。

- RSS 収集（ニュース）
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  - articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  - 返り値は記事オブジェクト（id, datetime, source, title, content, url）リスト

注意点:
- OpenAI 呼び出しは API エラーやレート制限に備えたリトライを持ちますが、API キー未設定だと ValueError が発生します。
- DuckDB のバージョン差異に依存する実装（executemany の空リスト制約など）があるため、DuckDB のバージョンはソースと合わせて運用してください。

---

## ディレクトリ構成（主なファイルと役割）

（src/kabusys 以下）

- __init__.py
  - パッケージのエントリポイント（version 等）
- config.py
  - 環境変数読み込み・Settings クラス（.env 自動ロード、必須チェック）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（ai_scores 書込み）
  - regime_detector.py — 市場レジーム判定（ma200 + マクロ NLU）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理・営業日判定・夜間更新ジョブ
  - etl.py — ETLResult 再エクスポート
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック群
  - audit.py — 監査テーブル定義・初期化ユーティリティ
  - jquants_client.py — J-Quants API クライアント（取得/保存/認証/レート制御）
  - news_collector.py — RSS 取得 / 前処理 / 保存補助ロジック
- research/
  - __init__.py
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等の研究用ツール

その他:
- packages / modules for strategy, execution, monitoring はパッケージ階層として存在する前提（__all__ に含まれる）が、今回の抜粋コードでは主に data / ai / research が実装されています。

---

## 実運用・運用上の注意

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストや一時的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは API コストとレート制限を伴います。バッチサイズ・リトライ設定は各モジュールの定数で管理されていますが、運用時は API 使用量に注意してください。
- ETL は市場カレンダーの取得 → 株価・財務取得 → 品質チェックの順に実行されます。品質チェックで重大（error）な問題が検出された場合は呼び出し元で処理を判断してください。
- DuckDB を運用 DB として利用する際、データ保守（バックアップ/アーカイブ）方針を定めてください。
- news_collector は外部 URL を取得するため、ネットワークセキュリティ（プロキシ/ファイアウォール）等を考慮してください。SSRF 対策・プライベートアドレスブロックを実装済みです。

---

必要であれば、README に含める実行スクリプト例（systemd サービス定義、cron / airflow 連携サンプル）や .env.example のテンプレート、依存パッケージの正確な一覧（requirements.txt / pyproject.toml から）を追加で作成します。どれを優先して追加しますか？