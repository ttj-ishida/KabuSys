# KabuSys

日本株のデータプラットフォームと自動売買（リサーチ・ETL・ニュースNLP・監査ログ）を提供するライブラリです。DuckDB をデータ保存に用い、J-Quants / JQ API から市場データを取得、OpenAI を用いたニュースセンチメント評価、研究用のファクター計算や品質チェック、監査ログ（発注トレース）などの機能を含みます。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を直接参照しない関数設計）
- DuckDB を中心とした冪等な ETL / 保存（ON CONFLICT を利用）
- 外部 API 呼び出しに対するリトライ / フェイルセーフ実装
- OpenAI の JSON Mode を使った堅牢な応答パースとバリデーション

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（jquants_client / data.pipeline）
  - 日次 ETL の統合実行（run_daily_etl）
- データ品質管理
  - 欠損・重複・スパイク・日付不整合の検出（data.quality）
- ニュース収集・NLP
  - RSS フィード収集（news_collector）と前処理（SSRF対策・トラッキング除去）
  - OpenAI を用いた銘柄ごとのニュースセンチメント算出（ai.news_nlp.score_news）
  - マクロニュースと価格指標を組み合わせた市場レジーム判定（ai.regime_detector.score_regime）
- 研究用途ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算、IC、統計サマリー（research.feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ / トレーサビリティ
  - シグナル → 発注要求 → 約定 の監査テーブル定義と初期化（data.audit.init_audit_db）

---

## セットアップ手順

前提:
- Python 3.9+（typing の新構文を利用）
- DuckDB をローカルにインストール可能な環境
- OpenAI API キー（ニュース NLP / レジーム判定用）
- J-Quants のリフレッシュトークン（J-Quants API 用）
- 必要なパッケージ（例: duckdb, openai, defusedxml）

1. リポジトリをクローン / パッケージを配置
   - 開発環境であれば src 配下をパッケージとしてインストールします（プロジェクトルートに pyproject.toml がある想定）。

2. 仮想環境作成・依存パッケージインストール（例）
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

3. パッケージインストール（開発モード）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabu ステーション API 用パスワード（発注系利用時）
     - SLACK_BOT_TOKEN        — Slack 通知用（モニタリング機能利用時）
     - SLACK_CHANNEL_ID       — Slack チャンネル ID
     - OPENAI_API_KEY         — OpenAI 呼び出しを行う場合（関数引数で上書きも可）
   - 任意 / デフォルト可能:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト "development"
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト "INFO"
     - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH — デフォルト "data/monitoring.db"

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```

5. データベース初期化（監査DBの例）
   - Python から:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
     ```

---

## 使い方（基本例）

以下は最小限の呼び出し例です。詳しい引数や戻り値は各モジュールのドキュメントを参照してください。

- DuckDB 接続を開く（デフォルトパスは settings.duckdb_path）
  ```python
  import duckdb
  from pathlib import Path
  from kabusys.config import settings

  db_path = str(settings.duckdb_path)  # 環境変数で上書き可
  conn = duckdb.connect(db_path)
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得と品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア算出（OpenAI APIキーは環境変数 OPENAI_API_KEY か api_key 引数で指定）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("ai_scores written:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを組み合わせる）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  ok = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査DBの初期化（発注・約定トレース用）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

注意点:
- OpenAI 呼び出しは API エラー時にフェイルセーフ（スコア 0.0）にフォールバックする設計です。必要に応じてログを確認してください。
- ETL / 保存は DuckDB 側のスキーマが必要です（プロジェクトにスキーマ初期化ロジックがあれば実行してください）。

---

## ディレクトリ構成（主要ファイル）

（抜粋 — 実際のリポジトリでは pyproject.toml / tests / scripts 等が存在する場合があります）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理（.env 自動読み込み）
    - ai/
      - __init__.py
      - news_nlp.py            — ニュースセンチメント算出（OpenAI）
      - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント & DuckDB 保存
      - pipeline.py            — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py — 市場カレンダー管理 / 営業日ロジック
      - news_collector.py      — RSS 収集 / 前処理 / SSRF 対策
      - quality.py             — データ品質チェック（欠損・重複・スパイク等）
      - stats.py               — Zスコア正規化など統計ユーティリティ
      - etl.py                 — ETLResult の再エクスポート
      - audit.py               — 監査ログスキーマ定義と初期化
    - research/
      - __init__.py
      - factor_research.py     — モメンタム / ボラティリティ / バリュー等
      - feature_exploration.py — 将来リターン / IC / 統計サマリー
    - ai/
      - (news_nlp, regime_detector) 上述
    - research/
      - (factor_research, feature_exploration) 上述

---

## 補足 / 運用上の注意

- .env の自動読み込みはプロジェクトルート（.git もしくは pyproject.toml の親ディレクトリ）を基準に行います。テスト時などで自動ロードしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定値は Settings クラス（kabusys.config.settings）からアクセスできます（例: settings.duckdb_path）。
- J-Quants API はレート制限があるため jquants_client は内部でレートリミッタ・リトライを実装しています。
- OpenAI API のレスポンス検証は厳密に行われます（JSON 抽出・バリデーション）。API のバージョンや返却フォーマットの変更に注意してください。
- DuckDB のバージョンや SQL の互換性により executemany の挙動が異なる場合があります（pipeline や ai.news_nlp 内で対策済み）。

---

この README はコードの主要部分を要約したものです。各モジュールの詳細な使い方やパラメータは該当ファイルの docstring / 関数コメントを参照してください。必要であればセットアップスクリプトや例示用の CLI スクリプトの追加も対応できます。