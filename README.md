# KabuSys

日本株向け自動売買・データプラットフォームライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）、および戦略用ヘルパーを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援する内部ライブラリ群です。主に以下を目的とします。

- J-Quants API を通じた株価/財務/カレンダーデータの差分 ETL（DuckDB 保存、冪等保存）
- RSS ベースのニュース収集と OpenAI（LLM）を用いたニュースセンチメント評価
- 銘柄レベルのファクター計算（モメンタム、バリュー、ボラティリティ等）、特徴量解析ユーティリティ
- マーケットカレンダー管理（JPX）、営業日判定ロジック
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定までの監査ログスキーマ（監査・トレーサビリティ用の DuckDB スキーマ）

設計方針として、バックテストでのルックアヘッドバイアス防止、API 呼び出しの堅牢性（リトライ/バックオフ）、および DuckDB を用いた効率的な SQL ベース処理に重きを置いています。

---

## 主な機能一覧

- データ取得・ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（kabusys.data.jquants_client）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存
- ニュース NLP（kabusys.ai.news_nlp）
  - GPT 系モデルを用いた銘柄別センチメント算出（ai_scores テーブルへ保存）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の MA200 乖離とマクロニュースの LLM スコアを合成して日次レジーム判定
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリー
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ
- 設定管理（kabusys.config）
  - 環境変数/.env 自動ロード、Settings クラスでプロパティ参照

---

## 前提・依存関係

- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

実プロジェクトでは pyproject.toml / requirements.txt 等で依存管理する想定です。

---

## セットアップ手順

1. リポジトリをクローン（あるいはパッケージを入手）
2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```
3. pip を更新して依存パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   pip install duckdb openai defusedxml
   # 開発用にパッケージ化が用意されていれば:
   # pip install -e .
   ```
4. .env を用意
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を配置すると、自動的に読み込まれます。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。
   - 必要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（発注/実行周り）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - OPENAI_API_KEY: OpenAI 呼び出し（score_news / regime_detector 等）を使用する場合
   - データベースパス（任意、既定値あり）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
   - システム設定:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

5. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下はライブラリの代表的なユースケースの簡単なコード例です。実行は仮想環境内で行ってください。

- DuckDB 接続の作成（設定の DUCKDB_PATH を使用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務を差分取得して DuckDB に保存）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（前日15:00〜当日08:30のウィンドウ）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_schema を直接呼び出すことも可能
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意:
- OpenAI を呼ぶ関数は api_key を引数で渡すこともできます（引数優先）。引数を省くと環境変数 OPENAI_API_KEY を参照します。
- 各関数は DuckDB 接続を受け取る設計のため、単体テスト時には in-memory DB を使うと便利です（例: duckdb.connect(":memory:")）。

---

## 設定と自動 .env 読み込みの挙動

- モジュール kabusys.config はプロジェクトルート（.git または pyproject.toml を起点）を探し、`.env` → `.env.local` の順で自動読み込みします。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Settings クラス経由で設定値にアクセスできます（例: `from kabusys.config import settings; settings.jquants_refresh_token`）。
- 未設定の必須変数にアクセスすると ValueError が発生します。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py
  - パッケージ初期化、バージョン情報
- config.py
  - 環境変数/.env 読み込み、Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント算出（OpenAI 呼び出し、チャンク処理、バリデーション）
  - regime_detector.py — MA200 とマクロニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック、リトライ・レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - etl.py — ETLResult の再エクスポート
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
  - news_collector.py — RSS 収集・前処理・保存（SSRF 対策、gzip/サイズ上限）
  - audit.py — 監査ログ（DDL / インデックス / 初期化ユーティリティ）
- research/
  - __init__.py
  - factor_research.py — momentum / value / volatility 計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

各モジュールは docstring に仕様・設計方針・注意点が詳細に記載されています。実装は DuckDB の SQL と Python の組合せで行われており、外部への書き込み（発注等）を行うものは分離された設計です。

---

## テスト・開発時のポイント

- 自動 .env ロードを無効にする: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`（ユニットテスト時に便利）
- OpenAI / J-Quants 等の外部 API 呼び出しはモック可能（内部で関数分離・差し替えしやすい実装）
- DuckDB の in-memory DB（":memory:"）を使うとテストが簡単です
- ログレベルは `LOG_LEVEL` で制御可能（Settings.log_level）

---

## 追加・貢献

- ドキュメントやテストの追加、外部 API の追加サポート、監査スキーマ拡張などは歓迎します。
- pull request を作成する際は関連するモジュールの docstring と単体テストを用意してください。

---

README はここまでです。必要であれば:
- .env.example のテンプレート作成
- より詳しい ETL 実行例（cron/コンテナ化）
- CI / デプロイ手順（paper/live 環境の扱い）

などを追加で作成します。どの情報を優先して追加しますか？