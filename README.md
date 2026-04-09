README
=====

概要
---
KabuSys は日本株のデータ取得・品質管理・特徴量計算・ニュースNLP・市場レジーム判定・監査ログなどを備えた自動売買／リサーチ基盤の一部実装です。  
主に以下を目的とします。

- J-Quants API からの株価・財務・カレンダー取得（ETL）
- DuckDB ベースでのデータ保存・品質チェック
- ニュース記事の収集と OpenAI を用いた銘柄別センチメント算出
- マーケットレジーム判定（ETF + マクロニュース）
- 監査ログ（signal → order_request → executions）のスキーマ初期化
- 研究用ファクター（モメンタム／バリュー／ボラティリティ等）の計算・解析ユーティリティ

特徴
---
- DuckDB を用いた軽量で高速なオンディスク分析基盤
- J-Quants API に対するページネーション、レート制御、リトライ対応を備えたクライアント
- OpenAI（gpt-4o-mini）を JSON モードで呼び出すニュースNLP／レジーム判定ロジック（フェイルセーフ設計）
- ETL の差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
- 監査テーブル群の冪等的な初期化・DB 接続ユーティリティ
- 研究向けモジュール（ファクター計算・IC・前方リターン計算・Zスコア正規化）

前提／要件
---
- Python 3.10+
- 必要な主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS, OpenAI API）

（実行環境に合わせて pyproject / requirements.txt を用意してください。ここでは主要依存だけを列挙しています）

セットアップ手順
---
1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージをインストール
   - pip install -e .    （パッケージ化されている場合）
   - 必要ライブラリを個別にインストール:
     - pip install duckdb openai defusedxml

4. 環境変数の準備
   - プロジェクトルートに .env または .env.local を配置できます（自動読み込みあり）  
     自動ロードは config.py のロジックにより .git または pyproject.toml の位置をルートとして探索します。
   - 自動読み込みを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨する .env の例（.env.example）
- JQUANTS_REFRESH_TOKEN=<あなたの J-Quants リフレッシュトークン>
- KABU_API_PASSWORD=<kabu ステーション API パスワード（実行モジュール使用時）>
- OPENAI_API_KEY=<OpenAI API キー>
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_FILL_MODE=instant
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

設定の優先度
- OS 環境変数 > .env.local > .env  
  注意: OS 環境変数は上書き保護されます（config の protected ロジックによる）

基本的な使い方（例）
---
以下はパッケージがインストール済み（または開発環境で import 可能）であることを前提にした Python スニペット例です。

1) DuckDB 接続を作り日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄別）を算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を参照
print("書き込み銘柄数:", n_written)
```

3) 市場レジームを算出して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # :memory: でインメモリも可
# conn を使って order/events/executions を操作できる
```

5) 研究用ファクター計算（例: momentum）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとの dict のリスト
```

主要 API の説明（抜粋）
---
- kabusys.config.settings
  - 環境変数から設定を取得する便利なプロパティ群（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH 等）
  - 自動 .env ロード機能あり（必要なら無効化）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...) : 日次 ETL のメインエントリポイント。ETLResult を返す。

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token(refresh_token=None)

- kabusys.data.quality
  - run_all_checks(conn, target_date, ...) : 品質チェックをまとめて実行

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None) : ニュースを集約し OpenAI で銘柄ごとの得点を算出して ai_scores に保存

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None) : ETF(1321) の MA200 乖離とマクロニュースを組み合わせて market_regime に書き込み

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False) : 監査テーブルを初期化（既存接続に対して）
  - init_audit_db(db_path) : 監査用 DuckDB を作って接続を返す

注意事項／設計上のポイント
---
- Look-ahead bias の回避:
  - モジュールの多くは内部で date.today() を用いず、ターゲット日（target_date）を明示的に受け取る設計です（バックテストでの公平性確保）。
- フェイルセーフ:
  - OpenAI API や外部 API の失敗時は、可能な限り処理を継続し（デフォルトスコア等で代替）ログを残す設計になっています。
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込みます。テストで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB 書き込みは冪等性を意識:
  - save_* 関数は ON CONFLICT / DO UPDATE などで多重実行に耐える設計です。

プロジェクト構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py                           : 環境変数・設定管理（.env 自動読み込みロジック含む）
- ai/
  - __init__.py
  - news_nlp.py                        : ニュース集約・OpenAI 呼び出し・ai_scores 書き込み
  - regime_detector.py                 : ETF MA200 とマクロニュースで市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py             : 市場カレンダー管理（営業日判定／更新ジョブ）
  - pipeline.py                        : ETL パイプラインの本体（run_daily_etl など）
  - jquants_client.py                  : J-Quants API クライアント（取得・保存）
  - news_collector.py                  : RSS 収集・前処理・raw_news 保存
  - quality.py                         : データ品質チェック（欠損・スパイク・重複・日付）
  - stats.py                           : 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                           : 監査ログテーブル定義・初期化
  - pipeline.py                         (ETLResult を含む)
- research/
  - __init__.py
  - factor_research.py                 : momentum / value / volatility 等
  - feature_exploration.py             : forward returns / IC / factor summary / rank

追加メモ
---
- テスト時に外部 API をモックするために、内部で API 呼び出しを抽象化した関数（_call_openai_api など）を用意しています。unittest.mock.patch を使って差し替えてテスト可能です。
- news_collector.py は SSRF 対策や XML パース防御（defusedxml）等の安全対策を実装しています。
- DuckDB のバージョン差分や executemany の振る舞いに対する記述があるため、DuckDB の互換性には注意してください。

貢献／ライセンス
---
プロジェクトの貢献方針やライセンスはリポジトリのトップレベルに置かれているドキュメント（LICENSE, CONTRIBUTING.md 等）を参照してください。

問い合わせ
---
不具合報告・機能要望は issue を立ててください。README に無い利用方法で困った点があれば、実行環境や再現手順を添えてお問い合わせください。