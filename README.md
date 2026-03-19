# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
DuckDB をデータストアに用い、J-Quants からマーケットデータ・財務データを取得して ETL → 特徴量生成 → シグナル生成 → 実行に繋げるための基盤的コンポーネント群を提供します。

主な設計方針：
- 研究（research）と本番（execution）を分離し、ルックアヘッドバイアスを防ぐ設計
- DuckDB を中心とした冪等なデータ保存（ON CONFLICT / upsert）
- API 呼び出しはレート制御・リトライ・トークン自動更新を内包
- 外部依存を最小化（標準ライブラリ寄り）、ただし DuckDB / defusedxml を使用

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）
  - 必須環境変数の取得（明示的エラー提示）
- データ取得（J-Quants）
  - 日足（OHLCV）取得・保存（ページネーション対応、トークン自動更新、リトライ）
  - 財務データ取得・保存
  - 市場カレンダー取得・保存
  - API レート制御（120 req/min）
- DuckDB スキーマ管理
  - raw / processed / feature / execution 層のテーブル定義と初期化
  - インデックス作成
- ETL パイプライン
  - 差分更新（バックフィル対応）
  - 市場カレンダー／株価／財務の一括更新（run_daily_etl）
  - 品質チェックフック（quality モジュールと連携）
- ニュース収集
  - RSS フィード収集、前処理、raw_news 保存、銘柄コード抽出・紐付け
  - SSRF 対策、受信サイズ制限、XML パース保護（defusedxml）
- 研究用ファクター計算
  - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials ベース）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング
  - 生ファクターの結合、ユニバースフィルタ、Z スコア正規化、features テーブルへのアップサート
- シグナル生成
  - features と ai_scores を組み合わせた final_score 計算
  - Bear レジーム抑制、BUY/SELL シグナル生成、signals テーブルへの冪等保存
- 監査（audit）スキーマ（監査ログ／発注トレーサビリティ用テーブル定義）

---

## セットアップ手順

推奨環境
- Python 3.10 以上（PEP 604 の型記法 `X | Y` を利用しているため）
- DuckDB（Python パッケージ）
- defusedxml（RSS パース保護）

1. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb defusedxml
     ```
   - 開発パッケージや追加の依存がある場合はプロジェクトの requirements.txt / pyproject.toml に従ってください。

3. パッケージをインストール（開発モード）
   ```
   pip install -e .
   ```
   （プロジェクトルートに setup.cfg / pyproject.toml がある想定です）

4. 環境変数の設定
   - プロジェクトルートに `.env` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須の環境変数（usage: kabusys.config.settings から参照されます）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID — Slack 送信先チャンネル（必須）
   - オプション（デフォルトあり）
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

   例 .env（抜粋）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（サンプル）

以下は主なユースケース例です。実行前に DuckDB 初期化と環境変数設定を行ってください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # または ":memory:"
  ```

- 日次 ETL 実行（J-Quants から差分取得して保存）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を渡すと任意日で実行可能
  print(result.to_dict())
  ```

- 特徴量の構築（features テーブルに書き込む）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  n = build_features(conn, date.today())
  print(f"features upserted: {n}")
  ```

- シグナル生成（features / ai_scores / positions を参照して signals を作成）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, date.today(), threshold=0.6)
  print(f"signals written: {total}")
  ```

- RSS ニュース収集（既知コードセットを渡して銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は存在する銘柄コードの集合（例: {"7203","6758",...}）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants 生データ取得（自由に使用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

注意点：
- generate_signals / build_features 等は DuckDB 上の所定テーブル（prices_daily, raw_financials, features, ai_scores, positions など）を前提とします。ETL により元データを用意してください。
- jquants_client は内部で RateLimiter・リトライ・トークンリフレッシュを行います。id_token を外部で発行して注入することも可能です（テスト容易性向上）。

---

## ディレクトリ構成

以下は主要ファイルの一覧（省略あり）。プロジェクトルートは src/kabusys 以下にライブラリが配置されます。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得／保存）
    - news_collector.py        — RSS ニュース収集・保存・銘柄抽出
    - schema.py                — DuckDB スキーマ定義・初期化
    - stats.py                 — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - features.py              — data 層の特徴量ヘルパ（再エクスポート）
    - calendar_management.py   — market_calendar 管理・営業日ヘルパ
    - audit.py                 — 監査ログ用スキーマ定義
    - (quality.py は参照されるがここにない場合は別モジュール)
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/volatility/value）
    - feature_exploration.py   — 将来リターン・IC・summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py   — 生ファクターの結合・正規化・features へ保存
    - signal_generator.py      — final_score 計算・BUY/SELL シグナル生成
  - execution/                 — 発注・execution 層（今後の拡張）
  - monitoring/                — 監視・メトリクス関連（今後の拡張）

---

## 実運用に関する注意事項

- 本ライブラリは発注ロジック（実際のブローカー送信）と切り離して設計されています。実際の注文送信を行うコード（execution 層）は別途実装し、監査テーブル等と連携してください。
- 本番（live）で運用する前に paper_trading / backtest で十分に検証してください。KABUSYS_ENV の設定に応じた挙動（ログや抑制など）を取り入れる設計です。
- J-Quants の API レート制御・リトライ・トークン管理は実装されていますが、API 利用規約や利用上限を遵守してください。
- RSS 取得は外部ネットワークに依存します。SSRF 対策・レスポンス上限・XML パース保護など実装していますが、運用時はソースの信頼性・利用条件を確認してください。

---

もし README に追加したい具体的な利用例（cron ジョブ、Docker 化、CI テスト手順、requirements.txt の内容など）があれば教えてください。必要に応じてサンプル .env.example や CLI ラッパー例も作成します。