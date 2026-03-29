# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータプラットフォームと自動売買基盤のライブラリ群です。  
データ取得（J-Quants 経由）、ETL、データ品質チェック、ニュース収集と NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（発注 → 約定のトレーサビリティ）などを含むモジュール群を提供します。

主な目的は、バックテスト・リサーチ環境と実運用（paper/live）を同一コードベースで安全に扱えるようにすることです。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（.env）
- 使い方（簡易サンプル）
- ディレクトリ構成
- 開発・運用上の注意

---

## プロジェクト概要

- データ収集: J-Quants API から株価（OHLCV）、財務、マーケットカレンダー、上場銘柄情報を取得。
- ETL: 差分取得・冪等保存（DuckDB）・品質チェックのパイプライン。
- ニュース収集: RSS から記事を収集し raw_news に保存、銘柄紐付け。
- ニュース NLP: OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア生成。
- 市場レジーム判定: ETF（1321）の MA200 乖離 + マクロニュースの LLM 評価を組み合わせて日次レジームを判定。
- 研究・ファクター: モメンタム／バリュー／ボラティリティなどのファクター計算、将来リターンと IC 分析。
- 監査ログ: signal → order_request → execution といったトレーサビリティ用テーブルを提供。
- 安全機構: SSRF 対策、XML パースの安全化、API リトライ・レート制御、ルックアヘッドバイアス対策など。

---

## 機能一覧（主要）

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）。
  - pipeline: 日次 ETL（run_daily_etl）・個別 ETL ジョブ（prices/financials/calendar）。
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）。
  - calendar_management: 市場カレンダーの判定・次営業日の計算等。
  - news_collector: RSS 収集、前処理、raw_news 保存（SSRF 対策あり）。
  - audit: 監査ログ（signal_events / order_requests / executions）初期化ユーティリティ。
  - stats: Zスコア正規化等の統計ユーティリティ。
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む。
  - regime_detector.score_regime: 市場レジーム（日次）を market_regime に書き込む。
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config: 環境変数管理（.env 自動ロード、必須設定チェック、環境・ログレベル判定）

注意: strategy / execution / monitoring パッケージがエクスポートされる設計になっています（将来的な戦略・発注・監視ロジックを想定）。

---

## 必要条件

- Python 3.10+
  - typing における | 演算子や forward reference を利用しています。
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS フィード）

実際の install 要件ファイル（requirements.txt / pyproject.toml）はプロジェクト配布物を参照してください。以下は最小の例です:

pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-dir>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください:
   pip install -r requirements.txt など）

4. 環境変数を準備
   - プロジェクトルート（pyproject.toml や .git がある階層）に `.env` を置くと自動ロードされます（ただしテスト等で無効化可能）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主要）

（必須と明示されているものを記載）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード（発注関連で使用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー（news_nlp, regime_detector で使用）
- KABUSYS_ENV (任意, default=development) — 有効値: development / paper_trading / live
- LOG_LEVEL (任意, default=INFO) — 有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意) — 1 をセットすると .env 自動ロードを無効化

例（.env）:
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=passwd
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

.env のパースは config モジュール独自実装で、コメントやクォート、export 形式にも対応します。

---

## 使い方（簡易サンプル）

以下は最小限の実行例です。適切な環境変数をセットし、DuckDB に接続して関数を呼びます。

- DuckDB に接続して日次 ETL を実行する例:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（ファイルパスは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- 監査 DB を初期化する例:

from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # 必要なら別ファイルを指定

- ニュース NLP スコアを生成する例:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を参照
print("written:", n_written)

- 市場レジーム判定の例:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を利用

- RSS フィードを取得する例:

from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["title"], a["datetime"], a["url"])

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数・設定管理
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP（score_news）
  - regime_detector.py            — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（fetch/save）
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - quality.py                    — データ品質チェック
  - calendar_management.py        — マーケットカレンダー管理
  - news_collector.py             — RSS 収集
  - audit.py                      — 監査ログ初期化・DB ユーティリティ
  - stats.py                      — 統計ユーティリティ（zscore_normalize）
  - etl.py                        — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py            — モメンタム / バリュー / ボラティリティ
  - feature_exploration.py        — 将来リターン, IC, summary, rank
- research/* その他
- (strategy/, execution/, monitoring/ はパッケージ公開の設計あり)

上記はコードベースの主要ファイルを抜粋したものです。詳細は src/kabusys 以下の各モジュールを参照してください。

---

## 開発 / 運用上の注意

- ルックアヘッドバイアス回避:
  - 多くのモジュールで date.today() を直接参照しない方針です。処理は引数で target_date を受け取るよう設計されています。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定。API エラー・JSON 解析エラーはフェイルセーフでスコア 0.0 にフォールバックするなど耐障害性を考慮しています。
- J-Quants:
  - レート制限（120 req/min）を内部で制御。401 時はトークン自動リフレッシュを試みます。
- セキュリティ:
  - RSS 取得では SSRF 対策（ホストチェック・リダイレクト検査）および defusedxml を利用しています。
- DB 操作:
  - DuckDB への挿入は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を想定しています。
- テスト:
  - OpenAI / 外部ネットワーク呼び出しはモックしやすいよう設計されています（内部関数をパッチする想定）。

---

この README はコードベースの主要機能と初期セットアップ・使用方法の概要を示します。実際の運用では .env.example（プロジェクトに同梱されている場合）や pyproject.toml / requirements.txt を参照して、依存関係・起動スクリプトを確認してください。必要であれば、README に追記してほしいトピック（例: CI 設定、より詳細な ETL 運用例、監視/アラート設計）を教えてください。