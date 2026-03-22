KabuSys
=======

KabuSys は日本株向けの自動売買（データ基盤・リサーチ・戦略・バックテスト）用の Python コードベースです。DuckDB によるデータ永続化、J-Quants API からの市場データ収集、特徴量計算・シグナル生成、バックテストフレームワークなどを含むモジュール群で構成されています。

主な特徴
-------
- データ取得
  - J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを取得・保存（rate limiting / リトライ / トークン自動リフレッシュ対応）
  - RSS ベースのニュース収集と銘柄紐付け（SSRF対策・記事IDの正規化）
- データ基盤
  - DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分更新・バックフィル・品質チェックのフック）
- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン・IC（Information Coefficient）計算、ファクター統計サマリ
  - クロスセクション Z スコア正規化ユーティリティ
- 戦略
  - 特徴量エンジニアリング：research 側の生ファクターをマージ・正規化して features テーブルへ保存
  - シグナル生成：features と ai_scores を統合して final_score を計算、BUY/SELL を判定して signals テーブルへ保存
- バックテスト
  - インメモリで DB をコピーして日次ループでシミュレーション（スリッページ・手数料モデル、ポジションサイジング）
  - ポートフォリオシミュレータ、バックテストメトリクス（CAGR、Sharpe、MaxDD、勝率、Payoff 等）
- 設計上の配慮
  - ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）
  - 各保存処理は冪等（ON CONFLICT / DO UPDATE など）を目指す
  - 外部依存を最小化（標準ライブラリ中心で実装）

セットアップ
---------
1. Python のインストール（推奨: 3.9+）
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージ（例）
   - pip install duckdb defusedxml
   - その他ロギングやテスト用パッケージはプロジェクトに合わせて追加してください
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）
4. 環境変数の設定
   - プロジェクトは .env / .env.local を自動読み込みします（ルート判定は .git または pyproject.toml）。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（execution 層用）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知用チャンネル ID
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: monitoring 用 SQLite（デフォルト: data/monitoring.db）
   - 例 .env（プロジェクトルートに配置）
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

初期 DB スキーマ作成
------------------
Python REPL またはスクリプトから DuckDB スキーマを初期化できます。

例:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" を指定するとインメモリ DB
conn.close()

主要な使い方（抜粋）
------------------

1) バックテスト（CLI）
プロジェクトに含まれる CLI:
python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

オプション:
--cash, --slippage, --commission, --max-position-pct など

2) バックテスト（プログラムから）
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest
conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
# result.history / result.trades / result.metrics を参照
conn.close()

3) 特徴量構築・シグナル生成
from kabusys.strategy import build_features, generate_signals
# DuckDB 接続 (conn) と target_date を用意
n = build_features(conn, target_date)  # features テーブルに書き込む
m = generate_signals(conn, target_date)  # signals テーブルに書き込む

4) データ取得・ETL
- J-Quants から日足を取得して保存:
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
saved = save_daily_quotes(conn, records)

- ニュース収集:
from kabusys.data.news_collector import run_news_collection
res = run_news_collection(conn, sources=None, known_codes=known_codes_set)

- ETL パイプライン（差分取得等）は kabusys.data.pipeline に関数群があります（run_prices_etl / run_news_collection 等）。

モジュールとディレクトリ構成
------------------------
主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS 取得・前処理・保存
    - pipeline.py                  — ETL パイプライン（差分更新・品質チェック）
    - schema.py                    — DuckDB スキーマ定義 / init_schema
    - stats.py                     — z-score 正規化等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / ボラ / バリュー計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py       — features テーブル作成（正規化・フィルタ）
    - signal_generator.py          — final_score 計算・BUY/SELL 判定
  - backtest/
    - __init__.py
    - engine.py                    — run_backtest（全体ループ・データコピー）
    - simulator.py                 — PortfolioSimulator（約定・評価）
    - metrics.py                   — バックテスト指標計算
    - run.py                       — CLI エントリポイント
    - clock.py                     — 模擬時計（将来用）
  - execution/                      — 発注・execution 層（プレースホルダ）
  - monitoring/                     — 監視用モジュール（プレースホルダ）

設計上の注意点 / 動作ポリシー
----------------------------
- ルックアヘッドバイアスを避けるため、多くの関数は target_date 時点までのデータのみを参照する設計です。
- DB の INSERT 操作は可能な限り冪等（ON CONFLICT DO UPDATE/DO NOTHING）を目指しています。
- J-Quants クライアントは rate limit（120 req/min）に従う実装です。
- news_collector では SSRF 対策や XML の安全パース、受信サイズ制限などを組み込んでいます。
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点として .env / .env.local をロードします。必要に応じて無効化可能です。

開発・貢献
----------
- コードベースはモジュール毎に責務が分離されています。新しい ETL チェックや戦略を追加する際は既存のテーブルスキーマ・日付扱い（target_date）ポリシーに従ってください。
- 単体テストや統合テストを書く場合、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を使って自動 .env 読み込みを無効化するとテスト環境の安定化に役立ちます。
- DuckDB のインメモリモード（":memory:"）を使うとテストが簡単です。

補足
----
- 本 README はコードベースの主要な機能と使い方を説明しています。実運用での設定（API トークン管理、Slack 通知設定、kabuステーション接続、監視やリカバリ手順）は別途運用ドキュメントを用意してください。
- 依存パッケージや CI 設定、詳細な ETL スケジュール（cron / Airflow 等）はプロジェクト環境に合わせて追加してください。

必要であれば、README にサンプル .env.example や よくあるコマンド（DB 初期化・ETL 実行・バックテスト実行）のシェルスクリプト例を追記します。どの追加情報が欲しいか教えてください。