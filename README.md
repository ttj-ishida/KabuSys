KabuSys — 日本株 自動売買 / データプラットフォーム
=================================================

概要
----
KabuSys は日本株向けのデータ収集・ETL・品質チェック・研究用ファクター計算・ニュース NLP（LLM）スコアリング・市場レジーム判定・監査ログ機能を備えたライブラリ群です。  
主に J-Quants API / RSS / OpenAI（gpt-4o-mini など）を利用してデータ基盤と研究ワークフローをサポートします。DuckDB をローカル DB として利用する設計です。

主な特徴
--------
- ETL パイプライン（株価/財務/市場カレンダー）の差分取得と冪等保存（J-Quants）
- ニュース収集（RSS）およびニュースの前処理（SSRF・サイズ制限・トラッキング除去）
- OpenAI を用いたニュースセンチメントのバッチスコアリング（JSON Mode, バックオフ付きリトライ）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの組合せ）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）と統計ユーティリティ（Zスコア等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）用スキーマ初期化ユーティリティ
- J-Quants クライアント：レート制限・トークン自動リフレッシュ・ページネーション対応

セットアップ手順
----------------

前提
- Python 3.10+（typing の "|" 演算子等を使用）
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）を利用する機能あり
- defusedxml（RSS パースの安全化）

例（仮想環境を作る場合）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合の最小例）
   - pip install duckdb openai defusedxml

3. パッケージを編集可能インストール（任意）
   - pip install -e .

環境変数 / .env
- パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 主な必要環境変数:
  - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
  - OPENAI_API_KEY        : OpenAI API キー（score_news/score_regime などで使用）
  - KABU_API_PASSWORD     : kabuステーション API パスワード
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : 監視通知用（必須）
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL

簡単な使い方（コード例）
------------------------

基本的に DuckDB 接続を作成し、各モジュールの関数を呼び出します。

1) 日次 ETL を実行する
- 取得・保存・品質チェックをまとめて実行します。

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースの NLP スコアリング（OpenAI 必須）
- raw_news / news_symbols / ai_scores を参照/更新します。

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print(f"scored: {count}")

3) 市場レジーム判定（MA200 + マクロセンチメント）
- ETF 1321 のデータと raw_news を参照し market_regime を更新

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数で指定

4) 監査ログデータベース初期化

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")

5) 研究用ファクター計算の例

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))

注意点 / 運用メモ
-----------------
- OpenAI 呼び出しや外部 API コールはネットワーク障害・429/5xx に対してリトライ・バックオフを実装していますが、API キーやネットワークが不安定な場合は処理が一部スキップされる可能性があります（フェイルセーフ設計）。
- ETL の差分取得は最終取得日とバックフィル日数を元に行われます。初回は過去開始日から全件取得する実装です。
- news_collector は RSS の SSRF 対策・サイズ制限・トラッキング除去等を行います。外部から提供するソース URL は https/http のみ許可されます。
- DuckDB への大量 INSERT は executemany/チャンク単位で行われ、冪等（ON CONFLICT）で更新します。
- .env の自動読み込みはプロジェクトルートを基準に行うため、実行場所に依存せずパッケージ配布後も正しく設定を読み込めるようになっています。

ディレクトリ構成（主要ファイル）
------------------------------
以下はパッケージ内主要モジュールの構成（src/kabusys 配下）です。実際のリポジトリでは他にテストや設定ファイルがあるかもしれません。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン / run_daily_etl 等
    - etl.py                  — ETL の公開インターフェース（ETLResult 再エクスポート）
    - jquants_client.py       — J-Quants API クライアント（取得/保存）
    - news_collector.py       — RSS ニュース収集
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（Zスコア）
    - calendar_management.py  — マーケットカレンダー管理（営業日判定など）
    - audit.py                — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py      — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー 等

開発 / テスト
--------------
- モジュールは外部 API を呼び出す箇所（OpenAI / J-Quants / URLopen 等）を設計上テストしやすく抽象化しており、ユニットテストでは該当関数をモックして動作を検証できます。
- 自動ロードされる .env をテスト時に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ライセンス・貢献
----------------
- この README 内ではライセンス情報を明示していません。実際のリポジトリの LICENSE ファイルを参照してください。  
- 貢献の際はコードスタイル・テスト・ドキュメントを追加してプルリクエストしてください。

問い合わせ / 補足
-----------------
- 実運用（ライブ発注等）に使う際は、kabuステーション API／証券会社の仕様・リスク・法令等を十分に理解し、安全性を担保する運用設計を行ってください。