# KabuSys

日本株向けの自動売買・リサーチ基盤ライブラリです。データ収集（J-Quants、RSS）、ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト等のコンポーネントを含みます。設計は「ルックアヘッドバイアス防止」「冪等性」「テストしやすさ」を重視しています。

---

## 主な概要

- パッケージ名: kabusys
- 目的: 日本株アルゴリズム投資の研究・バックテスト・運用支援
- 主な技術要素:
  - DuckDB を用いた時系列・財務データの管理
  - J-Quants API クライアント（リトライ・レートリミット・トークン自動リフレッシュ）
  - RSS ベースのニュース収集（SSRF 対策・トラッキング除去）
  - ファクター計算・特徴量正規化・シグナル生成（戦略ロジック）
  - ポートフォリオ構築（候補選定・配分・リスク調整・サイジング）
  - バックテストエンジン（擬似約定モデル・メトリクス算出）

---

## 機能一覧（ハイライト）

- データ収集
  - J-Quants API クライアント（fetch & save: 日足・財務・上場情報・カレンダー）
  - RSS ニュース収集と記事→銘柄紐付け（SSRF/size対策、重複排除）
- 研究系
  - ファクター計算: momentum / volatility / value
  - ファクター探索: 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Zスコア正規化ユーティリティ
- 戦略（Strategy）
  - 特徴量生成（build_features）: research 結果を正規化して features テーブルに保存
  - シグナル生成（generate_signals）: features と ai_scores を統合して BUY/SELL を生成
- ポートフォリオ構築
  - 候補選定、等配分 / スコア加重、リスクベース配分、セクター上限適用、レジーム乗数
  - 株数決定（単元丸め、aggregate cap、部分約定考慮）
- バックテスト
  - run_backtest: DuckDB データをインメモリにコピーしてバックテストを実行
  - 擬似約定モデル（スリッページ・手数料）、日次スナップショット、トレード履歴
  - 評価指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI エントリポイント: python -m kabusys.backtest.run
- その他
  - ニュース抽出・前処理・DB 保存ユーティリティ
  - 設定・環境変数管理（.env 自動ロード、必須チェック）

---

## 必要条件

- Python 3.10 以上（ソース内に | 型アノテーション等を使用）
- 推奨ライブラリ（最低限）:
  - duckdb
  - defusedxml
- その他、実際に動かす機能に応じて urllib（標準）、logging 等を使用します。

依存関係はプロジェクトの packaging に合わせて requirements.txt や pyproject.toml を用意してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   - 例（最小）:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用にローカルパッケージとしてインストールする場合:
     ```
     pip install -e .
     ```

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
     - KABU_API_PASSWORD — kabuステーション API パスワード（運用時）
     - SLACK_BOT_TOKEN — Slack 通知に使用
     - SLACK_CHANNEL_ID — Slack 通知チャンネル
   - 任意（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 env ロード無効化フラグ（1）
     - KABUSYS_BASE_URL 等（実装で参照される別キーあり）
   - 例 `.env`（最低限のテンプレート）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化
   - 本コードは `kabusys.data.schema.init_schema` を使って DuckDB を初期化します（schema SQL は別途プロジェクトに含まれている想定）。DB を準備してください。
   - 既存の DuckDB ファイルを使う場合は、prices_daily / features / ai_scores / market_regime / market_calendar / stocks 等のテーブルが必要です（バックテスト実行時の前提）。

---

## 使い方（主なユースケース）

1. バックテスト（CLI）
   ```
   python -m kabusys.backtest.run \
     --start 2023-01-01 --end 2023-12-31 \
     --cash 10000000 \
     --db path/to/kabusys.duckdb
   ```
   オプションで slippage, commission, allocation-method, max-positions などを指定可能です。DB は事前に必要データが格納されている必要があります。

2. プログラムからの特徴量構築 / シグナル生成
   - DuckDB 接続を作成して関数を呼び出します（例: duckdb.connect(...)）。
   - 特徴量作成:
     ```python
     from datetime import date
     import duckdb
     from kabusys.strategy.feature_engineering import build_features

     conn = duckdb.connect("path/to/kabusys.duckdb")
     n = build_features(conn, target_date=date(2024, 1, 10))
     print("features upserted:", n)
     ```
   - シグナル生成:
     ```python
     from kabusys.strategy.signal_generator import generate_signals
     total = generate_signals(conn, target_date=date(2024, 1, 10))
     print("signals written:", total)
     ```

3. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   import duckdb

   conn = duckdb.connect("path/to/kabusys.duckdb")
   known_codes = {"7203", "6758", ...}  # stocks テーブルから抽出する想定
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

4. J-Quants データ取得 & 保存
   - J-Quants から日足や財務データを取得して DuckDB に保存するユーティリティが実装されています（例: fetch_daily_quotes / save_daily_quotes）。
   - 実行例（トークンは環境変数経由）:
     ```python
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     import duckdb
     conn = duckdb.connect("path/to/kabusys.duckdb")
     recs = fetch_daily_quotes(date_from=..., date_to=...)
     saved = save_daily_quotes(conn, recs)
     ```

---

## 設計上の注意点 / 運用メモ

- .env 自動ロード:
  - `kabusys.config` はプロジェクトルート（.git または pyproject.toml の位置）を基準に `.env` と `.env.local` を自動で読み込みます。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

- Look-ahead バイアス防止:
  - J-Quants の取得時刻 (fetched_at) を UTC で保存するなど、バックテストの公正性に配慮した実装になっています。
  - バックテストはデータの「既知性」を守るため、必要なデータを過去日付までコピーしてインメモリで実行します。

- トランザクション・冪等性:
  - DB への挿入処理は ON CONFLICT（Upsert）やトランザクションで保護されています（重複挿入を避ける設計）。

- 安全性:
  - RSS フェッチでは SSRF 対策、レスポンスサイズ制限、XML パースのハードニング（defusedxml）を行っています。

---

## ディレクトリ構成（主要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - jquants_client.py
    - news_collector.py
    - ...（schema / calendar_management 等想定）
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - strategy/
    - feature_engineering.py
    - signal_generator.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - backtest/
    - engine.py
    - simulator.py
    - metrics.py
    - run.py (CLI)
    - clock.py
    - __init__.py
  - execution/
    - __init__.py (実行層のスタブ)
  - monitoring/ (監視・アラート関連の実装想定)

---

## 開発者向け情報

- 型付け / Python 要件:
  - ソースは Python 3.10+ を想定しています（PEP 604 の型表記等）。
- ロギング:
  - 各モジュールは標準 logging を使用しています。実行時にログレベルを設定してください。
- テスト:
  - 単体テストは別途プロジェクトの tests/ 等に配置することを推奨します。config の自動 env ロードはテストで影響するため `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用して無効化できます。

---

## 追加情報 / 今後の拡張案（抜粋）

- execution 層: 実際の発注（kabuステーション API）連携の具体実装とエラーハンドリング
- 銘柄ごとの単元情報（lot_size）の外部マスタ化
- 分足シミュレーション対応（SimulatedClock 拡張）
- AI スコア連携のパイプライン整備（学習モデル・推論結果の取り込み）

---

README にある使い方はコードベースから抽出した典型的なワークフローを示しています。実運用時は DuckDB のスキーマ定義（schema.sql）や実データの準備、API キーの管理（安全な場所に保存）を必ず行ってください。必要なら README に入れるサンプル .env.example や schema 初期化手順の追記も作成します。どの情報を追加したいか教えてください。