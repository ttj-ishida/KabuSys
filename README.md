# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。J-Quants API から市場データや財務データを取得して DuckDB に整備し、特徴量作成・シグナル生成・ニュース収集・カレンダー管理など、戦略開発と運用に必要な機能群を提供します。

主な設計方針:
- ルックアヘッドバイアス回避（target_date 時点のデータのみを利用）
- 冪等性（DuckDB への保存は ON CONFLICT / トランザクションで整合を保つ）
- 外部 API（発注等）への直接依存を最小化しモジュール化
- 標準ライブラリ中心（外部依存は最小限に抑制）

---

## 機能一覧

- データ取得・保存
  - J-Quants から日次株価（OHLCV）・財務データ・市場カレンダー取得（jquants_client）
  - DuckDB に対する冪等保存（raw_prices / raw_financials / market_calendar 等）
- ETL パイプライン
  - 差分取得・バックフィル・品質チェックを組み合わせた日次 ETL（data.pipeline）
- スキーマ管理
  - DuckDB 用スキーマ初期化・接続ユーティリティ（data.schema）
- 特徴量計算 / 戦略
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）（research.factor_research）
  - クロスセクション Z スコア正規化ユーティリティ（data.stats）
  - 特徴量構築（strategy.feature_engineering）
  - シグナル生成（strategy.signal_generator）
- ニュース収集
  - RSS フィード収集・前処理・記事保存・銘柄抽出（data.news_collector）
  - SSRF 対策・XML パース安全化・サイズ制限など堅牢な実装
- マーケットカレンダー管理
  - 営業日判定、次/前営業日、期間内営業日列挙、夜間更新ジョブ（data.calendar_management）
- 監査 / 実行層
  - 発注・約定・ポジション・監査ログ用テーブル定義（data.audit, schema）
- 設定管理
  - .env / 環境変数自動読み込み・バリデーション（config）

---

## セットアップ

前提
- Python 3.9+（typing | union 型注釈を使用しているため、環境に合わせて Python バージョンを選択してください）
- DuckDB（Python パッケージとしてインストール）

推奨手順（プロジェクトルートで実行）:

1. 仮想環境を作成・有効化:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell 等)
   ```

2. 必要パッケージをインストール:
   - 必須: duckdb, defusedxml
   - 開発用に setuptools 等が必要ならプロジェクトの pyproject.toml / setup.cfg を参照してください
   ```bash
   pip install duckdb defusedxml
   # パッケージを editable インストール（プロジェクト配布がある場合）
   pip install -e .
   ```

3. 環境変数の設定:
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。
   - 必須の環境変数（実行に必要）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabu API パスワード
     - SLACK_BOT_TOKEN: Slack ボットトークン
     - SLACK_CHANNEL_ID: 通知先の Slack チャンネル ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV: deployment 環境 (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト INFO）
     - KABU_API_BASE_URL: kabu API base URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（主要ユースケース）

以下は簡易的な Python サンプルです。適宜ログ設定やエラーハンドリングを追加してください。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（J-Quants から差分取得 -> 保存 -> 品質チェック）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定しないと today が対象
   print(result.to_dict())
   ```

3. 特徴量構築（features テーブルへ書き込み）
   ```python
   from kabusys.strategy import build_features
   from datetime import date
   n = build_features(conn, date(2025, 1, 15))
   print(f"features upserted: {n}")
   ```

4. シグナル生成（signals テーブルへ書き込み）
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date
   total = generate_signals(conn, date(2025, 1, 15))
   print(f"signals written: {total}")
   ```

5. ニュース収集ジョブ（RSS -> raw_news / news_symbols）
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes を与えると本文から銘柄コード抽出して紐付けを行う
   res = run_news_collection(conn, known_codes={"7203","6758"})
   print(res)  # {source_name: saved_count, ...}
   ```

6. マーケットカレンダー更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

7. 設定（settings）参照
   ```python
   from kabusys.config import settings
   print(settings.jquants_refresh_token)  # 存在しないと ValueError
   print(settings.is_live, settings.log_level)
   ```

注意:
- run_daily_etl やデータ取得系関数は API との通信や DB 書き込みを行うため、実行権限・ネットワーク・API トークンが必要です。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化し、必要な環境変数を明示的に差し替えてください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/ 配下にパッケージ化されています。代表的なファイル一覧は下記のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得 + 保存）
    - news_collector.py            — RSS 収集・前処理・保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                  — ETL パイプライン（差分更新 / 品質チェック）
    - features.py                  — data.features 再エクスポート
    - calendar_management.py       — 市場カレンダー管理
    - audit.py                     — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py       — features テーブル構築
    - signal_generator.py          — final_score 計算・signals 作成
  - execution/                      — 発注／実行関連（初期プレースホルダ）
  - monitoring/                     — 監視・メトリクス（初期プレースホルダ）

（README に記載のない追加モジュールやテスト、スクリプト等がある場合はプロジェクトルートを参照してください）

---

## 設計上の注意点・運用メモ

- 環境の分離:
  - KABUSYS_ENV により動作モードを切替（development / paper_trading / live）。本番では `live` を使用してください。
- 自動 .env ロード:
  - パッケージはプロジェクトルートを .git または pyproject.toml を基準に探索して `.env` / `.env.local` を自動ロードします。CI / テストで自動ロードしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 冪等性:
  - 多くの保存関数は ON CONFLICT（または DO NOTHING / RETURNING）やトランザクションを使って冪等性を保っています。外部から実行する場合も同一データの二重実行を意識してください。
- セキュリティ:
  - news_collector は SSRF 対策や XML パースの差し替え攻撃防止（defusedxml）を実装しています。外部からのフィード URL は慎重に扱ってください。
- ログと監視:
  - LOG_LEVEL で制御。運用では外部ログ集約（例: CloudWatch / ELK）や Slack 通知などの連携を検討してください。

---

## さらに詳しく / 開発者向け情報

- コーディング規約、データモデル（DataSchema.md）、戦略仕様（StrategyModel.md）、DataPlatform.md 等のドキュメントに実装詳細が記載されています（リポジトリに同梱されている想定）。
- テスト:
  - 外部 API 呼び出しはモック可能なように id_token の注入や _urlopen などの内部関数の差し替えを設計に取り入れています。ユニットテストではモックを使用してください。
- 依存関係の追加:
  - 必要に応じて pip パッケージを追加してください（例: pandas を導入して分析機能を拡張する等）。

---

質問や README に追加してほしい例（例: CI 設定、具体的な .env.example）などがあれば教えてください。README をプロジェクトに合わせて拡張します。