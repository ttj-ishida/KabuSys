# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）・ETL・データ品質チェック・ニュース収集とNLPスコアリング・市場レジーム判定・監査ログ（トレーサビリティ）など、運用に必要な機能群を提供します。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPXマーケットカレンダーを差分取得・保存（冪等）
  - 日次ETLパイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを順次実行
- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付不整合（未来日付・非営業日データ）検知
  - QualityIssue オブジェクトで問題を集約
- ニュース収集
  - RSS 取得・前処理（URL除去・正規化・SSRF対策）・raw_news への冪等保存
- ニュースNLP（LLM）
  - OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価（ai_scores へ書込）
  - チャンク処理、JSON Mode 応答バリデーション、リトライ・フェイルセーフ設計
- 市場レジーム判定
  - ETF(1321)の200日MA乖離（70%）とマクロニュースのLLMセンチメント（30%）を合成して日次レジーム判定（bull / neutral / bear）
  - LLM呼び出しのリトライ/フォールバック処理
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査スキーマを提供
  - init_audit_schema / init_audit_db で初期化可能
- 研究用ユーティリティ
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）、将来リターン計算、IC計算、Zスコア正規化（data.stats 経由）

---

## 必要条件（主な依存パッケージ）

- Python 3.9+
- duckdb
- openai
- defusedxml

（実行環境によって追加の依存が必要になる場合があります。pyproject.toml / requirements.txt を参照してください）

---

## 環境変数 / 設定

パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただし、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます）。

必須環境変数（Settings クラスで参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token で使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（実取引連携時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

その他設定:
- KABUSYS_ENV — 実行環境。allowed: `development`, `paper_trading`, `live`（デフォルト: development）
- LOG_LEVEL — ログレベル（`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: `data/monitoring.db`）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

設定は `from kabusys.config import settings` で参照できます。

注意:
- 自動.env読み込みはプロジェクトルート（.gitまたはpyproject.tomlの親）を基準に行います。
- 自動ロードが不要なテスト時などは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用してください。

---

## セットアップ手順

1. リポジトリをクローン（適宜）
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. インストール
   - 開発環境であれば（プロジェクトルートに pyproject.toml がある想定）:
     ```
     pip install -e .
     ```
   - 最低限必要なパッケージを直接インストールする場合:
     ```
     pip install duckdb openai defusedxml
     ```
4. .env を作成
   - リポジトリに `.env.example` がある場合はそれを参考に `.env` を作成。
   - 必須トークン（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_* など）を設定してください。

5. データベース用ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 基本的な使い方（例）

以下はライブラリの代表的な機能呼び出し例です。実運用ではログ設定や例外処理、APIキー管理を行ってください。

- DuckDB 接続を用意する:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーが環境変数にある前提）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026,3,20))
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査DB（監査用 DuckDB）初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ユーティリティ例（モメンタム計算）:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  ```

- 設定参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

テストのヒント:
- OpenAI API 呼び出しは内部の _call_openai_api をモックしてテストできます（例: unittest.mock.patch）。
- 自動.env読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## ログ / 実行環境

- ログレベルは `LOG_LEVEL` で設定（デフォルト：INFO）。
- 実行環境は `KABUSYS_ENV`（development, paper_trading, live）で切替。`settings.is_live` / `is_paper` / `is_dev` を参照可能。

---

## 主要ディレクトリ構成（src/kabusys の抜粋）

- kabusys/
  - __init__.py (パッケージのエントリ、version: 0.1.0)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースのLLMスコアリング、score_news)
    - regime_detector.py (市場レジーム判定、score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、fetch_* / save_*)
    - pipeline.py (ETL パイプライン、run_daily_etl 他)
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py (RSS 収集・前処理)
    - calendar_management.py (マーケットカレンダー管理、営業日判定)
    - quality.py (データ品質チェック、run_all_checks)
    - stats.py (zscore_normalize 等)
    - audit.py (監査ログスキーマと初期化)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum, calc_value, calc_volatility)
    - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)
  - ai/、research/、data/以外に strategy/, execution/, monitoring/ が想定（戦略・発注・監視用モジュール）

（上記は提供されているコードファイルの主要部分の説明です）

---

## 運用上の注意点 / 設計上の考慮

- Look-ahead bias 回避のため、モジュールは基本的に date / target_date を引数で受け取り、内部で date.today() を安易に参照しない実装になっています。
- OpenAI（LLM）呼び出しはリトライ・フェイルセーフ（失敗時はスコアを 0 にフォールバック）を備えていますが、APIキー・課金・レート制限に注意してください。
- J-Quants API のレート制限（120 req/min）は RateLimiter により制御されています。認証（id_token）自動リフレッシュやページネーション対応も実装済み。
- DuckDB への書き込みは基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識した設計です。
- ニュース収集では SSRF・XML脆弱性・過大レスポンス対策（リダイレクト検査、defusedxml、サイズ上限）を実装しています。

---

## 開発・テスト時のポイント

- 自動で .env を読み込む処理は config._find_project_root を基に行われます。パッケージ配布後も動作するよう CWD に依存しない設計です。
- テストでは外部API呼び出し（J-Quants / OpenAI / HTTP）をモックして単体テストを作成してください。
- DuckDBはインメモリ(":memory:")でも利用可能なため、単体テストで DB を分離して実行できます。
- news_nlp や regime_detector の _call_openai_api 関数はモック可能に実装されています。

---

## 貢献・ライセンス

（この README はリポジトリ内のコードから自動的にまとめた初期ドキュメントです。実運用での導入・配布にあたっては pyproject.toml / LICENSE / CONTRIBUTING.md などを追加してください。）

---

以上が本コードベースの概要と基本的な使用方法です。必要であれば、各モジュールの詳細な API 使用例（より具体的なコード例やユースケース）や、.env.example のテンプレート、サンプル ETL 実行スクリプト等を追加で作成します。どの部分を詳しく知りたいか教えてください。