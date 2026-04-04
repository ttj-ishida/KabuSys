# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群。J-Quants API などからデータを取得・保存し、ファクター計算・ニュースによる AI スコアリング・市場レジーム判定・ETL パイプラインや監査ログ（トレーサビリティ）等の機能を提供します。

主に DuckDB を内部データストアとして使用し、OpenAI（gpt-4o-mini 等）を利用したニュース NLP や市場レジーム判定を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 要件
- セットアップ手順
- 環境変数 (.env)
- 使い方（簡単なコード例）
- ディレクトリ構成（主要ファイル説明）
- 注意事項

---

## プロジェクト概要

KabuSys は以下を主眼に設計された Python ライブラリ群です。

- 市場データ（株価・財務・市場カレンダー）の差分 ETL（J-Quants 経由）
- ニュース収集・前処理・LLM による銘柄別センチメント付与
- 市場レジーム判定（ETF の MA とマクロニュースを合成）
- 研究用ファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）用スキーマの初期化・操作ユーティリティ

設計上の重要点：
- ルックアヘッドバイアスの回避（内部で date.today() 等を不用意に参照しない）
- DuckDB を使った SQL ベースの高性能処理
- OpenAI 呼び出しはリトライ・フォールバックロジックを備える
- ETL と品質チェックは段階的に実行し、部分失敗に強い

---

## 機能一覧

主な機能（モジュール別）
- kabusys.config
  - 環境変数 / .env 自動読み込み、Settings API
- kabusys.data
  - jquants_client: J-Quants API 呼び出し、DuckDB 保存（冪等）
  - pipeline: 日次 ETL（run_daily_etl 等）
  - calendar_management: 市場カレンダー管理、営業日判定ユーティリティ
  - news_collector: RSS 収集・前処理・保存（raw_news）
  - quality: データ品質チェック（欠損/スパイク/重複/日付不整合）
  - audit: 監査ログスキーマ初期化・監査 DB 用ユーティリティ
  - stats: zscore 正規化等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: 市場レジーム判定（bull/neutral/bear）を market_regime に書き込む
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 要件

最低動作環境（目安）
- Python 3.10+
  - （PEP 604 の `X | Y` 型注釈を使っているため 3.10 以上を推奨）
- 必須 Python パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml

インストール例（仮）:
pip install duckdb openai defusedxml

実際はプロジェクトの packaging / requirements.txt に合わせてインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（任意だが推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用）

4. パッケージとしてインストール（開発モード）
   pip install -e .

5. 環境変数を設定（下記を参照）。プロジェクトルートに .env / .env.local を置くと自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 環境変数 (.env) — 主要なキー

パッケージはプロジェクトルート（.git または pyproject.toml を含むディレクトリ）から .env / .env.local を自動ロードします（OS 環境変数を上書きしない既定の挙動）。.env.local は .env を上書き可能。

必須（ETL 実行などに必要）
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD
  - kabu ステーション API を使用する場合のパスワード（使用しない場面もあり）

OpenAI 関連
- OPENAI_API_KEY
  - news_nlp / regime_detector が使用（関数引数で上書き可能）
- その他
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知に使用する場合）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB: data/monitoring.db）
  - PID_FILE_PATH / KILL_FLAG_PATH / 各種監視閾値（CPU/MEM/DISK）
  - KABUSYS_ENV（development/paper_trading/live）
  - LOG_LEVEL（DEBUG/INFO/...）

サンプル (.env.example)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方

以下はライブラリを直接利用する簡単な例です。CLI は付属していないため、Python スクリプト / REPL から呼び出します。

- DuckDB 接続準備（デフォルトパスを settings から取得）
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュース NLP による銘柄別スコア付与
from kabusys.ai.news_nlp import score_news
from datetime import date
# OPENAI_API_KEY が環境変数に設定されているなら api_key 引数は省略可
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")

- 市場レジーム判定
from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DB 初期化（監査専用 DB を作る場合）
from kabusys.data.audit import init_audit_db
db_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます

- 研究モジュール例（モメンタム計算）
from kabusys.research.factor_research import calc_momentum
from datetime import date
mom = calc_momentum(conn, date(2026, 3, 20))
# 返り値は [{ "date": ..., "code": ..., "mom_1m": ..., ...}, ...]

基本的な利用手順
1. DuckDB 接続を用意する（settings.duckdb_path を参照）
2. run_daily_etl でデータを取り込む（または個別の run_prices_etl など）
3. 研究・AI スコアリング関数を呼び出す
4. 監査ログスキーマが必要なら init_audit_db / init_audit_schema を実行

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__）および公開モジュールリスト
- config.py
  - .env 自動読み込み、Settings クラス（環境設定の集中管理）
- ai/
  - __init__.py
  - news_nlp.py
    - ニュースの前処理・OpenAI による銘柄別センチメント評価・ai_scores テーブル書き込み
  - regime_detector.py
    - ETF 1321 の MA200 乖離とマクロニュースを合成して market_regime を書き込む
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得 / 保存 / 認証 / レート制御）
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）と ETLResult
  - calendar_management.py
    - 市場カレンダー管理、営業日判定ユーティリティ
  - news_collector.py
    - RSS 収集、正規化、保存（SSRF 対策や XML 安全対策含む）
  - quality.py
    - データ品質チェック（欠損/スパイク/重複/日付不整合）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - audit.py
    - 監査ログスキーマ定義 & 初期化ユーティリティ
  - etl.py
    - ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py
    - モメンタム・ボラティリティ・バリュー等の計算関数
  - feature_exploration.py
    - 将来リターン計算・IC 計算・統計サマリー等

---

## 注意事項 / 運用上のヒント

- OpenAI API キーは環境変数 OPENAI_API_KEY に設定してください。score_news / score_regime は api_key 引数で明示して上書きできます。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の API レート制限・認証仕様に基づいたリトライ/レートリミッタが実装されていますが、プロダクションでは API 利用ルールを遵守してください。
- DuckDB に対する executemany の空リスト渡しは一部バージョンで制約があるため、ライブラリ内部で空チェックを行っています。DuckDB バージョン互換性に注意してください。
- LLM（OpenAI）呼び出しは外部サービス依存であるため、API 失敗時はフェイルセーフ（スコア=0.0 等）で継続する設計です。運用時はログを監視してください。
- 研究用関数群（research/*）はバックテストや研究用途向けであり、本番環境の発注ロジックとは切り離して利用してください（Look-ahead バイアスに注意）。

---

必要に応じて README を拡張して、具体的な CLI スクリプト、Docker 化、CI 設定、詳細な .env.example、マイグレーション/スキーマ定義ファイル等を追加できます。必要であればそれらのテンプレートや手順も作成します。