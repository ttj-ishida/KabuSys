# KabuSys

KabuSys は日本株向けの自動売買 / 研究プラットフォームです。データ取得、ファクター計算、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集などのモジュールを備え、研究環境と本番運用を想定した設計になっています。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（ターゲット日時点のデータのみを使用）
- DuckDB をデータストアに利用
- 冪等性・トランザクションを意識した DB 操作
- API レート制御・リトライ・トークン自動リフレッシュ対応（J-Quants クライアント）
- 単体関数（純粋関数）で表現可能なロジックと、バックテスト用のメモリシミュレータを分離

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務、上場銘柄、マーケットカレンダー）
  - RSS ベースのニュース収集・正規化（SSRF 対策、トラッキング除去、記事ID のハッシュ化）
  - DuckDB への冪等保存関数（raw / processed テーブル）
- 研究（research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング（strategy.feature_engineering）
  - research のファクターを正規化・合成して `features` テーブルへ保存
  - ユニバースフィルタ（最低株価、最低売買代金）適用
- シグナル生成（strategy.signal_generator）
  - features と AI スコアを統合し final_score を算出
  - BUY / SELL シグナル生成（Bear レジーム抑制、ストップロス等）
  - signals テーブルへの冪等書き込み
- ポートフォリオ構築（portfolio）
  - 候補選定、等金額 / スコア加重配分、リスクベース配分
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - 株数サイジング（単元丸め、aggregate cap、部分約定ロジック）
- バックテスト（backtest）
  - インメモリ DuckDB を用いた再現性のあるバックテスト（run_backtest）
  - ポートフォリオシミュレータ（擬似約定、スリッページ・手数料モデル）
  - 評価指標計算（CAGR、Sharpe、Max Drawdown、勝率、ペイオフ比等）
  - CLI エントリポイントでの実行（python -m kabusys.backtest.run）
- ニュース処理（data.news_collector）
  - RSS 取得、記事正規化、記事 → 銘柄紐付け（抽出ロジック）
  - DB 保存（raw_news / news_symbols）でのチャンク挿入、RETURNING による挿入数取得

---

## セットアップ手順

想定 Python バージョン: 3.10+

1. リポジトリのクローン（またはソースを取得）
   - 例: git clone <repo-url>

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install -U pip
   - 必要ライブラリ（抜粋）:
     - duckdb
     - defusedxml
     - そのほかプロジェクトで使うライブラリを requirements.txt がある場合はそれを使用
   - 例:
     - pip install duckdb defusedxml

   （プロジェクト配布に requirements.txt / pyproject.toml があればそちらを利用してください）

4. 開発時インストール（任意）
   - プロジェクトルートで: pip install -e .

5. 環境変数 / .env ファイル
   - プロジェクトはルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数 > .env.local > .env の優先順位）。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - KABUS_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - .env の書式は一般的な KEY=VALUE をサポートし、export プレフィックスやクォート・コメントを処理します（自動読み込みは kabusys.config に実装）。

6. データベース初期化
   - 本リポジトリに `data.schema`（init_schema）を呼び出す API があるため、DuckDB ファイル作成とスキーマ初期化はその API を使えます（init_schema の存在を確認してください）。
   - 例（REPL などで）:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
     - conn.close()

   （スキーマ定義スクリプトがプロジェクトに含まれているかを確認し、初期テーブルを作成してください）

---

## 使い方

以下は主な利用例です。

1. バックテスト（CLI）
   - DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が準備されていることを前提に実行できます。
   - 例:
     - python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db data/kabusys.duckdb
   - オプション:
     - --cash, --slippage, --commission, --max-position-pct, --allocation-method, --max-utilization, --max-positions, --risk-pct, --stop-loss-pct, --lot-size

2. プログラムからバックテストを実行する
   - from kabusys.data.schema import init_schema
   - from kabusys.backtest.engine import run_backtest
   - conn = init_schema("data/kabusys.duckdb")
   - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000, ...)
   - conn.close()
   - result.history, result.trades, result.metrics を参照

3. 特徴量作成 / シグナル生成（プログラム利用）
   - build_features(conn, target_date)  — features テーブルを構築
   - generate_signals(conn, target_date, threshold=0.6) — signals テーブルを更新
   - これらは DuckDB 接続（kabusys.data.schema.init_schema が返す接続）を受け取ります。

4. J-Quants からデータを取得して保存
   - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   - records = fetch_daily_quotes(date_from=..., date_to=...)
   - save_daily_quotes(conn, records)
   - get_id_token(refresh_token) を使ったトークン取得や自動リフレッシュは組み込み済み

5. ニュース収集ジョブ
   - from kabusys.data.news_collector import run_news_collection
   - run_news_collection(conn, sources=..., known_codes=set_of_codes)

注意点:
- 多くの関数は DuckDB 接続を受け取り DB テーブルを参照/更新します。バックテストでは run_backtest が内部で本番データをコピーしインメモリ接続で実行するため本番テーブルを汚染しません。
- J-Quants API はレート制御（120 req/min）やリトライが組み込まれています。長時間のデータ取得は遅延が発生します。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 配下に配置されています。主要モジュールを抜粋すると:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込み、Settings クラス
  - data/
    - jquants_client.py      — J-Quants API クライアント、保存ユーティリティ
    - news_collector.py      — RSS 収集・前処理・保存
    - (schema.py, calendar_management.py などが想定)
  - research/
    - factor_research.py     — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — IC / forward returns / summary 等
  - strategy/
    - feature_engineering.py — features テーブル作成
    - signal_generator.py    — final_score 計算・signals 書込
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定、リスクベース算出
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py              — run_backtest（メインのバックテストループ）
    - simulator.py           — ポートフォリオシミュレータ（擬似約定）
    - metrics.py             — バックテスト評価指標
    - run.py                 — CLI 用エントリポイント
    - clock.py               — 将来拡張用模擬時計
  - execution/               — 発注 / 実行層（プレースホルダ）
  - monitoring/              — 監視・アラート（プレースホルダ）
  - portfolio/               — ポートフォリオ関連（上記）
  - research/                — 研究関連（上記）

（実際のファイル一覧はリポジトリの内容に依存します。上は現在の主要実装ファイルの抜粋です。）

---

## よくある質問 / 注意点

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テスト等で自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- run_backtest は本番 DuckDB から必要データをインメモリ DB にコピーして実行します（本番テーブルを汚染しない設計）。
- J-Quants クライアントはページネーション対応・トークンリフレッシュ・レート制御を実装しています。API キーやトークンは厳重に管理してください。
- ニュース収集では SSRF 対策、レスポンスサイズ制限、gzip 解凍後のサイズ検査などの安全対策を行っています。

---

## 開発 / 貢献

- バグ報告や機能提案は Issue を立ててください。
- コードの追加・変更は Pull Request を送ってください。テスト、型チェック（可能なら MyPy 等）、および簡単な説明を添えてください。

---

必要であれば README に以下を追加できます：
- 詳細なテーブルスキーマ（data/schema.py の内容）
- 具体的な .env.example（サンプルをそのまま掲載）
- CI / テスト実行方法
- デプロイ手順（paper/live 環境への切替や Slack 通知の設定）

希望があれば追記します。