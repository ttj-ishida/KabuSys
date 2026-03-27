KabuSys
=======

日本株向けのデータパイプライン・リサーチ・AI支援・監査機能を備えた自動売買プラットフォームのコアライブラリです。DuckDB をデータ層に使用し、J-Quants / JPY 市場カレンダー / RSS ニュース / OpenAI（LLM）などと連携してデータ取得・品質チェック・ファクター計算・AI スコアリング・監査ログ管理を行います。

主な目的
- データ取得（株価・財務・カレンダー）と ETL 自動化
- ニュースの NLP スコアリング（銘柄別センチメント）
- 市場レジーム判定（MA と LLM に基づく）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- データ品質チェックおよび監査ログ（トレーサビリティ）

機能一覧
- 環境設定読み込みと管理（kabusys.config）
  - プロジェクトルートの .env / .env.local を自動読み込み（必要に応じて無効化可）
  - 各種必須設定をプロパティ経由で取得
- データ取得 / ETL（kabusys.data.jquants_client, pipeline, etl）
  - J-Quants API 経由の株価・財務・上場情報・市場カレンダー取得（ページネーション・リトライ・レート制御）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - run_daily_etl による一括 ETL（カレンダー→株価→財務→品質チェック）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・正規化・前処理・raw_news への冪等保存
  - SSRF / Gzip / XML 攻撃対策やトラッキングパラメータ除去等の安全対策
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（急騰/急落）、日付不整合の検出
  - QualityIssue オブジェクトで検出結果を返す
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ
  - init_audit_db で監査専用 DuckDB を初期化
- AI（kabusys.ai）
  - score_news: 銘柄別ニュースセンチメントを OpenAI で評価して ai_scores に保存
  - score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM センチメント合成で市場レジーム判定
  - 再試行・フェイルセーフ・JSON Mode のレスポンスバリデーション等を実装
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン・IC（Information Coefficient）・統計サマリー
- 汎用統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize 等

セットアップ手順（ローカル開発環境）
- Python 環境
  - 推奨: Python 3.10+

1) 仮想環境作成（任意）
- macOS / Linux
  - python -m venv .venv
  - source .venv/bin/activate
- Windows
  - python -m venv .venv
  - .venv\Scripts\activate

2) 依存パッケージのインストール
- 必要な主なパッケージ例:
  - duckdb
  - openai
  - defusedxml
- 例:
  - pip install duckdb openai defusedxml

（プロジェクトに requirements.txt や pyproject.toml があればそちらを利用してください）

3) パッケージのインストール（開発モード）
- pip install -e .

4) 環境変数 / .env の準備
- プロジェクトルートに .env / .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 主な環境変数（最低限必要なもの）
  - JQUANTS_REFRESH_TOKEN=...       # J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD=...           # kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL=...           # 任意（デフォルト http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN=...             # Slack 通知用（必須）
  - SLACK_CHANNEL_ID=...            # Slack 通知先（必須）
  - OPENAI_API_KEY=...              # OpenAI を使う機能で必要
  - DUCKDB_PATH=data/kabusys.duckdb  # デフォルトの DuckDB ファイルパス
  - SQLITE_PATH=data/monitoring.db   # 監視用 SQLite（必要な場合）
  - KABUSYS_ENV=development|paper_trading|live
  - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

例（.env.example）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=your_openai_api_key
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

注意:
- settings は自動で .env/.env.local をロードしますが、環境やテストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings の必須プロパティは未設定時に ValueError を送出します。

基本的な使い方（簡単なコード例）
- DuckDB 接続の作成と ETL 実行

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニューススコアリング（OpenAI 必須）

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境に設定されているなら api_key 引数は省略可
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {count}")

- 市場レジーム判定

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB 初期化

from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_db = init_audit_db(Path("data/audit.duckdb"))
# 以降 audit_db を使って監査テーブルにアクセス可能

注意点 / 動作方針
- Look-ahead バイアス防止:
  - 日付計算は内部で datetime.today() を無作為に参照せず、呼び出し側から target_date を与える設計を推奨します。
  - ETL/run_daily_etl は target_date 引数を受け取ります（省略すると今日を使用）。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）に失敗してもシステムは完全停止せず、可能な限りフェイルセーフ（0.0 やスキップ）で続行します。ただし重要な設定がない場合は例外を投げます。
- 冪等性:
  - DuckDB への保存は基本的に ON CONFLICT DO UPDATE を利用し冪等になるよう設計されています。
- 外部リソース保護:
  - news_collector は SSRF 対策、gzip 上限、XML 脆弱性対策を備えています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュース NLP（score_news）
    - regime_detector.py           # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント + DuckDB 保存
    - pipeline.py                  # ETL パイプライン / run_daily_etl
    - etl.py                       # ETLResult 再エクスポート
    - news_collector.py            # RSS ニュース収集
    - calendar_management.py       # 市場カレンダー管理
    - quality.py                   # データ品質チェック
    - stats.py                     # 統計ユーティリティ（zscore_normalize）
    - audit.py                     # 監査ログ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           # ファクター計算（momentum/value/volatility）
    - feature_exploration.py       # 将来リターン / IC / 統計サマリ
  - (strategy, execution, monitoring)  # パッケージ外向けにエクスポートはあるが、実装は別途

追加情報 / 運用上のヒント
- J-Quants: レート制限（120 req/min）に合わせて内部でスロットリングを行います。大量取得時は pipeline の挙動を監視してください。
- OpenAI:
  - gpt-4o-mini を JSON Mode で利用する設計です。API 呼び出しの失敗や非期待レスポンスはログを出しスコアを 0.0 にフォールバックします。
  - テスト時は内部の _call_openai_api をモックして挙動を制御できます。
- ロギング:
  - settings.log_level プロパティでログレベル制御。各モジュールは標準 logging を利用しています。
- テスト:
  - 依存 API 呼び出し（OpenAI / J-Quants / HTTP）はモック可能なように設計されています（関数参照や内部ラッパーを差し替え）。

貢献 / 拡張
- strategy / execution / monitoring 層はバックテスト・実取引エンジンと連携するために拡張できます。監査テーブルを活用して発注/約定のトレーサビリティを確保してください。
- ニュースソースは news_collector.DEFAULT_RSS_SOURCES を拡張して追加できます。
- OpenAI モデルやプロンプトは ai/news_nlp.py, ai/regime_detector.py の定数を変更してカスタマイズ可能です。

ライセンス
- 本リポジトリ内にライセンス表記がない場合は、利用前にライセンス方針をプロジェクトオーナーに確認してください。

以上が KabuSys の概要と基本的な使い方です。具体的な運用手順や CI/CD、詳細なスキーマ（テーブル定義）などは別途ドキュメント（DataPlatform.md / StrategyModel.md など）を参照してください。必要であれば README に追記しますので、追加したい項目（例: API キーの取得手順、DB スキーマ一覧、デモ実行シナリオなど）を教えてください。