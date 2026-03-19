# KabuSys

KabuSys は日本株の自動売買基盤を目的とした Python ライブラリです。  
DuckDB をデータストアに用い、J-Quants API / RSS ニュース等からデータを収集して特徴量を構築し、戦略シグナルを生成するためのモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみを利用）
- DuckDB による冪等的なデータ保存（ON CONFLICT / upsert）
- API レート制限・リトライ・トークンリフレッシュなどの堅牢な外部接続処理
- 研究（research）と本番（strategy/execution）を分離した構造

---

## 機能一覧

- 環境設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須キーのチェック

- データ取得・保存（data モジュール）
  - J-Quants API クライアント（株価・財務・カレンダー）
    - レート制御、リトライ、トークン自動リフレッシュ対応
  - RSS ニュース収集と正規化（defusedxml を利用した安全なパース）
    - 記事 ID の冪等生成、トラッキングパラメータ除去、SSRF 対策
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
  - マーケットカレンダー管理（営業日判定、next/prev 等）
  - 各種統計ユーティリティ（Z スコア正規化など）
  - 監査ログ（signal -> order -> execution の追跡テーブル群）

- 研究用ユーティリティ（research モジュール）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー

- 戦略実行（strategy モジュール）
  - 特徴量作成（build_features）
    - research で計算した raw ファクターを正規化・フィルタして features テーブルへ UPSERT
  - シグナル生成（generate_signals）
    - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成し signals テーブルへ保存
    - Bear レジーム抑制、エグジット判定（ストップロス等）

- 実行（execution）層のためのスケルトン（発注処理やブローカ連携はここに実装想定）

---

## 要件

- Python 3.10 以上（PEP 604 の型合成（|）を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

（その他は標準ライブラリで実装されていますが、実行用途に応じて追加パッケージが必要になる場合があります）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo-directory>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール
   ```bash
   pip install --upgrade pip
   pip install duckdb defusedxml
   # 開発中にパッケージを編集して使う場合
   pip install -e .
   ```

3. 環境変数（.env）の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（デフォルト有効）。
   - 自動読み込みを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN：J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD：kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN：Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID：通知先 Slack チャンネル ID（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV：development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL：DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH：監視用 SQLite（デフォルト: data/monitoring.db）

---

## 使い方（クイックスタート）

以下は主要なワークフローのサンプルです。各関数は DuckDB 接続を受け取るため、まずスキーマを初期化して接続を取得します。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   ```

2. 日次 ETL を実行（J-Quants から差分取得して保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

3. 研究由来のファクターから features を構築
   ```python
   from kabusys.strategy import build_features
   from datetime import date
   cnt = build_features(conn, target_date=date(2025, 1, 6))
   print("built features:", cnt)
   ```

4. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date
   num_signals = generate_signals(conn, target_date=date(2025, 1, 6))
   print("signals:", num_signals)
   ```

5. RSS ニュース収集（raw_news / news_symbols 保存）
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes: 有効な銘柄コードのセット（抽出に使用）
   results = run_news_collection(conn, known_codes={"7203", "6758"})
   print(results)
   ```

6. J-Quants データ取得（直接呼び出し例）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = save_daily_quotes(conn, records)
   ```

---

## 設定（主な環境変数）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化

環境変数はモジュール kabusys.config.Settings 経由で取得できます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイルと概要）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・検証・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch / save / get_id_token）
    - news_collector.py
      - RSS フィード取得・記事前処理・DB 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義・init_schema/get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - calendar_management.py
      - market_calendar 管理・営業日判定
    - audit.py
      - 監査ログ用テーブル定義（signal / order / execution の追跡）
  - research/
    - __init__.py
    - factor_research.py
      - momentum/volatility/value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - strategy/
    - __init__.py (build_features, generate_signals を公開)
    - feature_engineering.py
      - raw ファクターの正規化・ユニバースフィルタ・features へのアップサート
    - signal_generator.py
      - final_score の計算、BUY/SELL シグナル生成、signals テーブル保存
  - execution/
    - __init__.py
      - 実行（発注）層のスケルトン（ブローカ連携を実装する場所）
  - monitoring/
    - （モジュール群は将来的に追加される想定）

---

## 注意点 / 実運用時のポイント

- J-Quants API のレート制限（120 req/min）に従う設計です。大量取得時は時間を分散してください。
- DuckDB スキーマは init_schema で一括作成します。既存テーブルがある場合も安全にスキップ（冪等）。
- ニュース収集では SSRF 対策やサイズ上限、XML パースの安全化（defusedxml）等に配慮しています。
- generate_signals / build_features は execution（発注）層とは分離されています。実際の発注ロジックは execution 層でブローカ API に繋ぐ必要があります。
- テスト時に .env 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

この README はコードベースの主要機能の概要と使い方を示したものです。詳細な API 引数や戻り値、運用手順（監視・ロギング・リトライ挙動の調整等）は各モジュールのドキュメント（ソースコード内の docstring）を参照してください。ご不明点があれば具体的な用途や実行環境を教えてください。