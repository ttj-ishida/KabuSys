# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ファクター計算、特徴量エンジニアリング、シグナル生成、バックテスト、ニュース収集など、戦略開発と運用に必要な主要コンポーネントを含みます。

---

## 主要な特徴（機能一覧）

- データ収集 & 保存
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - raw データの DuckDB への冪等保存（ON CONFLICT 対応）
- ETL パイプライン
  - 差分更新、バックフィル、品質チェック（品質チェックは quality モジュールと連携）
- ニュース収集
  - RSS からのニュース取得、URL 正規化、記事ID生成、DB 保存、銘柄コード抽出（SSRF対策、gzip / サイズ制限、XML脆弱性対策）
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Spearman）計算、ファクターの統計要約
  - Zスコア正規化ユーティリティ
- 特徴量エンジニアリング（Feature Engineering）
  - 生ファクターの統合・正規化・ユニバースフィルタ適用・features テーブルへの保存（冪等）
- シグナル生成（Strategy）
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成（Bear フィルタ、ストップロス等）
- バックテストフレームワーク
  - インメモリ DuckDB を用いた日次シミュレーション
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）、トレード履歴管理、評価指標（CAGR / Sharpe / MaxDD / WinRate / Payoff）
  - CLI エントリポイントで簡単にバックテスト実行
- 実行（execution）・監視（monitoring）レイヤーの骨子（発注／監視機能は拡張可能）

---

## 環境変数（主な必須項目）

以下の環境変数は Settings クラスから参照されます（未設定時はエラーになるものがあります）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 環境 (`development`, `paper_trading`, `live`)（デフォルト `development`）
- LOG_LEVEL — ログレベル（`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）（デフォルト `INFO`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite（監視用）ファイルパス（デフォルト `data/monitoring.db`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する（`1` などを設定）

パッケージはプロジェクトルートにある `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

前提:
- Python 3.10+（型アノテーションで Union 型の | を使用しています）
- Git（プロジェクトルート識別用）

手順の例:

1. リポジトリをチェックアウトし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （パッケージをローカルに editable インストールする場合）
     - pip install -e .

   依存: DuckDB（duckdb Python パッケージ）、defusedxml（RSS/XML の安全処理）。その他標準ライブラリを使用。

3. 環境変数を設定
   - プロジェクトルートに .env ファイルを作成（例: `.env`）
   - 必須変数（JQUANTS_REFRESH_TOKEN 等）を設定する

4. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで以下を実行:
     - from kabusys.data.schema import init_schema
     - init_schema("data/kabusys.duckdb")
   - もしくは: python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---

## 使い方（主要ユースケース）

以下は代表的な操作例です。

- データベース初期化（再掲）
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- J-Quants からデータ取得（ETL の一部）
  - 例: 株価差分 ETL を実行する（ライブラリ経由で呼ぶ）
    - from datetime import date
      from kabusys.data.pipeline import run_prices_etl
      from kabusys.data.schema import init_schema
      conn = init_schema('data/kabusys.duckdb')
      fetched, saved = run_prices_etl(conn=conn, target_date=date.today())
      conn.close()

  - ニュース収集（RSS）
    - from kabusys.data.news_collector import run_news_collection
      from kabusys.data.schema import init_schema
      conn = init_schema('data/kabusys.duckdb')
      results = run_news_collection(conn, known_codes={'7203','6758'})  # known_codes は任意
      conn.close()

- 特徴量構築
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - from kabusys.strategy import build_features
  - conn = init_schema('data/kabusys.duckdb')
    count = build_features(conn, target_date=date(2024,1,31))

- シグナル生成
  - from kabusys.strategy import generate_signals
  - conn = init_schema('data/kabusys.duckdb')
    n_signals = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)

- バックテスト（CLI）
  - 事前に DB を用意（prices_daily, features, ai_scores, market_regime, market_calendar が必要）
  - 実行例:
    - python -m kabusys.backtest.run \
        --start 2023-01-01 --end 2024-12-31 \
        --cash 10000000 --db data/kabusys.duckdb

  - 戻り値は標準出力にメトリクスを出力します（CAGR / Sharpe / MaxDD 等）。

- バックテスト（プログラム呼び出し）
  - from kabusys.backtest.engine import run_backtest
    result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
    # result.history, result.trades, result.metrics を利用

---

## 開発者向けヒント

- Settings（kabusys.config.Settings）は環境変数に厳密に依存します。CI/テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動 .env ロードを無効化し、テスト用に明示的に環境変数を注入してください。
- J-Quants クライアントは内部でレート制御・リトライ・401 自動リフレッシュを行います。テストでは get_id_token や HTTP 層をモックしてください。
- news_collector は SSRF・XML 攻撃・gzipped 大容量応答に対する防御ロジックを含みます。外部ネットワーク呼び出しはユニットテストでモック推奨です。
- DuckDB のスキーマ初期化は idempotent（同じ DDL を何度実行しても安全）です。

---

## ディレクトリ構成（概要）

以下はパッケージ内の主要ファイル・モジュールとその役割の概略です。

- src/kabusys/
  - __init__.py — パッケージ公開 API（data, strategy, execution, monitoring 等）
  - config.py — 環境変数 / 設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得＋DuckDB保存）
    - news_collector.py — RSS ニュース収集・正規化・保存
    - schema.py — DuckDB スキーマ定義・初期化（init_schema）
    - stats.py — Zスコア正規化などの統計ユーティリティ
    - pipeline.py — ETL パイプライン（差分取得、バックフィル、品質チェックの呼び出し）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — forward returns, IC, factor summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクターを統合して features テーブルへ保存
    - signal_generator.py — features & ai_scores からシグナル生成
  - backtest/
    - __init__.py
    - engine.py — バックテスト全体制御（run_backtest）
    - simulator.py — PortfolioSimulator（擬似約定・履歴管理）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py — 将来拡張用の模擬時計（SimulatedClock）
  - execution/
    - __init__.py — 発注 / execution 層の拡張ポイント（現状骨子）
  - monitoring/
    - （監視・アラート用モジュールを配置する想定）

---

## 参考 & 注意点

- 多くの処理は「ルックアヘッドバイアス」を避ける設計を優先しています（target_date 時点のデータのみ参照、fetched_at の記録など）。
- DuckDB を用いた設計により、ローカルファイルで大量の分析データを高速に扱えます。
- 本パッケージは実運用の注文送信を直接行うモジュール（execution 層）は限定的です。実際の取引接続・秘密鍵管理・送金管理は別途実装・安全管理が必要です。
- ライセンスや貢献ルールが別途ある場合はリポジトリのトップにある LICENSE / CONTRIBUTING を参照してください（本 README には含まれません）。

---

必要に応じて README の補足（例: .env.example、CI のセットアップ、詳細な API 使用例）を追加できます。追加したいセクションがあれば教えてください。