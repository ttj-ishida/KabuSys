# KabuSys

日本株向けの自動売買／データ基盤ライブラリ KabuSys のリポジトリ用 README（日本語）。

この README はリポジトリ内の実装ファイルを基に作成しています。プロジェクトはデータ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI を利用したセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（トレース）等の機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成する下記レイヤを含む Python パッケージです。

- データ収集 / ETL：J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存
- データ品質管理：欠損・スパイク・重複・日付不整合のチェック
- ニュース収集・NLP：RSS からニュースを収集し OpenAI で銘柄ごとのセンチメントスコアを生成
- 市場レジーム判定：ETF（1321）200 日 MA とマクロニュースを合成して市場レジームを算出
- リサーチ用ファクター計算：モメンタム、バリュー、ボラティリティ等の計算
- 監査ログ（Audit）：シグナル→発注→約定のトレーサビリティを保存する監査テーブル
- 外部連携設定：kabuAPI、Slack、OpenAI、J-Quants 等の設定管理

設計上の特徴：
- DuckDB をデータ格納に利用（軽量・高速な分析向け）
- Look-ahead bias を避けるため、内部で現在時刻を直接参照しない設計を重視
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスのバリデーション／リトライを実装
- J-Quants API 呼び出しはレート制御およびトークンリフレッシュを含む堅牢な実装

---

## 主な機能一覧

- data/
  - jquants_client：J-Quants API からのデータ取得・DuckDB への保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline：日次 ETL（差分取得・バックフィル・品質チェック）
  - quality：欠損・重複・スパイク・日付整合性チェック
  - news_collector：RSS 収集・前処理・保存（SSRF 対策・トラッキング除去）
  - calendar_management：営業日判定・次/前営業日・カレンダー更新ジョブ
  - audit：監査ログ用テーブル初期化・専用 DB 初期化
  - stats：Z スコア正規化などの統計ユーティリティ
- ai/
  - news_nlp：銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に書き込む
  - regime_detector：1321 の MA200 乖離とマクロニュースで日次市場レジーム判定
- research/
  - factor_research：モメンタム・ボラティリティ・バリュー等のファクター計算
  - feature_exploration：将来リターン計算、IC、統計サマリー等
- config.py：環境変数読み込み・設定管理（.env 自動読み込み対応）
- その他：各種ユーティリティ

---

## セットアップ手順（開発環境向け）

1. Python（推奨 3.10 以上）を用意します。

2. 必要パッケージをインストールします（プロジェクトに requirements.txt があればそれを使ってください）。最低限必要なパッケージ例：
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（config.py の自動ロード）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   推奨の `.env`（例）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

   # OpenAI（news_nlp / regime_detector で使用）
   OPENAI_API_KEY=sk-...

   # kabuステーション API (実行/約定系を使う場合)
   KABU_API_PASSWORD=...

   # Slack（通知等を使う場合）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456

   # DB ファイルパス（任意。デフォルト: data/kabusys.duckdb）
   DUCKDB_PATH=data/kabusys.duckdb

   # 動作環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. （任意）プロジェクトルートに `pyproject.toml` や `.git` があると config の自動 .env 探索が有効になります。

---

## 使い方（主要な呼び出し例）

以下は Python スクリプト／REPL からの利用例です。事前に環境変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続の作成例：
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（市場カレンダー、株価、財務データ、品質チェックを実行）：
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を省略すると today が使用される
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとのニューススコア付け）：
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数に設定済みなら api_key は省略可
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定：
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

  - OpenAI API キーを引数で渡すことも可能（api_key="..."）。

- 監査ログテーブルの初期化（既存の DuckDB に監査スキーマを追加）：
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn, transactional=True)
  ```

- 監査ログ専用 DB を新規作成して初期化：
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/monitoring_audit.duckdb")
  ```

- J-Quants の個別取得（ライブラリ内 API）：
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

注意点：
- OpenAI 呼び出しを行う機能（news_nlp, regime_detector）は API キーが必要です。api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants 接続は JQUANTS_REFRESH_TOKEN を使って id_token を発行します。`.env` にリフレッシュトークンを設定してください。
- DuckDB の executemany に空リストを渡すと問題となるバージョンのある処理をハンドルする実装になっています。

---

## よくある操作・トラブルシュート

- 自動 .env ロードを無効にしたい（テスト等）:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- OpenAI レスポンスが不正 / JSON パース失敗時:
  - モジュールはフェイルセーフとしてスコアを 0 にフォールバックするか、該当チャンクをスキップします。ログを確認してください。

- J-Quants API の 401（認証失敗）が出る場合:
  - refresh token が正しいか、`JQUANTS_REFRESH_TOKEN` を確認してください。jquants_client は 401 を検知するとトークンを自動リフレッシュし一度だけ再試行します。

- RSS 収集の SSRF 対策:
  - news_collector は URL のスキーム検証、リダイレクト先の検証、プライベートアドレスの検出を行います。内部ネットワークにアクセスしないよう保護されています。

---

## 環境変数（主なもの）

config.Settings クラスから参照される主要な環境変数（必須は README にて明示）:

必須（使用機能に応じて設定）
- JQUANTS_REFRESH_TOKEN  (J-Quants API 用)
- SLACK_BOT_TOKEN        (Slack 使用時)
- SLACK_CHANNEL_ID       (Slack 使用時)
- KABU_API_PASSWORD      (kabuステーション API を使う場合)

OpenAI / DB / 動作設定（任意だが実運用では必須）
- OPENAI_API_KEY         (news_nlp / regime_detector で必要)
- DUCKDB_PATH            (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH            (デフォルト: data/monitoring.db)
- KABUSYS_ENV            (development, paper_trading, live のいずれか、デフォルト: development)
- LOG_LEVEL              (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)
- PID_FILE_PATH          (監視用 PID ファイルパス)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT (監視しきい値)

---

## ディレクトリ構成（抜粋）

以下はパッケージ内部の主要ファイル/ディレクトリ構成の抜粋です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - quality.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - stats.py
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - その他（execution, monitoring, strategy 等のサブパッケージを __all__ で公開予定）

（注）ここに列挙されていないモジュールや将来的な拡張はリポジトリの実ファイルを参照してください。

---

## 開発メモ / 注意事項

- DuckDB を利用しているため、分析クエリは SQL と Python の組合せで記述されています。大規模データの処理や並列化には注意してください。
- OpenAI / J-Quants API 呼び出しはネットワーク依存であり、リトライやバックオフを実装していますが、API 利用上限や課金に注意してください。
- 監査テーブルは削除しない想定（トレーサビリティを保持）。スキーマ初期化は冪等（存在確認）になっています。
- 本 README はコードベースの静的解析に基づく概要です。実際のセットアップ手順や追加ツール（CI / Docker / バックテスト環境等）はプロジェクトのトップレベル設定に従ってください。

---

必要であれば、README に追加したい具体的なセットアップ手順（例：Docker, systemd サービス設定、CI 用スクリプト、依存関係ファイルへの記載など）やサンプル .env.example の完全版を作成します。どの情報を優先して加えるか教えてください。