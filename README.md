# KabuSys

日本株向けの自動売買システムのライブラリ/基盤コード群です。データ収集（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、監査・スキーマ管理などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐため、常に target_date 時点までの情報のみを使用
- DuckDB を中心としたローカル DB でデータ永続化（冪等性を重視）
- 外部 API への呼び出しは retry / rate-limit / token-refresh を考慮
- research 層と production 層を分離し、研究用関数は本番の発注層に依存しない

---

## 機能一覧

- データ収集
  - J-Quants API クライアント（株価日足 / 財務 / マーケットカレンダー取得、トークン自動リフレッシュ、ページネーション対応、レート制御）
  - RSS からのニュース収集（SSRF対策、トラッキングパラメータ除去、前処理、銘柄抽出）
- データ格納・スキーマ
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution / audit 層）
  - 冪等保存（ON CONFLICT を利用）
- ETL パイプライン
  - 差分更新（最終取得日に基づく差分取得、バックフィル対応）
  - 品質チェック（quality モジュール経由、ETLResult にて集約）
- 研究 / ファクター計算
  - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 特徴量生成 / 戦略
  - Zスコア正規化、ユニバースフィルタ（価格・流動性）
  - features テーブルへの日付単位 UPSERT（冪等）
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ保存
- 監査・実行ログ
  - signal_events / order_requests / executions 等、発注から約定までのトレーサビリティ用テーブル定義
- ユーティリティ
  - 統計ユーティリティ（zscore_normalize 等）
  - カレンダー補助（営業日判定、前後営業日取得、カレンダー更新ジョブ）

---

## 要件

- Python 3.10+
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml

（外部 HTTP 呼び出しは標準ライブラリ urllib を使用しています）

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を用意

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要なパッケージをインストール

   最低限は duckdb と defusedxml をインストールしてください（プロジェクトに requirements.txt があればそちらを利用）。

   ```bash
   pip install -U pip
   pip install duckdb defusedxml
   # 開発インストール
   pip install -e .
   ```

3. 環境変数を設定

   プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動で読み込まれます（自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーションAPI のパスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID : 通知先 Slack チャンネル ID（必須）

   オプション（デフォルトあり）
   - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL : kabu API の Base URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）

   サンプル .env（プロジェクトルート）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（クイックスタート）

以下は Python スクリプトや REPL での簡単な利用例です。

1. DuckDB スキーマを初期化する

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   ":memory:" を渡すことでメモリ DB を利用できます（テスト用）。

2. 日次 ETL を実行する（J-Quants からデータ取得して保存 → 品質チェック）

   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

3. 特徴量を計算して features に保存する

   ```python
   from datetime import date
   from kabusys.strategy import build_features
   count = build_features(conn, target_date=date(2026, 1, 31))
   print(f"features upserted: {count}")
   ```

4. シグナルを生成して signals テーブルに保存する

   ```python
   from kabusys.strategy import generate_signals
   from datetime import date
   total = generate_signals(conn, target_date=date(2026, 1, 31))
   print(f"signals generated: {total}")
   ```

5. ニュース収集ジョブを実行する

   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

注意点：
- run_daily_etl 等は内部で例外処理を行い、ETLResult にエラーや品質問題を集約します。ログを確認して運用してください。
- 実運用（本番 / live）では KABUSYS_ENV を "live" に設定し、発注部分は十分にテスト・審査した上で運用してください。

---

## 主要モジュール説明（パス）

- kabusys/__init__.py
  - パッケージエントリ。バージョン情報を保持。

- kabusys/config.py
  - 環境変数管理、.env 自動ロード、設定プロパティ（settings）

- kabusys/data/
  - jquants_client.py : J-Quants API クライアント（fetch / save 関数）
  - news_collector.py : RSS 収集 → raw_news 保存、銘柄抽出
  - schema.py : DuckDB スキーマ定義・初期化（init_schema / get_connection）
  - pipeline.py : ETL パイプライン（run_daily_etl, run_prices_etl 等）
  - calendar_management.py : market_calendar 管理、営業日判定/探索
  - audit.py : 監査ログ用の DDL（signal_events, order_requests, executions）
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - features.py : zscore_normalize の再エクスポート

- kabusys/research/
  - factor_research.py : momentum / volatility / value 等のファクター計算
  - feature_exploration.py : forward returns / IC / factor summary 等の分析ユーティリティ

- kabusys/strategy/
  - feature_engineering.py : research から来た raw factor を正規化・フィルタして features に保存
  - signal_generator.py : features と ai_scores を統合して BUY/SELL signals を生成

- kabusys/execution/
  - 将来的な発注ロジックを配置するためのパッケージ（現状空）

他に monitoring / UI 用のモジュール等を想定しています。

ツリー（抜粋）:

```
src/
  kabusys/
    __init__.py
    config.py
    data/
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      calendar_management.py
      audit.py
      stats.py
      features.py
    research/
      factor_research.py
      feature_exploration.py
    strategy/
      feature_engineering.py
      signal_generator.py
    execution/
    monitoring/
```

---

## 運用上の注意・ベストプラクティス

- 環境変数は機密情報（トークンやパスワード）を含むため、安全に管理してください（CI/CD ではシークレットマネージャ等の利用を推奨）。
- DuckDB ファイルは定期的にバックアップしてください。デフォルトは data/kabusys.duckdb。
- J-Quants の API レート制限を遵守するため、クライアントに組み込まれている RateLimiter に依存していますが、並列化時は注意してください。
- 本番での自動発注を組み込む前に、paper_trading 環境で十分な検証を実施してください（KABUSYS_ENV を使用）。

---

## 貢献 / 開発

- Python 3.10 以上で開発してください。
- コードスタイル、型ヒント、ログ出力に注意して PR をお願いします。
- 主要な機能はユニットテスト・統合テストを用意してからマージしてください。

---

ライセンスや追加のドキュメント（StrategyModel.md / DataPlatform.md / Research ドキュメント）がある場合は合わせて参照してください。README に不足している使い方・設定の詳細は該当ドキュメントに追記してください。