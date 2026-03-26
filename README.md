# KabuSys

日本株向けの自動売買 / 研究フレームワーク。  
特徴量生成・シグナル生成・ポートフォリオ構築・バックテスト・データ取得（J-Quants）・ニュース収集など、現物日本株運用のワークフローをモジュール化しています。

主に以下の用途を想定しています。
- ファクター研究（DuckDB をデータレイクとして利用）
- デイリーでの特徴量・シグナル生成（本番またはペーパー）
- 発注ロジックを分離したバックテスト実行
- J-Quants からの市場データ取得と DuckDB への保存
- RSS ベースのニュース収集と銘柄紐付け

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local / OS 環境変数から設定を自動読み込み（無効化可）
  - 必須変数は Settings で検証

- データ取得・ETL
  - J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - 株価日足・財務データ・上場銘柄一覧・カレンダー取得
  - DuckDB へ冪等的に保存するユーティリティ

- ニュース収集
  - RSS フィード取得（SSRF / サイズ制限 / gzip 対応）
  - 記事正規化・ID 化・raw_news への保存
  - 記事から銘柄コード抽出と news_symbols への紐付け

- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算（forward returns）、IC 計算、統計サマリー

- 特徴量・シグナル生成（strategy）
  - 特徴量正規化（Z スコア）・ユニバースフィルタ適用
  - AI スコア等を組み合わせた final_score に基づく BUY / SELL シグナル生成
  - Bear レジームの抑制、SELL のエグジット条件実装

- ポートフォリオ構築（portfolio）
  - 候補選定・等配分 / スコア加重配分
  - リスクベースのサイジング、単元丸め、セクターキャップ適用
  - レジームに応じた投下資金乗数（bull/neutral/bear）

- バックテスト（backtest）
  - インメモリ DuckDB によるデータ切り出し
  - 擬似約定シミュレータ（スリッページ・手数料・部分約定対応）
  - 日次スナップショット保存、トレード履歴記録、メトリクス計算（CAGR/Sharpe/MaxDD/等）
  - CLI エントリポイント（python -m kabusys.backtest.run）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で新しい構文を使用）
- Git, curl 等の基本ツール

1. リポジトリをクローン
   - git clone <リポジトリ_URL>
   - cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - 必須ライブラリ（例）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   ※ 本リポジトリに requirements.txt / pyproject.toml がある場合はそちらを利用してください（本コード一覧では依存宣言が抜けている箇所があります）。

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（execution モジュール利用時）
     - SLACK_BOT_TOKEN — Slack 通知用（monitoring 用）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネルID
   - 任意 / デフォルト値あり:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - LOG_LEVEL — default: INFO

   例 `.env`（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要なワークフロー例）

- バックテスト（CLI）
  - DB（DuckDB）に prices_daily / features / ai_scores / market_regime / market_calendar が準備されている前提。
  - 実行例:
    - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
  - オプションで初期現金、スリッページ、手数料、配分方法等を指定できます（ヘルプ: --help）。

- 特徴量構築（Python API）
  - DuckDB 接続を作成し、日付を指定して特徴量を丸ごと構築します。
  - 例:
    - from kabusys.data.schema import init_schema
    - from kabusys.strategy import build_features
    - conn = init_schema("path/to/kabusys.duckdb")
    - build_features(conn, date(2024, 1, 1))
    - conn.close()

- シグナル生成（Python API）
  - features / ai_scores / positions を参照して signals テーブルへ書き込みます。
  - 例:
    - from kabusys.strategy import generate_signals
    - generate_signals(conn, date(2024, 1, 1), threshold=0.6)

- J-Quants からのデータ取得と保存
  - fetch_* 関数で API から取得し、save_* 関数で DuckDB に保存する流れです。
  - 例:
    - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    - data = fetch_daily_quotes(date_from=..., date_to=...)
    - save_daily_quotes(conn, data)

- ニュース収集ジョブ
  - run_news_collection に DuckDB 接続と既知銘柄コードセットを渡して実行します。
  - 例:
    - from kabusys.data.news_collector import run_news_collection
    - result = run_news_collection(conn, known_codes=set_of_codes)

- ライブラリ API の構成により、研究用の小さなスクリプトから各機能を呼び出して組み合わせることができます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py
  - execution/                # 発注・実行層（空の __init__ が存在）
  - monitoring/               # 監視・通知（将来機能）
  - data/
    - jquants_client.py       # J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py       # RSS 収集・保存・銘柄抽出
    - (schema.py 等: DB スキーマ初期化ユーティリティは参照されるが一覧に含まれない場合あり)
  - research/
    - factor_research.py      # ファクター計算（mom / vol / value）
    - feature_exploration.py  # IC / forward returns / summary
  - strategy/
    - feature_engineering.py  # features テーブル構築
    - signal_generator.py     # final_score 計算と signals 生成
  - portfolio/
    - portfolio_builder.py    # 候補選定・重み計算
    - position_sizing.py      # 株数計算・サイジング
    - risk_adjustment.py      # セクターキャップ・レジーム乗数
  - backtest/
    - engine.py               # run_backtest（主要ループ）
    - simulator.py            # PortfolioSimulator（擬似約定・履歴）
    - metrics.py              # バックテスト評価指標計算
    - run.py                  # CLI エントリポイント
    - clock.py                # 将来用の模擬時計
  - portfolio/ __init__.py     # ポートフォリオ関連の公開 API 集約
  - research/ __init__.py      # 研究関連の公開 API 集約
  - strategy/ __init__.py      # strategy の公開 API 集約
  - backtest/ __init__.py      # backtest の公開 API 集約

> 注意: 上記はコードベースの主要モジュールを抜粋した構成です。実際のリポジトリには schema.py や DB 初期化、追加のユーティリティや CLI、テスト等が含まれることが多いです。

---

## 実運用時の注意事項

- Look-ahead Bias（将来情報の混入）を避ける設計思想が各所に組み込まれています。バックテスト用のデータ準備時には、必ず「その時点で利用可能なデータ」を使ってください。
- J-Quants API のレートリミット・認証ロジックはクライアントに実装されていますが、運用時は API 利用規約を順守してください。
- 本システムはリスク管理の参考実装を含みますが、本番資金での運用は自己責任です。paper_trading 環境で十分に検証してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

## 貢献・拡張

- 新しいファクターを追加する場合は research/factor_research.py に関数を追加し、strategy/feature_engineering.py で統合してください。
- 発注実行層（execution）や監視（monitoring）は抽象化されているため、Exchange / ブローカー固有の実装を追加して pluggable にすることが可能です。
- DuckDB スキーマや ETL パイプラインはデータ品質が重要です。schema.py によるテーブル定義・インデックス設計を確認のうえ拡張してください。

---

必要であれば、具体的な実行例や .env.example のテンプレート、DuckDB スキーマのサンプル、よくあるトラブルシュート（ログの見方・欠損データへの対処方法）などの追記を作成します。どの情報が欲しいか教えてください。