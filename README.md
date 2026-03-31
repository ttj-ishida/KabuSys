# KabuSys

日本株向け自動売買 / データ基盤ライブラリ (KabuSys)

このリポジトリは日本株のデータ収集（J-Quants）、データ品質チェック、特徴量計算、ニュースの自然言語処理（LLM）を用いたセンチメント評価、ならびに監査ログ（発注→約定のトレース）を含むソフトウェアコンポーネント群を提供します。実際の発注ロジックやブローカー接続は別モジュール（execution 等）で扱うことを想定した設計です。

主な用途例:
- 日次ETLパイプラインによる株価 / 財務 / カレンダーの差分取得と保存
- ニュース記事の収集と LLM による銘柄センチメント算出
- 市場レジーム判定（MA200 と マクロニュースの合成）
- ファクター計算・特徴量探索（リサーチ用途）
- 監査用の DuckDB スキーマ初期化と監査ログ管理

---

## 機能一覧

- 環境変数管理と .env 自動ロード（`kabusys.config`）
  - プロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を読み込みます
  - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 日次株価（OHLCV）、財務データ、JPXカレンダー等の取得
  - レートリミット遵守、リトライ、IDトークン自動リフレッシュ、DuckDB への冪等保存
- ETL パイプライン（`kabusys.data.pipeline`）
  - 差分取得、保存、品質チェックを統合
  - `run_daily_etl` による日次実行
- データ品質チェック（`kabusys.data.quality`）
  - 欠損・スパイク・重複・日付不整合などの検出
  - 問題は QualityIssue のリストとして返却
- ニュース収集（`kabusys.data.news_collector`）
  - RSS 収集、URL 正規化、SSRF 対策、メモリ上限管理、raw_news への冪等保存（設計に基づく）
- ニュース NLP（`kabusys.ai.news_nlp`）
  - OpenAI (gpt-4o-mini) を使った銘柄別センチメント算出
  - バッチ化、リトライ、レスポンスバリデーション、ai_scores テーブルへ保存
- 市場レジーム判定（`kabusys.ai.regime_detector`）
  - ETF(1321) の MA200 乖離とマクロ記事の LLM センチメントを合成してレジーム（bull/neutral/bear）を判定
- リサーチ / ファクター（`kabusys.research`）
  - Momentum / Volatility / Value 等のファクター計算、forward returns、IC、統計サマリ、zscore 正規化
- 監査ログ初期化（`kabusys.data.audit`）
  - signal_events / order_requests / executions など監査用テーブルの DDL とインデックスを提供
  - `init_audit_db` で専用 DuckDB を初期化可能

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - 推奨: Python 3.10+
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 本ライブラリは以下等を使用します（抜粋）:
     - duckdb
     - openai (OpenAI の最新 SDK)
     - defusedxml
   - 例（pip で個別インストール）:
     - pip install duckdb openai defusedxml
   - パッケージ配布用セットアップがある場合:
     - pip install -e .
     - または pip install -r requirements.txt（requirements があれば）

3. 環境変数設定 (.env)
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可）。
   - 必須環境変数（最低限の例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabus_api_password
     - SLACK_BOT_TOKEN=your_slack_token
     - SLACK_CHANNEL_ID=your_channel_id
   - 任意 / デフォルト有:
     - KABUSYS_ENV=development | paper_trading | live  （デフォルト: development）
     - LOG_LEVEL=INFO
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
   - サンプル（.env.example 形式）:
     ```
     JQUANTS_REFRESH_TOKEN=xxx
     OPENAI_API_KEY=xxx
     KABU_API_PASSWORD=xxx
     SLACK_BOT_TOKEN=xxx
     SLACK_CHANNEL_ID=xxx
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

4. データベース用ディレクトリ作成
   - DUCKDB_PATH 等で指定した親ディレクトリを作成しておくと良いです（多くの初期化関数が自動で作成しますが念のため）。

---

## 使い方（主要な利用例）

以下は対話的に Python から利用する際の例です。

- DuckDB 接続を作って ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコア付け（LLM を利用）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect('data/kabusys.duckdb')
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f'wrote {n_written} ai_scores')
  ```
  - `OPENAI_API_KEY` 環境変数が設定されているか、`api_key` 引数で渡してください。

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect('data/kabusys.duckdb')
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を用いて監査テーブルにアクセス可能
  ```

- ファクター計算（研究用途）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date
  conn = duckdb.connect('data/kabusys.duckdb')
  recs = calc_momentum(conn, target_date=date(2026,3,20))
  # recs は各銘柄の辞書リスト
  ```

注意点:
- AI（OpenAI）を呼ぶ関数は API キーを必要とします。API 呼び出しは課金が発生しますので注意してください。
- LLM 呼び出しは外部ネットワークに依存するため、テスト時はモック化することを推奨します（モジュール内で _call_openai_api をパッチする設計）。
- DuckDB クエリは設計上 look-ahead bias を避けるように実装されています（target_date より先のデータは参照しない等）。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (AI モジュールで必須、score_news / score_regime 等)
- KABU_API_PASSWORD (kabu ステーション用)
- KABUSYS_ENV (development / paper_trading / live) — settings.env で検証されます
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知用)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB 等、デフォルト data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み設定
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI）と ai_scores 登録
    - regime_detector.py     — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 / DuckDB 保存）
    - pipeline.py            — 日次 ETL パイプライン / 個別 ETL ジョブ
    - quality.py             — データ品質チェック
    - news_collector.py      — RSS 収集 / 前処理 / 保存
    - calendar_management.py — 市場カレンダーの管理 / 営業日判定
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - etl.py                 — ETLResult の再公開インターフェース
    - audit.py               — 監査ログスキーマ定義と初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — forward returns / IC / 統計サマリ

---

## テスト・開発メモ

- LLM 呼び出し部や外部 API 呼び出し部はモック化しやすい設計になっています（内部の `_call_openai_api` / `_urlopen` 等を patch）。
- 自動で .env を読み込む実装はプロジェクトルートを .git または pyproject.toml で探索します。CI やユニットテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定するか、明示的に設定値を注入してください。
- DuckDB に関する SQL は一部バージョン依存（executemany の空配列等の挙動）を考慮した実装があります。DuckDB の互換性に注意してください。

---

## 運用上の注意

- J-Quants（商用API）と OpenAI の利用はコストが発生します。API レート・コスト管理を行ってください。
- 実際の発注処理（execution 層）を本番環境で動かす場合は、`KABUSYS_ENV=live` とし、十分なテストと安全対策（多段チェック、監査ログの確認、二重発注防止）を行ってください。

---

ご質問や README の補足（例: API レスポンス例、より詳しいセットアップ手順、CI 用の設定例など）が必要であれば教えてください。README を用途に合わせて拡張します。