# KabuSys

日本株向けの自動売買・データ基盤ライブラリ KabuSys のリポジトリ用 README（日本語）。

この README はソースコード（src/kabusys 以下）に基づき作成しています。実装の詳細や設計方針はコード内ドキュメントを参照してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／データプラットフォーム向けユーティリティ群です。主に以下の役割を持ちます。

- J-Quants API からのデータ取得（株価日足、財務、JPX カレンダー）
- RSS ニュース収集と NLP による銘柄センチメント評価（OpenAI）
- 市場レジーム判定（ETF とマクロニュースの合成）
- ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- Research 用ファクター計算／特徴量解析ユーティリティ

設計上の注意点として、ルックアヘッドバイアス防止、冪等性（Idempotency）、API リトライ・レートリミット対応、外部 API 呼び出しの失敗に対するフォールバックなどが組み込まれています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（jquants_client）
  - ETL パイプライン（data.pipeline.run_daily_etl 等）
  - カレンダー更新ジョブ（data.calendar_management.calendar_update_job）
- ニュース関連
  - RSS 収集（data.news_collector.fetch_rss）
  - ニュース NLP（ai.news_nlp.score_news） — OpenAI を使った銘柄別センチメント
- AI / Regime
  - 市場レジーム判定（ai.regime_detector.score_regime） — ETF + マクロニュース
- Research
  - ファクター計算（research.factor_research: momentum/value/volatility）
  - 将来リターン / IC / 統計集計（research.feature_exploration）
  - 正規化ユーティリティ（data.stats.zscore_normalize）
- 品質管理
  - データ品質チェック（data.quality.run_all_checks）
- 監査ログ
  - 監査スキーマ初期化 / DB 作成（data.audit.init_audit_schema / init_audit_db）

---

## 必要環境・依存パッケージ

- Python 3.10 以上（ソース内での型ヒントにより 3.10+ を想定）
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- その他 標準ライブラリ（urllib, datetime, json など）

（実際の setup.cfg / pyproject.toml に依存関係が定義されている想定です。開発環境では pip install -e . 等でインストールしてください。）

例:
- 仮想環境作成 & 開発インストール
  1. python -m venv .venv
  2. source .venv/bin/activate
  3. pip install -e .

---

## 環境変数・設定

自動読み込み:
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に利用する環境変数:
- J-Quants / データ系
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- kabuステーション API
  - KABU_API_PASSWORD : kabu API のパスワード（必須）
  - KABU_API_BASE_URL : kabu API ベース URL（省略可; デフォルト http://localhost:18080/kabusapi）
- Slack 通知
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- OpenAI（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY （関数呼び出し時に引数で渡すことも可能）
- DB パス（デフォルトを変更する場合）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用: data/monitoring.db）
- システム
  - KABUSYS_ENV : development | paper_trading | live（デフォルト development）
  - LOG_LEVEL : DEBUG/INFO/...（デフォルト INFO）

settings は kabusys.config.settings として利用可能です（プロパティにより必須チェックあり）。

サンプル .env（例）
- .env.example を参考に `.env` を作成してください。例（実際の値は置換してください）:
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - OPENAI_API_KEY=sk-...
  - KABU_API_PASSWORD=your_kabu_password
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=C01234567
  - DUCKDB_PATH=data/kabusys.duckdb
  - LOG_LEVEL=INFO
  - KABUSYS_ENV=development

---

## セットアップ手順（開発用）

1. リポジトリをクローン
   - git clone <repo>
2. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存インストール（プロジェクトルートで）
   - pip install -e .         # または pip install .（パッケージがひとつのパッケージとしてインストールされる想定）
   - pip install duckdb openai defusedxml
4. .env を作成（上記参照）
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL / スクリプト内での利用イメージです。各関数は詳細な引数を持つため、実運用時はログ・例外処理を適切に追加してください。

- DuckDB 接続の作成（settings に DUCKDB_PATH を設定している前提）
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を指定可能
  - print(result.to_dict())

- ニュースセンチメントスコア生成（OpenAI API キーは環境変数 OR api_key 引数で）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n_written = score_news(conn, target_date=date(2026, 3, 20))
  - print("書込み銘柄数:", n_written)

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20))

- 監査DB初期化（監査専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- カレンダー関連ユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  - is_trading = is_trading_day(conn, date(2026,3,20))

- Research / ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - momentum = calc_momentum(conn, target_date=date(2026,3,20))

注意: OpenAI を利用する関数（score_news, score_regime など）は API 呼び出しを行います。api_key を明示的に引数として渡すか、環境変数 OPENAI_API_KEY を設定してください。API 呼び出しはリトライやフォールバック（失敗時はスコア 0.0 など）を実装していますが、料金やレート制限には注意してください。

---

## ディレクトリ構成

（src/kabusys 配下の主要ファイル / モジュール）

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の自動読み込み・設定管理（settings）
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント解析 & ai_scores 書込み
  - regime_detector.py  — 市場レジーム判定（ETF + マクロニュース）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（取得・保存）
  - pipeline.py         — ETL パイプライン（run_daily_etl など）
  - calendar_management.py — 市場カレンダー管理
  - news_collector.py   — RSS 収集と前処理
  - quality.py          — データ品質チェック（欠損/スパイク/重複/日付不整合）
  - stats.py            — 汎用統計ユーティリティ（zscore_normalize 等）
  - etl.py              — ETL 公開インタフェース（ETLResult の再エクスポート）
  - audit.py            — 監査ログテーブル定義 / 初期化
- src/kabusys/research/
  - __init__.py
  - factor_research.py  — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー等

各モジュールはソース内に詳細な docstring（設計方針や処理フロー）があります。実装の挙動や戻り値は該当ファイルのドキュメントを参照してください。

---

## 設計上の重要ポイント（抜粋）

- ルックアヘッドバイアス防止: 各処理は target_date を明示的に受け取り、datetime.today() 等に依存しない設計が基本です。
- 冪等性: DB への保存は ON CONFLICT / DELETE→INSERT のパターンで上書きし、部分失敗時に既存データを不要に削除しないよう配慮しています。
- フェイルセーフ: 外部 API（OpenAI / J-Quants / RSS）失敗時は基本的に処理をスキップまたはフォールバックして継続します（例: macro_sentiment=0.0）。
- レート制御・リトライ: J-Quants は固定間隔スロットリングで 120 req/min を守る実装、OpenAI 呼び出しもリトライ実装があります。
- セキュリティ: RSS 取得時の SSRF 対策、defusedxml を使った XML パース等の防御を実装しています。

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートの判定は .git または pyproject.toml を基準に行われます。別の構成であれば環境変数を直接エクスポートするか、KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動でロードしてください。
- OpenAI 呼び出しの失敗
  - OPENAI_API_KEY が未設定だと ValueError が出ます。テスト時は関数の api_key 引数で鍵を渡すか、環境変数を設定してください。API の RateLimit 等はリトライで対処しますが、連続失敗はスキップして 0.0 を返す等のフォールバック動作になります。
- DuckDB のファイルが作成されない
  - settings.duckdb_path の親フォルダを作成してください（多くの初期化関数は親ディレクトリを自動作成しますが、パスの指定を確認してください）。

---

## ライセンス・貢献

この README はコード内コメントに基づくもので、実際のリポジトリの LICENSE ファイルや CONTRIBUTING ガイドラインをご確認ください。

---

必要であれば README を README.md 形式でファイルとして出力したり、具体的な例や簡易スクリプト（cron 向けの daily_etl ラッパー等）を追記します。どの部分を詳細化したいか教えてください。