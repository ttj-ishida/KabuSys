# KabuSys

KabuSys は日本株向けのデータパイプライン・リサーチ・自動売買補助ツール群です。  
DuckDB をデータ層に使い、J-Quants / RSS / kabuAPI / OpenAI（LLM）等を組み合わせて、データ収集（ETL）、品質チェック、ニュースによる NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログなどを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得（J-Quants）
  - 日足（OHLCV）/ 財務データ / JPX カレンダーの差分取得（ページネーション対応、再試行・レート制御）
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
- ETL パイプライン
  - run_daily_etl による市場カレンダー・株価・財務データの差分取得と品質チェック
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集
  - RSS フィードからのニュース収集（SSRF対策、トラッキング除去、前処理）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント評価（gpt-4o-mini + JSON mode）
  - チャンク・バッチ処理、リトライ・フェイルセーフ
  - score_news(conn, target_date, api_key=None)
- 市場レジーム判定（AI + テクニカル）
  - ETF(1321) の 200 日移動平均乖離とマクロニュース（LLM）を合成して日次のレジーム判定
  - score_regime(conn, target_date, api_key=None)
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions 等の監査テーブル初期化ユーティリティ
  - init_audit_db() / init_audit_schema()
- ユーティリティ
  - 環境変数管理（.env 自動ロード）、統計ユーティリティ（Zスコア正規化）など

---

## システム要件

- Python 3.10 以上
- 主な依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（実際の requirements はプロジェクト側で管理してください。上記はコード内で使用されている主要パッケージです。）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化（例）
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

3. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（必須 / 任意）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL — kabuステーション API のベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 用）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を使う場合
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — 実行環境 (development | paper_trading | live)、デフォルトは development
   - LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB データベース初期化（監査ログ用）
   - 監査テーブルを別 DB に初期化する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
   ```
   - 既存の DuckDB 接続へ監査スキーマを追加:
   ```python
   from kabusys.data.audit import init_audit_schema
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要なユースケース）

- DuckDB に接続して ETL を走らせる（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（銘柄別 ai_scores への書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentums = calc_momentum(conn, date(2026,3,20))
  values = calc_value(conn, date(2026,3,20))
  vols = calc_volatility(conn, date(2026,3,20))
  ```

- 統計ユーティリティ（Zスコア正規化）
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])
  ```

- 監査ログを使った発注トレーサビリティ初期化
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

---

## 環境変数の自動ロードについて

- パッケージはプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動で読み込みます（`kabusys.config` の実装）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 自動読み込みは OS 環境変数を上書きしない設計（.env.local は override=True だが OS 環境変数は保護されます）。

---

## 開発時の注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス対策：target_date ベースでのクエリ、datetime.today()/date.today() の直接参照回避（関数の外から日付を注入する設計）。
- API 呼び出しはリトライとフェイルセーフを重視：LLM / J-Quants 呼び出しはリトライ・バックオフ、失敗時は安全側のデフォルトで継続。
- DuckDB へは冪等保存（ON CONFLICT DO UPDATE）を採用し、ETL の再実行に耐える設計。
- ニュース収集は SSRF 対策、XML の脆弱性対策（defusedxml）、応答サイズ制限などを行う。

---

## 主要ディレクトリ構成

（この README はリポジトリ内の src/kabusys 以下の実装に基づきます）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（銘柄ごとのスコアリング）
    - regime_detector.py           — マーケットレジーム判定（MA200 + LLM）
  - data/
    - __init__.py
    - calendar_management.py       — 市場カレンダー管理（営業日判定・更新ジョブ）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py            — J-Quants API クライアント（取得 + 保存関数）
    - news_collector.py            — RSS ニュース収集
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（Zスコア）
    - audit.py                     — 監査ログスキーマ初期化
    - etl.py                       — ETL の公開インターフェース（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（モメンタム・バリュー・ボラティリティ）
    - feature_exploration.py       — 将来リターン / IC / 統計サマリ等
  - (その他) strategy / execution / monitoring 等はパッケージの公開 API に含まれるが、
    実装は用途に応じて追加または外部連携される想定です。

---

## ロギング・実行環境

- LOG_LEVEL は環境変数で指定（デフォルト INFO）。
- KABUSYS_ENV により挙動（paper_trading / live など）を分ける場合のフラグが用意されています。実際の発注や外部連携を行うモジュールを運用する際は、この値を用いた厳格なリスク制御を行ってください。

---

## テスト・モックについて

- OpenAI / ネットワーク呼び出し / ルートの HTTP や時間依存処理はテスト時に差し替え（mock）できるよう設計されています（各モジュール内で呼び出し関数を切り出している箇所が多くあります）。
- ETL / 保存系は DuckDB を使ってローカルの一時 DB（:memory:）で動作確認可能です。

---

## ライセンス / 貢献

- ライセンス情報・貢献ガイドラインはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（必要に応じて追加してください）。

---

この README はコードベース（src/kabusys 以下）の主要機能と使い方の概要をまとめたものです。より詳細な API リファレンスや運用手順（本番 kabuAPI 接続や注文フロー、Slack 通知設定など）は別途ドキュメント化することを推奨します。必要であれば、運用手順例や .env.example のテンプレートも作成します。どの情報がさらに必要か教えてください。