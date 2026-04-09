# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）によるセンチメント、研究用ファクター計算、監査ログなどを含みます。

主な設計方針は「バックテストでのルックアヘッドバイアス回避」「DuckDB を中核とした冪等な ETL」「外部 API 呼び出しの堅牢なリトライ処理」「監査性の高い発注トレーサビリティ」です。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ヘルパ
- データ取得 / ETL
  - J-Quants API クライアント（ページネーション・トークン自動リフレッシュ・レートリミット）
  - 日次 ETL（株価、財務、マーケットカレンダー）
  - 差分更新・バックフィル機能
- データ品質チェック
  - 欠損、スパイク、重複、将来日付・非営業日チェック
  - QualityIssue による問題一覧化
- ニュース収集
  - RSS フィード取得・前処理（URL 正規化・SSRF 対策・XML ハードニング）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントをバッチで評価し ai_scores に保存（gpt-4o-mini）
  - レスポンスバリデーション、リトライ、スコアクリップ
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離 + マクロニュースセンチメントを合成して日次レジーム判定
  - レジームを market_regime に保存
- 研究用モジュール
  - モメンタム / バリュー / ボラティリティ等のファクター算出
  - 将来リターン計算、IC（スピアマン）計算、ファクターサマリ
  - z-score 正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査スキーマ定義・初期化
  - 監査DBを DuckDB で初期化するユーティリティ

---

## 必要条件（例）

- Python 3.10 以上（型ヒントに | を使用）
- 主な依存パッケージ（インストールしないと動作しない主なもの）
  - duckdb
  - openai
  - defusedxml

（実際はプロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

---

## セットアップ手順

1. レポジトリをクローン / プロジェクトルートへ移動

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトの pyproject.toml / requirements.txt があればそれを使用）

4. パッケージを編集可能インストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env / .env.local を置くと、自動で読み込まれます（起動時）。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

6. 必要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=<J-Quants リフレッシュトークン>  （必須：データ ETL 用）
   - KABU_API_PASSWORD=<kabu API パスワード>  （発注周り）
   - OPENAI_API_KEY=<OpenAI API キー>  （news_nlp / regime_detector）
   - LINE_CHANNEL_ACCESS_TOKEN=<任意：通知用>
   - LINE_USER_ID=<任意：通知先>
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB, デフォルト data/monitoring.db）
   - PAPER_FILL_MODE（paper_trading 時のモック挙動: instant|partial|never|reject）

---

## 使い方（簡単な例）

以下はライブラリを使う最小の Python スクリプト例です（DuckDB 接続を作って ETL を実行、ニューススコア、レジーム判定を呼ぶ）。

- ETL（日次実行）：

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- news_nlp でニューススコアを付ける：

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で OPENAI_API_KEY を参照
  print(f"scored {count} codes")

- 市場レジーム判定：

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査DB初期化（監査用 DuckDB ファイル作成）：

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続

注意点：
- news_nlp と regime_detector は OpenAI を呼ぶため OPENAI_API_KEY が必要です。テスト環境では内部の _call_openai_api をモックできます（ユニットテスト向けに差し替えが可能）。
- ETL や保存処理は冪等性を保つよう実装されています（ON CONFLICT DO UPDATE 等）。

---

## 自動 .env ロードの挙動

- 実行時に環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていない場合、パッケージ初期化時にプロジェクトルートを探します（.git または pyproject.toml を探索）。見つかればそのディレクトリの .env を読み込み、続けて .env.local を上書き読み込みします。
- OS の環境変数は上書きされません（.env.local に override=True ではあるが protected によって OS 環境変数は保護されます）。
- .env ファイルのパースはシンプルながらクォートやコメント、export キーワードに対応しています。

---

## 主要モジュールとディレクトリ構成

プロジェクトの主要なファイル群（抜粋）：

- src/kabusys/
  - __init__.py
  - config.py  — 環境設定 / 自動 .env ロード / Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py  — ニュースセンチメント解析、score_news
    - regime_detector.py  — MA + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント、fetch_* / save_* 関数
    - pipeline.py  — run_daily_etl、個別 ETL ジョブ
    - etl.py  — ETLResult の再エクスポート
    - news_collector.py  — RSS 取得・前処理・保存
    - calendar_management.py  — market_calendar の操作、営業日判定
    - quality.py  — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py  — zscore_normalize 等の統計ユーティリティ
    - audit.py  — 監査スキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py  — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py  — forward returns, IC, factor_summary, rank

（上記はコードベースの主要ファイルを抜粋した構成です。実際のリポジトリでは他のユーティリティやテストが含まれる場合があります）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須：ETL）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注周り）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- PAPER_FILL_MODE — paper_trading 用のモック埋め方（instant|partial|never|reject）
- KABUSYS_ENV — environment: development | paper_trading | live
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値がセットされていれば無効）

.env.example を作って上記を設定して運用してください。

---

## テスト & モック向けの注記

- OpenAI 呼び出しは内部で _call_openai_api を通して行われます。テストでは unittest.mock.patch などでこれらの関数を差し替えて API 呼び出しをモックできます（news_nlp._call_openai_api、regime_detector._call_openai_api 等）。
- jquants_client の HTTP 呼び出しは urllib を使用しており、get_id_token / _request の振る舞いはエラーリトライや 401 の自動リフレッシュを想定した実装になっています。ユニットテストではモジュール関数をモックしてください。
- DuckDB への書き込みは executemany を使用する箇所があり、DuckDB のバージョン互換性に注意（コード内に互換性対策あり）。

---

## ライセンス / 責務

この README はコードベースから自動生成したドキュメントです。実際の運用では各 API キー・トークンの管理、責任ある取引運用、法規準拠を必ず確認してください。

---

質問や使い方の具体的なサンプル（ETL スケジューリング、発注フロー統合、バックテストでの活用方法など）が必要であれば、目的に合わせたサンプルコードを提供します。どの部分を詳しく知りたいか教えてください。