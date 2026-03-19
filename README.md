# KabuSys — 日本株自動売買プラットフォーム

バージョン: 0.1.0

このリポジトリは、日本株向けのデータ基盤・ファクター計算・戦略シグナル生成・ETL を含む自動売買システムのコアライブラリです。DuckDB をデータレイクとして利用し、J-Quants API からのデータ収集、ニュース収集、特徴量（features）生成、戦略シグナル生成、発注監査ログなどの機能を提供します。

主な設計方針:
- ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで保護）
- テスト可能性（依存注入・キャッシュ制御・自動環境読み込みの無効化）

---

## 機能一覧

- 環境変数 / .env 読み込みと管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須変数未設定時のエラー報告

- データ取得（kabusys.data.jquants_client）
  - J-Quants API から日次株価・財務データ・マーケットカレンダーを取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - DuckDB への idempotent 保存（ON CONFLICT）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新／バックフィル対応の prices/financials/calendar ETL
  - 日次ETL 実行エントリ（run_daily_etl）
  - 品質チェック（quality モジュール呼び出し、別実装）

- スキーマ管理（kabusys.data.schema）
  - DuckDB スキーマ定義・初期化（init_schema）
  - テーブル群（raw / processed / feature / execution / audit）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、記事ID生成（URL 正規化 + SHA-256）
  - SSRF 対策、gzip 制限、XML 安全パーサ（defusedxml）
  - raw_news / news_symbols への冪等保存

- 特徴量計算（kabusys.research.factor_research）
  - Momentum / Volatility / Value 等のファクターを計算
  - DuckDB を使った SQL + Python 実装

- 特徴量正規化（kabusys.strategy.feature_engineering）
  - ユニバースフィルタ（最低株価・流動性）適用
  - Z スコア正規化（クロスセクション）・クリップ
  - features テーブルへ日付単位で UPSERT（冪等）

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score 計算
  - Bear レジームフィルタ、BUY/SELL シグナル生成
  - signals テーブルへ日付単位で置換（冪等）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次/前営業日取得、カレンダー更新ジョブ

- 統計ユーティリティ（kabusys.data.stats）
  - Z スコア正規化の汎用実装（外部ライブラリ不使用）

---

## 要件

- Python 3.10 以上（typing の | 構文等を使用）
- DuckDB Python パッケージ
- defusedxml（ニュース RSS の安全パース）
- （ネットワーク経由で J-Quants を利用する場合）インターネット接続と有効な J-Quants リフレッシュトークン

推奨パッケージ（例）:
pip install duckdb defusedxml

（実運用ではログ・HTTP クライアント拡張等の追加パッケージが必要になる可能性があります）

---

## 環境変数

kabusys/config.py で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注連携時）
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb) — DuckDB ファイルパス
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, default: development) — 有効値: development / paper_trading / live
- LOG_LEVEL (任意, default: INFO) — DEBUG/INFO/WARNING/ERROR/CRITICAL

自動読み込み:
- プロジェクトルートに `.env` / `.env.local` がある場合、自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成・有効化

   - 例:
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows

2. 依存パッケージをインストール

   - 最低限:
     pip install duckdb defusedxml

   - 実運用では logging、HTTP、テスト用パッケージなどを追加してください。

3. 環境変数を設定

   - プロジェクトルートに `.env`（または `.env.local`）を作成してください。
   - 必須項目（例）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...

   - 可能であれば `.env.example` を参考にしてください（リポジトリに含めていない場合は自力で作成）。

4. DuckDB スキーマ初期化

   - Python REPL またはスクリプトで実行:

     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # :memory: も可

   - これで必要なテーブルとインデックスが作成されます。

---

## 使い方（基本例）

以下は代表的なワークフローのスニペットです。実際はログ・例外処理・ジョブスケジューラ（cron 等）と組み合わせて運用してください。

1) スキーマ初期化（先述）

   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

2) 日次 ETL 実行（J-Quants からの差分収集）

   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

3) 特徴量作成（features テーブルの作成）

   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date.today())
   print(f"features upserted: {n}")

4) シグナル生成

   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals written: {total}")

5) ニュース収集ジョブ（RSS）

   from kabusys.data.news_collector import run_news_collection
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")
   # known_codes: 銘柄抽出に使う有効コードの集合（例: {'7203','6758',...}）
   results = run_news_collection(conn, known_codes=set(), sources=None)
   print(results)

6) マーケットカレンダー更新

   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")

---

## 注意点・運用メモ

- Python バージョン: 本コードは Python 3.10+ の構文（PEP 604 の union types など）を使用しています。
- 環境変数の自動読み込みは .env の存在場所をプロジェクトルート（.git または pyproject.toml を基準）から自動検出します。テストや一時環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- DuckDB のパスは Settings.duckdb_path（環境変数 DUCKDB_PATH）で変更可能。
- J-Quants の API レート制限やトークン扱いには注意（jquants_client がリミットとリトライを持ちます）。
- news_collector は外部 RSS を取得するため、ネットワークポリシー・SSRF 制御に注意。モジュールは SSRF 対策を組み込んでいます。
- 実際に発注を行う execution 層・ブローカー連携は本コードベースの一部（audit / execution テーブル等）をサポートしますが、証券会社 API の実装は別途必要です。

---

## ディレクトリ構成

概略:

src/
  kabusys/
    __init__.py                 - パッケージメタ情報 (version)
    config.py                   - 環境変数 / 設定管理
    data/
      __init__.py
      schema.py                 - DuckDB スキーマ定義・初期化
      jquants_client.py         - J-Quants API クライアント + 保存
      pipeline.py               - ETL パイプライン（run_daily_etl 等）
      news_collector.py         - RSS ニュース収集・保存
      calendar_management.py    - マーケットカレンダー管理
      features.py               - features 公開インターフェース
      stats.py                  - 統計ユーティリティ（zscore_normalize）
      audit.py                  - 発注監査ログスキーマ（未完の DDL あり）
      execution/                 - 発注関連（空の __init__.py が存在）
    research/
      __init__.py
      factor_research.py        - ファクター計算（momentum/value/volatility）
      feature_exploration.py    - 研究用分析（IC/forward returns 等）
    strategy/
      __init__.py
      feature_engineering.py    - features の構築（正規化・フィルタ）
      signal_generator.py       - final_score 計算とシグナル生成
    monitoring/                  - 監視・モニタリング系（フォルダ）
    execution/                   - 発注実行層（フォルダ）

重要ファイル:
- src/kabusys/__init__.py: バージョンと公開モジュール定義
- src/kabusys/config.py: Settings クラス（環境変数アクセス）
- src/kabusys/data/schema.py: init_schema / get_connection

---

## 開発・貢献

- コードはドキュメント内に参照されている設計ドキュメント（DataSchema.md、StrategyModel.md、DataPlatform.md 等）に基づいています。これらがない場合は実装コメントを参照してください。
- ユニットテストや CI、さらなる静的解析（型チェック、リント）を追加することを推奨します。
- 実稼働での発注・資金管理を行う場合は、バックテスト・ペーパー口座で十分に検証してください。

---

README に記載の無い詳細や、特定機能（quality モジュールや execution 実装等）についてのドキュメントが必要であれば、どの領域を掘り下げたいか教えてください。