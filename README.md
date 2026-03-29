# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J‑Quants からの差分取得）・ニュース収集・AI によるニュースセンチメント評価・市場レジーム判定・ファクター計算・データ品質チェック・監査ログ（発注→約定トレーサビリティ）など、アルゴリズム取引基盤で必要となる機能群を備えています。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J‑Quants API から株価日足、財務データ、JPX マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル・品質チェックを含む日次パイプライン（run_daily_etl）
- ニュース収集
  - RSS からのニュース収集・前処理・raw_news への冪等保存
  - SSRF / XML 脆弱性対策、HTTP レスポンスサイズ制限など安全設計
- ニュース NLP（LLM を用いたセンチメント）
  - 銘柄単位に複数記事を統合して gpt-4o-mini によるセンチメント採点（score_news）
  - レスポンス検証・クリップ・バッチ処理・リトライを実装
- 市場レジーム判定
  - 日経225 連動 ETF (コード 1321) の 200 日 MA とマクロニュースセンチメントを合成して市場レジームを判定（score_regime）
- リサーチ用ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出して QualityIssue を返す
- 監査ログ（Audit）
  - signal / order_request / executions の監査テーブル作成・初期化機能（init_audit_schema / init_audit_db）
- 設定管理
  - .env / 環境変数から設定を読み込み（自動ロード機能、テスト用に無効化可能）

---

## 動作要件（概略）

- Python 3.10+
- 必要な主なライブラリ（pip インストール例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで動作するユニットも多数）

※ 実運用ではネットワーク接続（J‑Quants / OpenAI）、DuckDBファイルの永続化、各種 API キーが必須です。

---

## インストール

ローカル開発環境例:

1. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. 開発パッケージとしてインストール（プロジェクトルートで）
   - pip install -e .

（プロジェクトには setup/pyproject 設定がある想定です。パッケージ配布方法に合わせて調整してください）

---

## 環境変数 / .env について

kabusys/config.py が起動時にプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（CWD ではなくパッケージファイル位置からプロジェクトルートを探索）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数（.env に設定）:

- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション等の API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime などで利用）

オプション / デフォルト値:

- KABUSYS_ENV — 環境 (development / paper_trading / live)。デフォルト: development
- LOG_LEVEL — (DEBUG/INFO/WARNING/ERROR/CRITICAL)。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite （モニタリング用、デフォルト: data/monitoring.db）

.env の書式は一般的な KEY=VALUE に対応し、export プレフィックスやクォートを取り扱います。

---

## 簡単な使い方（コード例）

下記は基本的な呼び出し例です（すべて Python スクリプトで実行）。

- DuckDB 接続の作成
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL の実行
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026,3,20))
  - print(result.to_dict())

- ニュースのスコアリング（AI）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要

- 監査 DB 初期化（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

- リサーチ関数例
  - from kabusys.research.factor_research import calc_momentum
  - from datetime import date
  - momentum = calc_momentum(conn, target_date=date(2026,3,20))

- 設定参照
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token
  - is_live = settings.is_live

注意点:
- OpenAI / J‑Quants の API 呼び出しを行う機能はネットワーク呼び出しとレート制限・課金が発生します。ローカルでのテストはモック化を推奨します（モジュール内の _call_openai_api, _urlopen 等はテストで差し替えられるよう設計されています）。
- 各関数はルックアヘッドバイアスを避けるため内部で date.today() を直接参照しない設計になっています。必ず target_date を明示するか、期待される挙動を確認してください。

---

## ディレクトリ構成（主要ファイル・概要）

- src/kabusys/
  - __init__.py — パッケージ初期化（__version__=0.1.0）
  - config.py — 環境変数 / .env の読み込みと Settings クラス
  - ai/
    - __init__.py — ai パッケージ公開関数
    - news_nlp.py — ニュース → 銘柄別センチメント計算（score_news）
    - regime_detector.py — ETF MA とニュースを合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J‑Quants API クライアント（取得/保存ロジック）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集・正規化・保存
    - calendar_management.py — 市場カレンダー操作（is_trading_day 等）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ初期化 / DB 初期化
  - research/
    - __init__.py — 研究用ユーティリティの公開
    - factor_research.py — モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリなど

各モジュールは設計コメント（docstring）に処理フローや設計方針、フェイルセーフ挙動が詳述されています。コードは DuckDB 接続を引数に取る関数群（副作用が明示）で構成されており、テストやシミュレーションで扱いやすく設計されています。

---

## 開発上の注意 / トラブルシューティング

- 環境変数が不足していると Settings のプロパティで ValueError が発生します。必須変数は .env.example を参考に .env を準備してください（*.example は本リポジトリに含める想定）。
- J‑Quants API はレート制限があります（120 req/min）。jquants_client は固定間隔の RateLimiter を用いて制御しますが、独自で大量の並列リクエストを行うと制約に達します。
- OpenAI の呼び出しはリトライ・バックオフ処理を備えていますが、API キーや課金設定に注意してください。
- テスト実行時は自動的に .env を読み込む挙動を無効化できます:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

この README はコードベースの利用開始ガイドです。さらに詳細な API 仕様や ETL の設定、運用手順（ジョブスケジューラ設定、監視・アラート、Slack 通知の例など）は別途ドキュメント（Operations.md / StrategyModel.md / DataPlatform.md 等）を参照してください。必要であれば README にサンプル .env.example や運用チェックリストを追加します。