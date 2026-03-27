KabuSys
=======

概要
----
KabuSys は日本株向けのデータパイプライン・リサーチ・自動売買基盤のコアライブラリです。本リポジトリは以下の主要機能を提供します。

- J-Quants API からのデータ ETL（株価日足・財務・JPX カレンダー）
- ニュース収集と LLM によるニュースセンチメント（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースを融合）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- データ品質チェックとカレンダー管理
- 監査ログ（signal → order → execution トレース）用の DuckDB スキーマ
- 各種ユーティリティ（統計、日付ユーティリティなど）

主な設計方針は「Look-ahead bias の回避」「DB による冪等保存」「外部 API 呼び出しのフェイルセーフ／リトライ制御」「テストしやすさ（API 呼び出しの差し替え可能）」です。

機能一覧
--------
- data/
  - jquants_client.py: J-Quants API クライアント（取得/保存/認証/リトライ/レート制御）
  - pipeline.py / etl.py: 日次 ETL パイプライン（差分取得、保存、品質チェック）
  - news_collector.py: RSS 取得・前処理・raw_news への保存（SSRF 対策、サイズ制限）
  - calendar_management.py: JPX カレンダー管理、営業日判定・next/prev_trading_day 等
  - quality.py: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit.py: 監査ログテーブルの DDL と初期化ユーティリティ
  - stats.py: z-score 正規化等の統計ユーティリティ
- ai/
  - news_nlp.py: ニュースを銘柄ごとに集約し OpenAI でスコアリング（JSON Mode、バッチ/リトライ）
  - regime_detector.py: ETF(1321)の MA200 乖離とマクロニュースセンチメントを統合して市場レジームを判定
- research/
  - factor_research.py: モメンタム・バリュー・ボラティリティ等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC（スピアマンランク相関）、統計サマリー等
- config.py: 環境変数／.env 自動読み込み、Settings オブジェクトによる設定取得
- その他ユーティリティ: data/schema 初期化や DB 関連ユーティリティ等

セットアップ手順
----------------
前提
- Python 3.9 以上（プロジェクトの実装で typing の新機能を使用しているため推奨）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン
   - git clone ... （プロジェクトルートには pyproject.toml や .git が存在すると自動で .env を読み込みます）

2. 仮想環境を作成してアクティブ化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .                # パッケージを編集可能モードでインストールする場合
   - もしくは必要最小限:
     - pip install duckdb openai defusedxml

   （requirements.txt / pyproject.toml が提供されている場合はそちらを使用してください）

4. 環境変数 / .env を準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（config.py により .git または pyproject.toml を基準に探索）。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

.env に設定すべき主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx    # J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY=sk-xxxx...                 # OpenAI API キー（AI 機能を使う場合必須）
- KABU_API_PASSWORD=...                     # kabuステーション API パスワード（発注周りを使う場合）
- SLACK_BOT_TOKEN=...                       # Slack 通知を行う場合
- SLACK_CHANNEL_ID=...                      # Slack 通知チャンネルID
- DUCKDB_PATH=data/kabusys.duckdb            # DuckDB データファイルパス（デフォルト）
- SQLITE_PATH=data/monitoring.db             # 監視用 SQLite（必要なら）
- KABUSYS_ENV=development|paper_trading|live # 実行環境（デフォルト development）
- LOG_LEVEL=INFO|DEBUG|...                  # ログレベル（デフォルト INFO）

使い方（簡易サンプル）
--------------------

1) ETL（日次パイプライン）を実行する
- ETL は DuckDB 接続を受け取り run_daily_etl を実行します。例:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- run_daily_etl はカレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック の順で実行し ETLResult を返します。

2) ニューススコアリング（OpenAI 必須）
- news_nlp.score_news は raw_news / news_symbols テーブルを参照して ai_scores テーブルへ書き込みます。

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("scored:", n_written)

- 注意: OpenAI 呼び出しはリトライを行いますが、テスト時は kabusys.ai.news_nlp._call_openai_api をモックして差し替えられます。

3) 市場レジーム判定
- regime_detector.score_regime を利用して market_regime テーブルに日次判定を保存できます。

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で指定

4) 監査ログ（監査DB）の初期化
- audit.init_audit_db により監査用 DuckDB を初期化できます。

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")

5) カレンダー操作 / 営業日判定
- calendar_management モジュールの is_trading_day / next_trading_day / get_trading_days 等を利用できます。

6) 研究用ユーティリティ
- research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary 等を使ってファクター研究や検証ができます。

ディレクトリ構成
----------------
（主要なファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - etl.py (公開 re-export)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*（ユーティリティのエクスポート）
- その他ユーティリティ（monitoring / execution / strategy 等はパッケージ公開対象に含まれます）

運用上の注意点
--------------
- 環境変数管理:
  - config.py はプロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数優先）。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。
- OpenAI の呼び出し:
  - news_nlp/regime_detector は gpt-4o-mini を想定（JSON Mode）。API レスポンスのパース失敗や API エラーはフェイルセーフでスコアを 0 にフォールバックする設計です。
  - テストでは内部の _call_openai_api をモックしてください。
- J-Quants:
  - jquants_client はリフレッシュトークンから id_token を取得しページネーション／リトライ／レート制御を行います。JQUANTS_REFRESH_TOKEN を必ず設定してください。
- Look-ahead Bias:
  - 各 AI/ETL/研究モジュールは datetime.today()/date.today() を直接参照しないよう設計されています。バックテスト等で意図せぬ未来データ参照が発生しないよう注意されています。
- DuckDB バージョン差異:
  - 一部の executemany 空リストの動作や ANY バインドの扱いなどでバージョン依存が想定されるため、DuckDB の互換性に注意してください（README のコードは DuckDB 0.10 系に配慮した実装が行われています）。

開発・テスト
-------------
- OpenAI や J-Quants への実際のネットワークリクエストを発生させたくない単体テストでは、モジュール内の _call_openai_api、jquants_client._request、news_collector._urlopen 等をモックしてください。
- ETL の各ステップはエラーを捕捉して継続する設計なので、部分的にモックして統合テストを行うことが容易です。

ライセンス・貢献
----------------
- この README はコードベースの説明用テンプレートです。実際のライセンスやコントリビューションガイドが別途ある場合はそちらを参照してください。

以上が KabuSys の簡易 README です。必要であれば、実行スクリプト例（CLI）や .env.example のテンプレート、よくあるトラブルシューティング項目（OpenAI レート制限対策、J-Quants 認証失敗時の対処など）を追加で作成します。どの情報を優先して追加しますか？