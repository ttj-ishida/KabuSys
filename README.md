KabuSys
=======

KabuSys は日本株を対象とした自動売買・データ基盤・バックテスト用のPythonライブラリ群です。
DuckDB をデータストアとして用い、J‑Quants や RSS 等からデータを取得して特徴量（features）を作成し、
シグナル生成 → 発注シミュレーション（バックテスト）までをカバーする設計になっています。

本 README はリポジトリ内のコードベース（src/kabusys 配下）に基づく簡易ドキュメントです。

主な特徴
-------
- データ収集
  - J‑Quants API クライアント（株価 / 財務 / カレンダー取得）
  - RSS ベースのニュース収集（SSRF/サイズ制限対策・トラッキング除去）
  - 差分ETL パイプライン（差分取得・backfill 対応・品質チェック連携）
- データ格納
  - DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - 冪等保存（ON CONFLICT による上書きや INSERT RETURNING の利用）
- 研究・特徴量
  - ファクター計算（Momentum / Volatility / Value / Liquidity）
  - クロスセクションの Z スコア正規化ユーティリティ
  - 研究向けの IC / 将来リターン解析・統計要約
- 戦略
  - 特徴量の構築（build_features）
  - 正規化済みファクターと AI スコアを統合してシグナル生成（generate_signals）
  - Bear レジーム抑制、BUY/SELL の日次置換書き込み（冪等）
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル・全量クローズ）
  - 日次ループのバックテストエンジン（run_backtest）
  - メトリクス計算（CAGR / Sharpe / MaxDD / 勝率 / Payoff 等）
- 設定管理
  - .env / 環境変数の自動ロード（プロジェクトルート検出、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須設定は Settings プロパティで検証

セットアップ（ローカル開発用）
-----------------
1. Python（3.9+ 相当）をインストールし、仮想環境を作成・有効化します（推奨）。
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要な依存パッケージをインストールします（最小限）。
   - 必要な主要ライブラリ: duckdb, defusedxml
   - 例:
     pip install duckdb defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

3. 環境変数を設定します。
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env/.env.local を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env の例
----------
以下は config.Settings が参照する代表的な環境変数の例 (.env ファイル)：

    # J-Quants
    JQUANTS_REFRESH_TOKEN=xxxx...

    # kabuステーション API（発注用）
    KABU_API_PASSWORD=your_kabu_password
    KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意

    # Slack (任意: 通知等)
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567

    # DB
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db

    # 動作モード / ログ
    KABUSYS_ENV=development  # development / paper_trading / live
    LOG_LEVEL=INFO

使い方（主要な操作例）
-------------------

1) DuckDB スキーマ初期化
   - Python REPL やスクリプトで実行:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ DB
     conn.close()

   - この関数は必要なテーブル（raw / processed / feature / execution）とインデックスを作成します（冪等）。

2) J‑Quants からデータを取得して保存（ETL の一部）
   - run_prices_etl 等の ETL ヘルパーを使います（例は簡略）:

     from datetime import date
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_prices_etl

     conn = init_schema("data/kabusys.duckdb")
     fetched, saved = run_prices_etl(conn, target_date=date.today())
     conn.close()

   - run_prices_etl は差分取得（backfill）や quality チェックと連携する設計です。id_token を注入してテスト可能。

3) ニュース収集（RSS）
   - run_news_collection を使用して RSS から記事を収集して raw_news に保存／銘柄紐付けを行う:

     from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
     conn = init_schema("data/kabusys.duckdb")
     results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
     conn.close()

   - SSRF対策、サイズ制限、トラッキング除去など安全寄りの実装が施されています。

4) 特徴量構築（features テーブル）
   - 研究モジュールで算出した生ファクターを正規化して features に保存する:

     from datetime import date
     from kabusys.data.schema import init_schema
     from kabusys.strategy import build_features

     conn = init_schema("data/kabusys.duckdb")
     n = build_features(conn, target_date=date(2024, 1, 31))
     print(f"{n} 銘柄の features を作成しました")
     conn.close()

   - 処理はユニバースフィルタ（最低株価・流動性）・Z スコア正規化・±3 clip を行い、日付単位で置換します（冪等）。

