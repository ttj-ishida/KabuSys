# KabuSys

日本株向けの自動売買・リサーチプラットフォーム（プロトタイプ実装）。  
データ取得（J-Quants）、ETL、ファクター計算、特徴量生成、シグナル生成、バックテスト、ニュース収集などの主要コンポーネントを備えています。

主な設計方針
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみを使用）
- DuckDB を単一の分析 DB として利用（インメモリでのバックテストコピーをサポート）
- API 呼び出しはレート制御・リトライ・トークン自動更新を実装
- ETL / DB 操作は冪等（ON CONFLICT / トランザクション）で安全に保存

---

## 機能一覧
- 環境設定管理
  - .env / .env.local 自動読み込み（パッケージ配置後も cwd に依存しないルート探索）
  - 必須環境変数チェック（settings オブジェクト）
- データ取得・保存（data/）
  - J-Quants API クライアント（rate limiting、リトライ、token refresh）
  - 株価（OHLCV）、財務データ、JPX マーケットカレンダーの取得と DuckDB への保存
  - ニュース（RSS）収集：SSRF 対策、URL 正規化、記事ID生成、記事→銘柄紐付け
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
- リサーチ（research/）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - クロスセクションの Z スコア正規化ユーティリティ
- 戦略（strategy/）
  - 特徴量エンジニアリング（build_features: raw factor の正規化・フィルタ・features テーブルへ UPSERT）
  - シグナル生成（generate_signals: features + ai_scores 統合、BUY/SELL 判定、signals テーブルへ書込）
- バックテスト（backtest/）
  - ポートフォリオシミュレータ（擬似約定、スリッページ/手数料モデル、MTM 記録）
  - バックテストエンジン（本番 DB からインメモリ DB へデータコピーし日次ループでシミュレーション）
  - メトリクス計算（CAGR、Sharpe、MaxDD、勝率、Payoff Ratio）
  - CLI ランナー（python -m kabusys.backtest.run）
- 実行・監視レイヤーのためのスキーマ（signals / orders / trades / positions 等）

---

## 動作環境（推奨）
- Python 3.10+
- 主要外部依存（例）
  - duckdb
  - defusedxml
- その他: 標準ライブラリ（urllib, datetime, logging など）

（実際の package 化・requirements はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate あるいは .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または開発インストール: pip install -e .

4. 環境変数の準備
   - プロジェクトルートに .env（.env.local）を作成します。自動読み込みはデフォルトで有効です。
   - 主要な環境変数（config.Settings が参照するもの）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

   - 自動ロードを抑止する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境に設定

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
     - conn.close()
   - ":memory:" を渡すとインメモリ DB が初期化されます（バックテスト用に便利）。

---

## 使い方（例）

- Backtest CLI
  - 事前に DuckDB に prices_daily, features, ai_scores, market_regime, market_calendar を準備しておく必要があります。
  - 実行例:
    - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
  - オプション:
    - --cash 初期資金
    - --slippage スリッページ率
    - --commission 手数料率
    - --max-position-pct 1銘柄あたり最大ポートフォリオ比率

- DuckDB スキーマ初期化（スクリプト例）
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- ETL（株価差分取得）の呼び出し例（ライブラリ API）
  - from kabusys.data.pipeline import run_prices_etl, ETLResult
  - from kabusys.data.schema import init_schema
  - conn = init_schema('data/kabusys.duckdb')
  - result = run_prices_etl(conn, target_date=date.today())
  - conn.close()
  - run_prices_etl は差分取得・保存・バックフィルを行い (fetched, saved) を返します。

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - conn = init_schema('data/kabusys.duckdb')
  - results = run_news_collection(conn, sources=None, known_codes=set(['7203','6758']), timeout=30)
  - conn.close()

- 特徴量構築 / シグナル生成（ライブラリ API）
  - from kabusys.strategy import build_features, generate_signals
  - conn = init_schema('data/kabusys.duckdb')
  - build_count = build_features(conn, target_date=date(2024,1,1))
  - signal_count = generate_signals(conn, target_date=date(2024,1,1))
  - conn.close()

- プログラムから J-Quants を直接呼ぶ
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - data = fetch_daily_quotes(date_from=..., date_to=...)
  - save_daily_quotes(conn, data)

---

## 重要な設計・セキュリティ注意事項（要約）
- 環境変数: 必須トークン等は .env に格納し、git 管理に含めないこと。
- J-Quants クライアント:
  - リクエストは固定間隔のレートリミットで制御（120req/min）
  - 401 発生時は自動的に refresh トークンで id_token を再取得してリトライ
  - 再試行は指数バックオフで最大回数が設定されています
- ニュース収集:
  - URL 正規化、トラッキングパラメータ除去、ID ハッシュ化
  - SSRF 対策（スキーム検証・プライベート IP 拒否・リダイレクト検査）
  - レスポンスサイズ上限による DoS 対策（最大 10 MB）
- DB 保存は可能な限り冪等（ON CONFLICT）かトランザクションで行う

---

## ディレクトリ構成（主なファイル）
（src/kabusys 以下。省略箇所あり）

- kabusys/
  - __init__.py
  - config.py                        — 環境設定読み込み・settings
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント・保存ロジック
    - news_collector.py               — RSS 収集・保存・銘柄抽出
    - schema.py                       — DuckDB スキーマ定義と init_schema()
    - pipeline.py                     — ETL パイプライン（差分取得等）
    - stats.py                        — zscore_normalize 等ユーティリティ
  - research/
    - __init__.py
    - factor_research.py              — mom/vol/value 等ファクター計算
    - feature_exploration.py          — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py          — build_features（features テーブル作成）
    - signal_generator.py             — generate_signals（signals テーブル作成）
  - backtest/
    - __init__.py
    - engine.py                       — run_backtest（インメモリコピー + 日次ループ）
    - simulator.py                    — PortfolioSimulator（擬似約定）
    - metrics.py                      — バックテスト指標計算
    - run.py                          — CLI entrypoint (python -m kabusys.backtest.run)
    - clock.py
  - execution/                        — 発注/ステータス周り（パッケージ化済み）
  - monitoring/                       — 監視・アラート関連（未編集箇所あり）

---

## 開発・貢献
- コードは型注釈・ロギング・トランザクション制御に配慮して実装されています。ユニットテスト・統合テストは別途整備してください。
- Pull Request 前に linters / tests を実行し、環境変数等の秘匿情報はコミットしないでください。

---

README では主要な使い方と構成をまとめました。具体的な API の利用方法や ETL の詳細（quality チェックルール、backfill 戦略等）は各モジュールの docstring を参照してください。問題や不明点があれば実装ファイルの該当 docstring を確認いただくか、質問してください。