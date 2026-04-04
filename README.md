KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータプラットフォームとリサーチ / 自動売買基盤のライブラリ群です。  
主に次を目的としています。

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- ETL パイプラインによる差分取得・保存・品質チェック
- ニュース収集と LLM によるニュースセンチメント評価（OpenAI）
- 市場レジーム判定（ETF MA + マクロニュース）
- リサーチ用ファクター計算・特徴量分析ユーティリティ
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- データ品質チェック、マーケットカレンダー管理 等

設計上の特徴:
- DuckDB をストレージに利用（ローカルファイルまたはインメモリ）
- OpenAI（gpt-4o-mini）を JSON Mode で呼び出す設計（リトライ・フェイルセーフ）
- Look-ahead bias を避ける設計（内部で date.today()/datetime.now() を直接参照しない箇所が多い）
- API 呼び出しにはリトライ・レート制御・トークンリフレッシュを実装
- ETL/保存は冪等に設計（ON CONFLICT DO UPDATE 等）

主な機能一覧
--------------
- data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline: 日次 ETL（市場カレンダー・株価・財務・品質チェック）
  - calendar_management: JPX カレンダー管理・営業日計算
  - news_collector: RSS からのニュース収集と保存（SSRF 対策・正規化）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal_events / order_requests / executions の初期化）
  - stats: 汎用統計ユーティリティ（z-score 正規化 等）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成し ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF MA とニュースセンチメントを合成して market_regime に保存
- research
  - factor_research: momentum / value / volatility のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリ、ランキング

セットアップ手順
----------------

必要条件（推奨）
- Python 3.10+
- ネットワークアクセス（J-Quants / OpenAI へアクセスする場合）

推奨パッケージ（例）
- duckdb
- openai
- defusedxml

例: 仮想環境作成・インストール
- Unix/macOS:
  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install duckdb openai defusedxml

パッケージとしてインストール（開発モード）
  pip install -e .

環境変数 / .env
- このプロジェクトは .env / .env.local / OS 環境変数から設定を読み込みます。
  読み込み優先度: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にする場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時）
- KABU_API_PASSWORD: kabu ステーション連携用パスワード（使用する場合）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- 各種監視閾値や PID ファイルパスも .env で設定可能（config.Settings を参照）

使い方（簡単な例）
-----------------

共通: DuckDB 接続
from datetime import date
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL を実行する
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースのセンチメントを評価して ai_scores に保存
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")

3) 市場レジーム判定（market_regime に保存）
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須（または api_key 引数）

4) ファクター計算 / リサーチユーティリティ
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))

normed = zscore_normalize(moms, columns=["mom_1m", "mom_3m", "mom_6m"])

5) 監査ログ（監査 DB）の初期化
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" でも可

注意点・運用時のヒント
- OpenAI 呼び出しはリトライやフェイルセーフを備えていますが、API キー・コストに注意してください。
- J-Quants API はレート制限（120 req/min）に合わせた RateLimiter を実装しています。大量取得は時間を要します。
- ETL は差分取得・バックフィル戦略を持ち、品質チェックは Fail-Fast ではなく問題を収集して返します。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用すると良いです。
- DuckDB executemany は空リストを渡すと問題になるバージョンがあります（コード内でガードしていますが運用DBバージョンに注意）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定管理（Settings）
- ai/
  - __init__.py
  - news_nlp.py                    — ニュース NLP（score_news）
  - regime_detector.py             — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント（fetch/save）
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - etl.py                         — ETLResult の再エクスポート
  - calendar_management.py         — マーケットカレンダー管理
  - news_collector.py              — RSS ニュース収集
  - quality.py                     — データ品質チェック
  - stats.py                       — 統計ユーティリティ（zscore_normalize）
  - audit.py                       — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py             — ファクター計算（momentum/value/vol）
  - feature_exploration.py         — 将来リターン・IC・統計サマリ等

ライセンス / 貢献
-----------------
この README はコードベースに基づく概要ドキュメントです。実際のライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

フィードバック・改良案
--------------------
不整合や機能追加の提案、ドキュメント改善などあれば issue / PR を歓迎します。README に記載して欲しいサンプルや運用手順があればお知らせください。