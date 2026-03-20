# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）の README。

このリポジトリはデータ取得・ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ・監査記録などを含むモジュール群を提供します。戦略実装（strategy 層）とデータ基盤（data / research 層）を分離し、冪等性・トレーサビリティ・ルックアヘッドバイアス防止を設計方針としています。

主要な概念
- DuckDB をデータストアとして利用（ローカルファイルまたは in-memory）
- J-Quants API から株価・財務・カレンダーを取得（ページネーション・リトライ・自動トークン更新）
- RSS ベースのニュース収集と銘柄紐付け
- 研究用のファクター計算（momentum / volatility / value 等）
- 特徴量正規化 → シグナル生成（BUY / SELL） → signals テーブルへ永続化
- 発注・実行管理のためのスキーマ（信頼性の高い監査ログ設計）

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（fetch / save: daily quotes, financial statements, market calendar）
  - 保存は冪等（ON CONFLICT で更新）
- ETL
  - 差分更新（最終取得日を元に差分を取得）、バックフィル対応
  - 日次 ETL パイプライン（calendar, prices, financials, 品質チェック）
- スキーマ管理
  - DuckDB スキーマ初期化（raw / processed / feature / execution レイヤー）
- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research/factor_research）
  - クロスセクション Z スコア正規化（data.stats.zscore_normalize）
  - 特徴量作成（strategy.feature_engineering.build_features）→ features テーブル
- シグナル生成
  - 正規化ファクターと AI スコアを統合して final_score を算出（strategy.signal_generator.generate_signals）
  - BUY / SELL ロジック（閾値、Bear レジーム抑制、ストップロスなど）
  - signals テーブルへの日付単位の置換保存（冪等）
- ニュース収集
  - RSS 取得・前処理・ID生成（SSRF / XML 攻撃対策、gzip 解凍、トラッキングパラメータ除去）
  - raw_news / news_symbols への保存（チャンク & トランザクション）
- カレンダー管理
  - market_calendar の更新・営業日判定ユーティリティ
- 監査ログ
  - signal_events / order_requests / executions 等でトレース可能な監査スキーマ

---

## セットアップ手順

必要環境（一例）
- Python 3.9+（typing の新機能を使用）
- pip

必須パッケージ（最低限）
- duckdb
- defusedxml

インストール手順（プロジェクトルートで実行）:

1. 仮想環境を作成＆有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

2. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # または開発用の requirements ファイルがあればそれを使う
   # pip install -r requirements.txt
   ```

3. パッケージを編集可能モードでインストール（任意）
   ```bash
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（自動読み込みはデフォルトで有効）。
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：ETL 実行時）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（execution 関連で使用）
     - KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（通知実装があれば使用）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（簡単な例）

以下は Python スクリプト / REPL で利用するサンプルフローです。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（J-Quants トークンが設定済みであること）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

3. 特徴量のビルド（target_date を指定）
   ```python
   from kabusys.strategy import build_features
   from datetime import date
   count = build_features(conn, date(2025, 1, 31))
   print(f"features upserted: {count}")
   ```

4. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date
   total_signals = generate_signals(conn, date(2025, 1, 31))
   print(f"signals written: {total_signals}")
   ```

5. ニュース収集（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
   stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(stats)
   ```

6. カレンダー更新ジョブ（夜間バッチ用）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print("calendar saved:", saved)
   ```

注意:
- 上記はライブラリ API の直接利用例です。運用では CLI またはジョブランナー（cron, systemd timer, Airflow 等）から呼び出す想定です。
- ETL を実行するには J-Quants の認証情報（JQUANTS_REFRESH_TOKEN）が必要です。
- 実際の発注・execution 層を動かす場合は kabuステーション等の設定と安全対策が必要です（本リポジトリは発注 API との接続点を用意していますが、実行環境での確認・権限管理は必須）。

---

## ディレクトリ構成

主要ファイル / モジュールの一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数・設定管理（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント、取得・保存ロジック
    - news_collector.py         — RSS 収集・保存・銘柄抽出
    - schema.py                 — DuckDB スキーマ定義・初期化
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — market_calendar の更新・営業日ユーティリティ
    - features.py               — features API（再エクスポート）
    - audit.py                  — 監査ログスキーマ（signal_events, order_requests, executions）
    - execution/                 — execution 層（発注ロジック等の拡張点）
  - research/
    - __init__.py
    - factor_research.py        — ファクター計算（momentum / volatility / value）
    - feature_exploration.py    — 将来リターン・IC・統計サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py    — features テーブル構築（正規化・フィルタ等）
    - signal_generator.py       — final_score 計算と signals 生成
  - monitoring/                 — 監視・メトリクス（SQLite を想定）
  - execution/                  — 発注実行に関する実装場所（未展示の部分）

README で触れていない補助モジュール・テスト・ドキュメント等もリポジトリ内に存在する可能性があります。各モジュールは docstring とコメントで設計思想・想定動作が詳細に記載されています。

---

## 開発メモ・運用上の注意

- 環境分離: KABUSYS_ENV により development / paper_trading / live を切り替え、ミスで実口座へ流さない運用を推奨します。
- 認証情報: J-Quants トークン・ブローカーの資格情報は安全に保管してください（共有リポジトリに置かない）。
- 自動ロード: config モジュールはプロジェクトルート（.git または pyproject.toml を探索）から .env を自動読み込みします。CI/テスト時に自動ロードを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト: ETL / API 呼び出しはネットワークや外部 API に依存するため、ユニットテストでは外部呼び出しをモックすることを推奨します（コード内にもモック差し替えを想定した抽象化あり）。
- データの冪等性: save_* 系関数は ON CONFLICT を使っているため、何度実行しても同じ結果となることを意図しています。ただしスキーマやロジック変更時は注意してください。
- ロギング: LOG_LEVEL と組み合わせて実行ログを監視してください。長時間バッチ運用ではログローテーションが必要です。

---

必要に応じて README を拡張して、CLI コマンド例、デプロイ方法（systemd / Docker / Kubernetes）、CI 設定、運用 runbook（バックアップ・リストア手順）などを追加できます。追加したい項目があれば指示してください。