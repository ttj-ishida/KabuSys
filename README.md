KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータパイプライン・リサーチ・AI解析・監査（トレーサビリティ）を含む
自動売買支援ライブラリです。J-Quants（株価／財務／カレンダー）や OpenAI を利用した
ニュースセンチメント評価、ファクター算出、ETL バッチ処理、監査ログ（約定トレース）などを提供します。

主な特徴
--------
- データ取得・ETL
  - J-Quants API 経由で株価（日足）、財務データ、JPX カレンダー等を差分取得・保存（DuckDB）
  - 差分更新 / バックフィル機構、ページネーション、レート制限・リトライ制御を実装
- ニュース / AI
  - RSS 収集（SSRF 対策、トラッキング除去）と記事前処理
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）スコアリング
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定
- 研究・ファクター
  - モメンタム、バリュー、ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクターの統計サマリ
- 品質管理・監査
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal → order_request → execution）テーブル定義と初期化ユーティリティ
- 設定管理
  - .env（プロジェクトルート）自動読み込み（.env.local 優先）と環境変数
  - KABUSYS_ENV（development / paper_trading / live）やログレベル制御

セットアップ
------------
前提
- Python 3.10 以上（型注釈に | 演算子を使用）
- 仮想環境の使用を推奨

例: 簡易インストール
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージ（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）
3. パッケージを開発モードでインストール（プロジェクトルートに pyproject.toml / setup がある場合）
   - pip install -e .

環境変数（.env）
- プロジェクトルート（.git または pyproject.toml を探索）にある .env を自動読み込みします。
  読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な environment keys（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- KABU_API_PASSWORD: kabuステーション API を使用する場合のパスワード
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知設定（任意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視等に使用, デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

使い方（代表的な例）
-------------------

1) 設定確認
from kabusys.config import settings
print(settings.duckdb_path)  # DUCKDB のパスや他の設定を確認

2) DuckDB 接続を作り ETL 日次処理を実行
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

3) OpenAI を用いたニューススコアリング（銘柄別）
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")

4) 市場レジーム判定
from datetime import date
from kabusys.ai.regime_detector import score_regime
count = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

5) ファクター計算 / 研究ユーティリティ
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.data.stats import zscore_normalize

moms = calc_momentum(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
normalized = zscore_normalize(moms, ["mom_1m", "mom_3m", "mom_6m"])

6) 監査ログ（初期化）
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db(settings.duckdb_path)  # 指定 DB に監査スキーマを追加

注意事項・トラブルシューティング
--------------------------------
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN）が未設定だと settings プロパティを参照した際に ValueError が発生します。
- OpenAI を利用する機能（score_news / score_regime 等）は OPENAI_API_KEY が必要です。関数に api_key を明示的に渡すことも可能です。
- J-Quants API はレート制限があり、内部でスロットリングとリトライを実装しています。大量の同時呼び出しは避けてください。
- DuckDB に対する executemany の空リストバインドはバージョン依存の挙動があるため、本ライブラリは空チェックを行っています。DuckDB のバージョン互換性に注意してください。
- RSS 収集は SSRF 対策・レスポンスサイズ制限を実装していますが、運用時は信頼できるソースのみを追加してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       # 環境設定・.env 自動読み込み
- ai/
  - __init__.py
  - news_nlp.py                    # ニュースセンチメント（銘柄別）
  - regime_detector.py             # 市場レジーム判定（ETF MA + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py              # J-Quants API クライアント / DuckDB 保存
  - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
  - etl.py                         # ETL 結果型のエクスポート（ETLResult）
  - calendar_management.py         # 市場カレンダー管理・営業日ロジック
  - news_collector.py              # RSS 取得・前処理（SSRF 対策）
  - stats.py                       # 汎用統計ユーティリティ（zscore 正規化）
  - quality.py                     # データ品質チェック
  - audit.py                       # 監査ログスキーマ定義 / 初期化
- research/
  - __init__.py
  - factor_research.py             # モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py         # 将来リターン / IC / 統計サマリー
- monitoring/ (※モジュール一覧に含めているが該当ファイルはここに配置想定)
- strategy/, execution/            # 戦略・発注モジュール（パッケージ構成に含める想定）

（上記は主要なモジュールの抜粋です。詳細はソースツリーを参照してください。）

開発・貢献
-----------
- 自動テスト、CI、依存関係定義（pyproject.toml / requirements.txt）を用意してください。
- 環境分離（development / paper_trading / live）を設定し、実運用時は live モードでの誤発注防止に注意してください。
- AI 呼び出しはコストが発生するため、ローカルテスト時はモック化してください（ソース内にモック差替えを想定した設計あり）。

最後に
-----
この README はソースコード（src/kabusys/*）の主要機能と使用方法をまとめた概要です。具体的な API の引数・戻り値や詳細な運用手順は各モジュールの docstring（ソース内コメント）を参照してください。必要であれば、セットアップ用のサンプル .env.example やコマンドラインツールの説明を追加しますので指示ください。