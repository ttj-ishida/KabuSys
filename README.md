# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（研究・データ基盤・戦略・バックテスト・実行レイヤ）です。本リポジトリはデータ取得・ETL、ファクター計算、特徴量合成、シグナル生成、バックテストシミュレータ、ニュース収集などを含むモジュール群を提供します。

## プロジェクト概要
- 目的: J-Quants 等から取得した市場データを整備し、ファクター計算 → 特徴量生成 → シグナル生成 → 発注（実運用）を行うための基盤を提供します。  
- 設計方針:
  - ルックアヘッドバイアスを避ける（target_date 時点までの情報のみ利用）
  - DuckDB を主要データストアとして利用（軽量で高速）
  - 冪等性を重視（DB への保存は ON CONFLICT 等で更新）
  - ネットワーク／XML／SSRF 等の安全対策を考慮

## 主な機能一覧
- data/
  - J-Quants API クライアント（レート制限・リトライ・トークン自動更新）
  - RSS ニュース収集（正規化・SSRF 対策・銘柄抽出）
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（差分取得・品質チェック）
  - 統計ユーティリティ（Zスコア正規化）
- research/
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索（将来リターン計算 / IC / 統計サマリ）
- strategy/
  - 特徴量合成（build_features）
  - シグナル生成（generate_signals） — AIスコアやレジーム考慮、BUY/SELL 判定
- backtest/
  - ポートフォリオシミュレータ（約定モデル、スリッページ・手数料）
  - バックテストエンジン（run_backtest）
  - 評価指標計算（CAGR, Sharpe, MaxDD, Win rate 等）
  - CLI ランナー（python -m kabusys.backtest.run）
- execution/ と monitoring/ のための骨組み（今後の実装想定）

## 必要な環境変数
必須（Settings で _require されるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

オプション（デフォルト値あり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値が設定されると無効）
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — モニタリング用 SQLite デフォルト `data/monitoring.db`
- KABU_API_BASE_URL — kabu API ベース URL（デフォルトローカル）

.env を使う場合はプロジェクトルートに `.env` / `.env.local` を配置してください。パーサは bash 風の export やクォートを扱います。自動ロードはプロジェクトルート（.git または pyproject.toml）から行われます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

## セットアップ手順（ローカル）
1. Python をインストール（推奨: 3.10+）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb defusedxml
   - （その他必要な HTTP ライブラリ等がある場合は適宜追加）
   - 本リポジトリに requirements.txt があればそれを使用してください。
4. 環境変数を設定（推奨は .env/.env.local）
   - JQUANTS_REFRESH_TOKEN=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - KABU_API_PASSWORD=...
5. データベース初期化
   - Python コンソール、またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - またはメモリ DB:
     init_schema(":memory:")

## 使い方（主要ワークフローの例）

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- J-Quants からデータ取得・保存（例）
  - from kabusys.data import jquants_client as jq
  - records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  - jq.save_daily_quotes(conn, records)

- ETL（差分取得・品質チェック） — pipeline モジュール
  - from kabusys.data.pipeline import run_prices_etl
  - result = run_prices_etl(conn, target_date=date.today())
  - result は ETLResult（取得件数・保存件数・品質問題等を含む）

- 特徴量構築（daily）
  - from kabusys.strategy import build_features
  - count = build_features(conn, target_date=some_date)

- シグナル生成
  - from kabusys.strategy import generate_signals
  - total = generate_signals(conn, target_date=some_date)

- バックテスト（Python API）
  - from kabusys.backtest.engine import run_backtest
  - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  - result.history / result.trades / result.metrics を参照

- バックテスト（CLI）
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
  - res = run_news_collection(conn, sources=None, known_codes=set_of_codes)

## API キー関数（代表）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.jquants_client.get_id_token(...)
- kabusys.data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(...)
- kabusys.data.pipeline.run_prices_etl(...)
- kabusys.data.news_collector.fetch_rss(...) / save_raw_news(...)
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights)
- kabusys.backtest.run_backtest(...)

## ログ・デバッグ
- ロギングは標準ライブラリ logging を利用。簡単に設定可能:
  - import logging; logging.basicConfig(level=logging.INFO)
- 環境変数 `LOG_LEVEL` でデフォルトログレベル変更が可能

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数管理・自動 .env 読み込み
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得/保存関数）
    - news_collector.py — RSS 取得・前処理・DB保存
    - schema.py — DuckDB スキーマ定義・init_schema
    - pipeline.py — ETL パイプライン（run_prices_etl など）
    - stats.py — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（ファクター正規化・フィルタ）
    - signal_generator.py — generate_signals（final_score 計算・BUY/SELL）
  - backtest/
    - __init__.py
    - engine.py — run_backtest（バックテスト全体フロー）
    - simulator.py — PortfolioSimulator / 約定ロジック
    - metrics.py — バックテスト評価指標計算
    - clock.py — SimulatedClock（将来拡張用）
    - run.py — CLI エントリポイント
  - execution/ — 発注関連（現状はパッケージ用意）
  - monitoring/ — 監視関連（将来実装想定）

## 注意事項 / 実運用上のポイント
- 必須環境変数が未設定だと起動時に ValueError が発生します（settings 参照）。
- J-Quants API のレート制限・リトライ動作は jquants_client に実装済みですが、実行頻度は運用ポリシーに従ってください。
- ETL の差分取得は DB の最終取得日を参照します。初回ロード時は期間指定（date_from）を指定してください。
- DuckDB のバージョンや外部ライブラリの互換性に注意してください（特に ON CONFLICT / RETURNING の挙動）。
- news_collector は XML パースや外部 URL の扱いに対して防御的実装（defusedxml、SSRF チェック、レスポンスサイズ制限）がありますが、運用ではフィードの信頼性を確認してください。

## 貢献 / 開発
- 既存の仕様ドキュメント（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）に従って機能拡張してください。
- テストや CI はプロジェクト方針に従い追加してください。データアクセスは DuckDB を使うため、unit テスト時は ":memory:" の DB を利用すると簡便です。
- 自動 .env ロードが邪魔なテストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

上記はリポジトリ内の主要モジュールの要点と典型的な操作例です。より詳しい仕様や設計はコード内の docstring（各モジュール先頭の説明）および別途配布されている設計文書（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）を参照してください。必要であれば README に記載する実行例や追加のセットアップ手順（依存パッケージ一覧）を追記します。どの部分を詳しく書き足しましょうか？