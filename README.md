# KabuSys — 日本株自動売買プラットフォーム（README）

簡潔な概要、機能、セットアップ手順、主要な使い方（コード例）、およびディレクトリ構成をまとめた README です。

注意：
- この README はリポジトリ内のソースコード（src/kabusys）をもとに作成しています。
- 実行には外部 API（J-Quants、OpenAI など）の認証情報が必要です。環境変数または .env ファイルで設定してください。

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームと研究／運用コンポーネント群を提供するライブラリです。主な目的は以下です。

- J-Quants API からの株価・財務・市場カレンダーなどの差分 ETL（DuckDB に保存）
- ニュース収集（RSS）・NLP（OpenAI）による銘柄別センチメント集約（ai_scores 保存）
- 市場レジーム判定（MA乖離 + LLM によるマクロセンチメント）
- 研究用ファクター（モメンタム・バリュー・ボラティリティ等）計算
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- 監査ログ（signal / order_request / execution）のスキーマ初期化ユーティリティ
- 各種セキュリティ／堅牢性対策（リトライ、レートリミット、SSRF 対策、フェイルセーフ）

パッケージ名: kabusys（src/kabusys）

---

## 機能一覧（ハイライト）

- データ取得・保存
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB への冪等保存（ON CONFLICT を利用）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- ニュース関連
  - RSS 収集（SSRF 防止、トラッキング除去、前処理）
  - LLM によるニュースセンチメント算出（gpt-4o-mini を利用想定）
  - 銘柄単位でのバッチ処理、結果を ai_scores に保存
- AI / レジーム判定
  - 市場レジーム判定（ETF 1321 の 200 日 MA 乖離とマクロセンチメントの合成）
  - OpenAI 呼び出しはリトライ・フォールバックあり（失敗時は中立スコア）
- 研究（research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン算出、IC 計算、統計サマリ（rank, factor_summary 等）
  - zscore_normalize（data.stats）
- データ品質
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）
  - QualityIssue データクラスで問題を収集
- 監査ログ
  - signal_events, order_requests, executions の DDL とインデックス定義
  - init_audit_schema / init_audit_db による初期化
- 設定管理
  - .env / .env.local からの環境変数読み込み（自動ロードは無効化可能）
  - settings オブジェクトで主要設定・パス取得（例: settings.duckdb_path）

---

## 必要条件 / 推奨環境

- Python 3.10+（型ヒントの union 演算子（|）等を使用）
- 必要な Python パッケージ（主なもの）:
  - duckdb
  - openai
  - defusedxml
  - 追加で標準ライブラリ以外の依存がある場合は適宜インストールしてください。

例（最小インストール）:
pip install duckdb openai defusedxml

※実運用ではバージョン固定（requirements.txt / poetry）を推奨します。

---

## 環境変数（.env）

config.py によって自動読み込みされる主要環境変数：

必須（実行する機能により必須のものは異なる）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知を使用する場合
- SLACK_CHANNEL_ID — Slack チャネル ID
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注等で使用）

オプション / デフォルトあり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動ロードを無効化
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — データ用 DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

注: .env.example がある想定で、そこを参考に .env を作成してください。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject の記載があればそれに従ってください:
   pip install -r requirements.txt / pip install -e .）

4. 環境変数の用意
   - プロジェクトルートに .env を作成（.env.local を併用可能）
   - 必須トークン（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）などを設定
   - 自動ロードは config.py が .git または pyproject.toml を探索して行います。
     テストや CI で自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. データディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 主要な使い方（コード例）

以下は Python REPL / スクリプトから利用する際の代表的な例です。DuckDB はファイルパスまたは ":memory:" をサポートします。

1) DuckDB 接続と ETL の実行（日次 ETL）:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))  # settings.duckdb_path を使ってもよい
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニューススコアリング（AI）を実行（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")

3) 市場レジーム判定（regime）:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーが必要

4) 監査 DB の初期化（監査ログ専用 DB）:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions のテーブルが作成されます

5) 研究用ファクター計算:

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))

6) データ品質チェック:

from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)

注意点:
- 各関数は Look-ahead bias を避ける設計になっており、内部で date.today() を参照しないものが多いです。必ず明示的な target_date を渡すことが想定されます（テスト・バックテスト・再現性確保のため）。
- OpenAI 呼び出しは回数課金が発生するため、本番環境では適切に制限してください。

---

## 実行に関する補足（設計上の挙動）

- 環境変数自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込みます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- J-Quants クライアント:
  - レート制限（120 req/min）を内部で制御します。
  - 401 エラー発生時はリフレッシュトークンで自動更新を試みます。
  - ページネーション対応・リトライロジックあり。

- ニュース収集:
  - RSS 取得時に SSRF 対策（ホストのプライベート判定、リダイレクト検査）を行います。
  - トラッキングパラメータ除去、最大レスポンスサイズ制限あり。

- OpenAI 呼び出し:
  - gpt-4o-mini（コード中のデフォルト）を使用する想定で JSON mode を使い、厳密な JSON 出力を期待します。
  - 再試行や 5xx の扱いなど、フェイルセーフ設計（失敗時は 0.0 の中立スコアにフォールバック）です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP スコアリング（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント & 保存ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集（fetch_rss 等）
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック
  - audit.py — 監査ログ DDL / 初期化（init_audit_schema, init_audit_db）
- research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
- data/（上記と同じ階層にあるモジュール群）

（実際のリポジトリにはさらにモジュールやユーティリティがある可能性があります）

---

## 開発 / 貢献 / テスト

- 開発時は仮想環境を使い、依存を明確にして実装・単体テストを行ってください。
- OpenAI / J-Quants API 呼び出しはネットワーク依存のため、ユニットテストではモック（unittest.mock.patch 等）を使用するよう各モジュールが想定されています（実装中のコメント参照）。
- 自動ロードされる .env の扱いに注意してください（テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定推奨）。

---

## 参考 / トラブルシューティング

- 環境変数が見つからない旨の ValueError が出る場合は .env の設定および環境変数を確認してください（config.Settings の _require による検証）。
- DuckDB の executemany で空リストを渡すと古いバージョンでは失敗することがあるため、コード側で空チェックが行われています。
- OpenAI の JSON パースに失敗する場合は LLM の出力が期待する JSON 構造になっているか確認してください（news_nlp, regime_detector ともにフォールバック処理あり）。

---

必要であれば、あなたのリポジトリの README.md に合わせて「実行スクリプト」「systemd ユニットの例」「CI 設定」「requirements.txt の候補」なども追記できます。どの情報を追加したいか教えてください。