# KabuSys

KabuSys は日本株向けの自動売買基盤（研究・データ収集・特徴量生成・シグナル生成・バックテスト）を目的とした Python パッケージです。J-Quants API など外部データソースから市場データ・財務データ・ニュースを収集し、DuckDB に保存して特徴量を計算、戦略シグナルを生成、バックテストを実行するためのモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアスを防ぐ（target_date 時点のデータのみ使用）
- 冪等性・トランザクション志向（DuckDB への保存は ON CONFLICT / トランザクションで整合性確保）
- テスト性を考慮（依存注入や自動ロード無効化オプション等）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env ファイル / OS 環境変数の自動読み込み（無効化可能）
  - 必須環境変数チェック（J-Quants トークン、Slack 等）

- データ収集 / ETL
  - J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事ID生成）
  - ETL パイプライン（差分取得、バックフィル、品質チェックフック）
  - DuckDB スキーマ初期化 / 接続ヘルパー

- 研究（Research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- 特徴量エンジニアリング
  - 生ファクターの正規化（Z スコア）、ユニバースフィルタ（最低株価・売買代金）適用
  - features テーブルへの冪等アップサート

- シグナル生成
  - features + ai_scores 統合による最終スコア（final_score）計算
  - Bear レジーム抑制、BUY/SELL シグナル生成、signals テーブルへの書き込み

- バックテスト
  - インメモリ DuckDB に必要データをコピーして日次シミュレーション（発注はモック）
  - PortfolioSimulator（擬似約定、手数料・スリッページモデル）
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）

- 補助ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - ニュースと銘柄コードの紐付け（テキストから 4 桁銘柄抽出）

---

## セットアップ手順

前提
- Python 3.9+
- DuckDB（Python パッケージとしてインストール）
- ネットワークアクセス（J-Quants API / RSS フィード）

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトで別途要求するパッケージがあれば追加でインストールしてください）

3. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主な必須変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード（発注を行う場合）
     - SLACK_BOT_TOKEN — Slack 通知を行う場合の Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル
   - 任意:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG / INFO / ...（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

4. DuckDB スキーマ初期化
   - Python REPL などで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - これにより必要なテーブルとインデックスが作成されます。

---

## 使い方（主要なワークフロー例）

以下はよく使う操作の例です。各関数はモジュールに docstring やログがあるので詳細はソースを参照してください。

- DuckDB スキーマ初期化
  python:
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- J-Quants から株価を取得して保存（簡易例）
  python:
    from kabusys.data import jquants_client as jq
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    records = jq.fetch_daily_quotes(date_from=..., date_to=...)
    jq.save_daily_quotes(conn, records)

  注: 実運用では差分 ETL（kabusys.data.pipeline）を利用してください。

- ETL（パイプライン）実行（例: 株価差分）
  python:
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_prices_etl
    from datetime import date
    conn = init_schema("data/kabusys.duckdb")
    etl_result = run_prices_etl(conn, target_date=date.today())
    print(etl_result.to_dict())

- 特徴量構築（features テーブルへ保存）
  python:
    from kabusys.data.schema import init_schema
    from kabusys.strategy import build_features
    from datetime import date
    conn = init_schema("data/kabusys.duckdb")
    n = build_features(conn, target_date=date(2024, 1, 5))
    print(f"built features for {n} symbols")

- シグナル生成
  python:
    from kabusys.data.schema import init_schema
    from kabusys.strategy import generate_signals
    from datetime import date
    conn = init_schema("data/kabusys.duckdb")
    cnt = generate_signals(conn, target_date=date(2024, 1, 5))
    print(f"{cnt} signals generated")

- バックテスト（CLI）
  - 事前に DuckDB を用意し、prices_daily / features / ai_scores / market_regime / market_calendar を埋めておく必要があります。
  - 実行例:
    python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --cash 10000000 --db data/kabusys.duckdb
  - これにより指定期間のバックテストが実行され、結果（CAGR, Sharpe 等）が標準出力に出力されます。

- ニュース収集
  python:
    from kabusys.data.schema import init_schema
    from kabusys.data.news_collector import run_news_collection
    conn = init_schema("data/kabusys.duckdb")
    res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
    print(res)

---

## 重要な注意事項・運用メモ

- 環境変数の自動ロードはパッケージインポート時に行われます。テスト時や明示的に制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 呼び出しはレート制限（120 req/min）を守る実装になっています（固定間隔スロットリング）。大量データ取得時は遅延が発生します。
- news_collector は SSRF 対策やレスポンスサイズチェック、XML パースに対する安全対策（defusedxml）を備えています。
- features / signals / positions 等は日付単位で「削除→挿入（置換）」する冪等な実装になっています。
- 本リポジトリには発注（実際のブローカー接続）層は分離設計されています。live 運用時は十分な検証を行い、KABUSYS_ENV を正しく設定してください（is_live/is_paper/is_dev が利用可能）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                           — 環境設定 / .env 読み込み
  - data/
    - __init__.py
    - jquants_client.py                  — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py                  — RSS ニュース収集・保存
    - pipeline.py                        — ETL パイプライン
    - schema.py                          — DuckDB スキーマ定義 / init_schema
    - stats.py                           — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py                 — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py             — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py             — features 構築（正規化・フィルタ）
    - signal_generator.py                — final_score 計算・BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py                          — バックテストのループ / run_backtest
    - simulator.py                       — PortfolioSimulator（擬似約定）
    - metrics.py                         — バックテスト評価指標
    - run.py                             — CLI エントリポイント
    - clock.py                           — 模擬時計（将来拡張用）
  - execution/                            — 発注／実行層（パッケージ化済み、実運用ロジックは別途実装）
  - monitoring/                           — 監視・メトリクス（未詳細実装）

---

## 開発・拡張のポイント

- 新しいファクターや AI スコアを追加する場合は、research/* または data/* で計算して features / ai_scores テーブルへ出力し、signal_generator の重みや欠損補完ロジックに合わせて調整してください。
- 発注 / execution 層は戦略層（signal_generator）と疎結合に設計されています。実ブローカー接続を実装する場合は execution パッケージを実装して監査ログや再送処理を追加してください。
- テストを容易にするため、多くの API 呼び出しでトークン注入や HTTP のモックが可能です（例: jquants_client._request 関数の id_token 引数、news_collector._urlopen の差し替えなど）。

---

必要に応じて README をさらに詳しく（詳細な ETL 手順、DB テーブル定義抜粋、運用チェックリスト、サンプル .env.example）に拡張できます。どの領域を深掘りしたいか教えてください。