5) シグナル生成
   - features と ai_scores を読み final_score を計算して signals に書き込む:

     from kabusys.strategy import generate_signals
     from kabusys.data.schema import init_schema
     from datetime import date

     conn = init_schema("data/kabusys.duckdb")
     cnt = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
     print(f"{cnt} 件のシグナルを signals テーブルに書き込みました")
     conn.close()

   - Bear レジーム判定や SELL（エグジット）判定も含まれます。weights を渡して重みを調整可能です。

6) バックテスト（CLI）
   - 提供されているランナーを使ってバックテストを実行できます（DB は事前にデータを準備してください）:

     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb

   - 代表的なオプション:
     --start / --end: 日付範囲
     --cash: 初期資金
     --slippage / --commission: スリッページ・手数料率
     --max-position-pct: 1銘柄あたりの最大比率
   - run_backtest は本番 DB から必要なテーブルをインメモリ DB にコピーし（signals/positions を汚さない）、日次ループで generate_signals → 約定処理 → マーク・トゥ・マーケット を実行します。

ディレクトリ構成（主要ファイル）
------------------------------
（リポジトリ内 src/kabusys 配下の主要モジュール要約）

- kabusys/
  - __init__.py
  - config.py               : 環境変数・設定管理（.env 自動ロード／必須項目検証）
  - data/
    - __init__.py
    - jquants_client.py     : J‑Quants API クライアント（レート制御・リトライ・保存関数）
    - news_collector.py     : RSS 収集・前処理・raw_news 保存・銘柄抽出
    - schema.py             : DuckDB スキーマ定義と init_schema()
    - stats.py              : zscore_normalize 等の統計ユーティリティ
    - pipeline.py           : ETL パイプライン・差分取得ヘルパー
  - research/
    - __init__.py
    - factor_research.py    : momentum / volatility / value 等のファクター計算
    - feature_exploration.py: 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py: features テーブル構築ロジック
    - signal_generator.py    : final_score 計算・BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py             : run_backtest の実装（本体ループ）
    - simulator.py          : PortfolioSimulator（約定ロジック・履歴）
    - metrics.py            : バックテスト評価指標計算
    - run.py                : CLI エントリポイント
    - clock.py              : 将来拡張用の模擬時計
  - execution/              : 発注周り（パッケージ化用のプレースホルダ）
  - monitoring/             : 監視・通知関連（パッケージ化用のプレースホルダ）

設計上の注意点 / 備考
--------------------
- 冪等性: ETL / 保存関数は可能な限り冪等に設計されています（ON CONFLICT、INSERT ... RETURNING など）。
- Look‑ahead バイアス対策: 特徴量やシグナル計算は target_date 時点までのデータのみを利用する方針です。
- セキュリティ:
  - news_collector は SSRF 対策、受信サイズ制限、defusedxml による XML パースを行います。
  - jquants_client はトークン自動更新（401 対応）とレート制限を実装しています。
- テスト容易性:
  - id_token 等を関数引数で渡せるようにしており、ネットワーク呼び出しの差し替え/モックが容易です。
  - ETL の自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

トラブルシューティング
--------------------
- .env が読み込まれない場合:
  - パッケージは __file__ を起点に親ディレクトリを見てプロジェクトルート（.git または pyproject.toml）を検出します。ルートが見つからない場合は自動ロードをスキップします。
  - 明示的に .env を読み込みたい場合は環境変数を直接 export してください。
- J‑Quants の認証エラー:
  - JQUANTS_REFRESH_TOKEN が正しいかを確認してください。get_id_token でトークンを発行します。jquants_client 内で 401 の場合は自動でリフレッシュを試みます。
- DuckDB 関連:
  - init_schema は指定パスの親ディレクトリを自動作成します。":memory:" を用いるとインメモリDBになります。

貢献 / 開発
-----------
- 新しい ETL 機能やデータソースを追加する際は data/schema.py のスキーマと互換性を考慮してください。
- 戦略やファクターは research/* と strategy/* に分離されています。研究→特徴量→シグナルという流れを守ることで本番レイヤーの安全を担保します。

ライセンス
---------
- このリポジトリのライセンス情報は本 README には含まれていません。実プロジェクトでは LICENSE ファイルを参照してください。

以上が KabuSys コードベース（src/kabusys）の概要と基本的な使い方です。詳細は各モジュールの docstring を参照してください。