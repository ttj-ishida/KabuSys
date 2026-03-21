# KabuSys

日本株の自動売買プラットフォーム向けライブラリ群（研究・データプラットフォーム・戦略・発注レイヤーの基盤実装）

短い概要:
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）を備えた ETL / 特徴量生成 / シグナル生成 / ニュース収集 / J-Quants クライアント等を提供します。
- 研究環境（research）で作成した生ファクターを正規化・合成して戦略用の特徴量を構築し、戦略ロジックに従って売買シグナルを作成します。
- J-Quants API と連携して株価・財務・マーケットカレンダーを差分取得・保存します。
- 冪等性・トレーサビリティ・SSRF対策・API レート制御など運用上の堅牢性を重視した設計です。

---

## 主な機能一覧

- データ取得（J-Quants クライアント）
  - 日次株価（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応、トークン自動リフレッシュ、リトライ・レート制御）
- ETL パイプライン
  - 差分取得（バックフィル対応）、保存（冪等）、品質チェック（quality モジュール呼び出しに対応）
  - 日次ETL の統合エントリ（run_daily_etl）
- DuckDB スキーマ管理
  - raw / processed / feature / execution 各層のテーブル定義と初期化（init_schema）
- 特徴量計算（research 層）
  - momentum / volatility / value などのファクター計算（calc_momentum, calc_volatility, calc_value）
  - クロスセクションの Z スコア正規化ユーティリティ
- 特徴量エンジニアリング（strategy 層）
  - build_features: 生ファクターを正規化・合成して `features` テーブルに UPSERT
- シグナル生成（strategy 層）
  - generate_signals: features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを `signals` テーブルへ保存
  - Bear レジーム抑制、売買エグジット判定、重み調整対応
- ニュース収集
  - RSS フィード収集、前処理、raw_news 保存、銘柄コード抽出（SSRF・gzip・サイズ上限・XML攻撃対策あり）
- 監査ログ / 発注トレーサビリティ（audit）
  - signal_events / order_requests / executions など監査用テーブル定義（UUID とタイムスタンプでトレース可能）

---

## 要求環境（例）

- Python 3.9+（typing の一部機能を使用）
- 主要依存パッケージ（抜粋）
  - duckdb
  - defusedxml
- 実行環境により追加の依存がある場合があります。パッケージ化されていれば `requirements.txt` / pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリを取得
   - git clone ...（リポジトリ URL）
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存関係をインストール
   - pip install -r requirements.txt
   - またはパッケージ化されている場合: pip install -e .
4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（優先順位: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabu API パスワード（発注連携時）
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID: 通知先チャンネル ID
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: データベースファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
5. データベース初期化
   - デフォルトでは DuckDB ファイルは `data/kabusys.duckdb` を使用します（DUCKDB_PATH で変更可）。
   - 初期化サンプル（Python）:
     ```python
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

---

## 使い方（主要なユースケース）

以下はライブラリ呼び出しの簡単な例です。実運用では例外ハンドリングやログ管理を適宜追加してください。

- 日次 ETL（J-Quants から市場カレンダー・株価・財務を差分取得して保存）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 特徴量の構築（build_features）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  print(f"features upserted: {n}")
  conn.close()
  ```

- シグナル生成（generate_signals）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals saved: {total}")
  conn.close()
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes を渡すとニュース中の銘柄コード抽出を行って news_symbols に紐付けします
  known_codes = {"7203","6758", ...}
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- J-Quants API の直接利用例
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  from datetime import date

  token = get_id_token()
  rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  print(len(rows))
  ```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: 必須。J-Quants のリフレッシュトークン。
- KABU_API_PASSWORD: 必須（発注連携で使用）。
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）。
- SLACK_BOT_TOKEN: 必須。Slack 通知用トークン。
- SLACK_CHANNEL_ID: 必須。Slack 通知先チャンネル ID。
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト data/kabusys.duckdb。
- SQLITE_PATH: 監視用 SQLite ファイルパス。デフォルト data/monitoring.db。
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）。
- LOG_LEVEL: ログレベル。デフォルト INFO。
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットするとパッケージ起動時の .env 自動ロードを無効化。

設定が不足していると Settings プロパティが ValueError を投げます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定の取り扱い（.env 自動読み込みロジック含む）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レートリミット、再試行、トークン自動更新）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義・初期化（init_schema）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py
      - 市場カレンダー更新 / 営業日判定ユーティリティ
    - audit.py
      - 発注・約定の監査ログ定義
    - features.py
      - data.stats の公開インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value ファクター計算
    - feature_exploration.py
      - 将来リターン計算 / IC 計算 / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features（Z スコア正規化・ユニバースフィルタ・UPSERT）
    - signal_generator.py
      - generate_signals（final_score 算出・BUY/SELL 作成・エグジット判定）
  - execution/
    - __init__.py
    - （発注・ブローカー連携の実装を想定）
  - monitoring/
    - （監視・アラート関連を想定）

---

## 運用上の注意 / 設計上のポイント

- 冪等性を重視：API からのデータ保存では ON CONFLICT / UPSERT を使用し、再実行での二重挿入を回避します。
- ルックアヘッドバイアス対策：特徴量・シグナル生成は target_date 時点で利用可能なデータのみを参照するよう設計されています。
- セキュリティ：RSS の取得では SSRF 対策（リダイレクト先チェック・プライベートアドレス拒否）、defusedxml による XML 攻撃対策、受信サイズ制限を実施しています。
- エラー耐性：ETL の各ステップは独立した例外処理を持ち、1 ステップの失敗が他を止めないように設計されています（監査・ログでフォロー）。
- テスト容易性：id_token 等を引数で注入できる設計になっている箇所があり、モック注入で単体テストを行いやすくしています。

---

## 貢献・拡張案（簡単なガイドライン）

- 新しいファクターを追加する場合は `kabusys.research.factor_research` に関数を追加し、`kabusys.strategy.feature_engineering` の正規化対象に反映してください。
- 発注/ブローカー連携ロジックは `kabusys.execution` に実装してください（監査/audit テーブルとの整合性に注意）。
- 品質チェックは `kabusys.data.quality`（現行コードベースに依存）に統合して ETL 後に呼ぶようにしてください。

---

README は以上です。必要であれば、導入用の example スクリプトや requirements.txt、.env.example のテンプレートも作成しますか？