# KabuSys

日本株向け自動売買・データプラットフォームライブラリ（KabuSys）。  
J-Quants / DuckDB を用いたデータ ETL、ニュース NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、売買システムの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築向けに設計されたモジュール群です。主な目的は以下：

- J-Quants API からの株価・財務・カレンダー取得（ETL）
- DuckDB を用いたローカルデータベース管理と品質チェック
- RSS ニュース収集・前処理と OpenAI によるニュースセンチメント評価（銘柄別 ai_score）
- ETF を用いた市場レジーム判定（MA200 とマクロニュースの統合）
- 研究用ファクター計算・特徴量探索ユーティリティ
- 監査ログ（signal → order → execution）のスキーマ初期化ユーティリティ
- 環境設定管理と自動 .env ロード

設計上の重要点：
- ルックアヘッドバイアスを避けるため、内部で datetime.today() を直接参照しない設計が多く採用されています（target_date を明示的に渡す）。
- 冪等性（ON CONFLICT / UPSERT）とフェイルセーフ（API失敗時のフォールバック）を重視。
- 外部 API 呼び出し（OpenAI/J-Quants）は明確に分離され、リトライ・レート制御を実装。

---

## 主な機能一覧

- data（ETL / calendar / jquants_client / news_collector / quality / stats / audit）
  - 日次 ETL（run_daily_etl）
  - J-Quants API クライアント（fetch/save / token 自動更新 / レート制御）
  - JPX カレンダー管理・営業日判定（is_trading_day / next_trading_day 等）
  - ニュース RSS 収集（SSRF 対策・トラッキング除去・前処理）
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログ（signal_events / order_requests / executions）のスキーマ初期化（init_audit_db / init_audit_schema）
  - 統計ユーティリティ（zscore_normalize）

- ai（news_nlp / regime_detector）
  - 銘柄ごとのニュースセンチメント評価（gpt-4o-mini, JSON Mode）→ ai_scores テーブルへ保存
  - マクロニュース + ETF1321 の MA200 乖離を合成した市場レジーム判定（bull/neutral/bear）

- research（factor_research / feature_exploration）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー

- config
  - .env ファイルまたは OS 環境変数からの設定読み込み（自動ロード機能あり）
  - 必須設定のチェックと型変換（Path/float 等）
  - 自動ロード無効化用: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

以下は開発環境での基本的なセットアップ例です。

1. リポジトリをクローン／プロジェクトルートへ移動

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール（プロジェクトに requirements.txt/pyproject.toml があればそちらを使用）
   例（最小セット）:
   - pip install duckdb openai defusedxml

   開発インストール（パッケージ化されている場合）:
   - pip install -e .

4. 環境変数設定
   プロジェクトルートに `.env` または `.env.local` を作成するか、OS 環境変数で設定してください。主なキー：

   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID (必須)
   - OPENAI_API_KEY (必須でないが ai 機能を使う場合は必須)
   - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (任意, 監視用)
   - KABUSYS_ENV: development / paper_trading / live
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   自動 .env ロードを無効化する場合：
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. ディレクトリ作成（データ格納先）
   - mkdir -p data

---

## 使い方（簡易サンプル）

以下はライブラリをインポートして主要な操作を行うサンプルです。すべて Python スクリプト内で実行できます。

- DuckDB 接続例（ファイル DB を使用）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を明示的に渡すことでルックアヘッドを回避
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア (銘柄別) の取得と保存
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーは環境変数 OPENAI_API_KEY に設定しておくか api_key に渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {written}")
  ```

- 市場レジームスコア計算
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（例: momentum）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点：
- OpenAI 呼び出しにはネットワークと API 制限があるため、API キーと料金プランに注意してください。
- run_daily_etl 等は内部で J-Quants のアクセストークンを取得するため、JQUANTS_REFRESH_TOKEN を必ず設定してください。

---

## 推奨ワークフロー例

- バッチ ETL（夜間）:
  1. run_daily_etl を cron で定期実行。market_calendar → prices → financials → 品質チェック。
  2. ETL 成果が得られたら、ニュース収集 → score_news（AI スコア）を実行。
  3. regime_detector で市場レジームを決定し、戦略・ポジション管理へ反映。

- 研究ワークフロー:
  - research モジュールでファクターを計算し、zscore_normalize 等で正規化→統計解析。

---

## ディレクトリ構成

主要なソースツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境設定 / .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュース集約・OpenAI 呼び出し・ai_scores 書込
    - regime_detector.py           -- 市場レジーム判定ロジック
  - data/
    - __init__.py
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - etl.py                       -- ETL 公開インターフェース
    - jquants_client.py            -- J-Quants API クライアント（fetch/save）
    - news_collector.py            -- RSS 収集・前処理
    - calendar_management.py       -- JPX カレンダー管理（営業日判定等）
    - quality.py                   -- データ品質チェック
    - stats.py                     -- 統計ユーティリティ（zscore_normalize）
    - audit.py                     -- 監査ログスキーマ初期化（init_audit_db 等）
  - research/
    - __init__.py
    - factor_research.py           -- Momentum/Volatility/Value ファクター
    - feature_exploration.py       -- forward returns / IC / rank / summary
  - monitoring/ (未記載実装ファイルがある想定)
  - strategy/, execution/ (パッケージ公開は __all__ に含まれるが実装は別途)

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化 (1 を設定)

.env の例（プロジェクトルートに .env を配置）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## その他の注意事項

- DuckDB との互換性: コード内に DuckDB 固有の挙動（executemany の空リスト制約など）への配慮がなされています。DuckDB のバージョンによって挙動が変わる可能性があるため、本番環境のバージョン固定を推奨します。
- OpenAI 呼び出しはリトライとバックオフを実装していますが、API レートやコストに注意してください。
- news_collector は SSRF 対策・受信サイズ制限などセキュリティ配慮が実装されています。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行います。テスト環境などで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

必要に応じて README に追記（インストールの詳細、CI / テスト手順、運用ガイド、API リファレンス）することができます。どの情報を優先的に補足したいか教えてください。