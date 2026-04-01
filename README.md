KabuSys
=======

日本株向けの自動売買・データプラットフォーム用ライブラリセットです。
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュースの NLP スコアリング・市場レジーム判定・リサーチ（ファクター計算）・監査ログ（オーディット）等の機能を提供します。

主な特徴
-------
- J-Quants API からの差分取得（株価日足 / 財務 / マーケットカレンダー）と DuckDB への冪等保存
- データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- ニュース収集（RSS）／前処理と LLM を用いた銘柄別センチメント（ai_scores）の生成
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを統合）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）を表現するスキーマの初期化
- 環境変数中心の設定管理（.env / .env.local を自動ロード可能）

必須環境
-------
- Python 3.10+
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全性向上のため）
- 標準ライブラリ以外の追加依存は requirements.txt にまとめて運用してください（本リポジトリにはサンプルのみ記載）。

推奨インストール（例）
-----------------
仮想環境を作成してから依存をインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 任意: pip install -e .
```

環境変数（.env）
---------------
主に以下の環境変数が利用されます。実運用前に .env（または環境）を用意してください。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（注文系）
- SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）

オプション:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / …（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など運用用閾値

自動 .env 読み込み:
- パッケージ内の config モジュールは、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）にある .env / .env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（基本例）
--------------

1) DuckDB 接続の用意
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（株価 / 財務 / カレンダー の差分取得と品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのセンチメントスコアを生成（OpenAI を使用）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を明示的に渡すか環境変数 OPENAI_API_KEY を利用
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書込み銘柄数: {n_written}")
```

4) 市場レジーム判定を実行
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

6) 監査ログスキーマの初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルへ書き込み等を行う
```

主要モジュール（機能一覧）
-----------------------
- kabusys.config
  - 環境変数の読み込みと Settings オブジェクト（各種設定プロパティ）
- kabusys.data.jquants_client
  - J-Quants API クライアント（取得 / 保存 / 認証・リトライ・レート制限）
- kabusys.data.pipeline, etl
  - 日次 ETL の主エントリポイント（run_daily_etl）と個別ジョブ（prices/financials/calendar）
- kabusys.data.quality
  - データ品質チェック（欠損 / スパイク / 重複 / 日付整合性）
- kabusys.data.news_collector
  - RSS 取得・前処理・raw_news への保存ロジック（SSRF 防御・サイズ制限・正規化）
- kabusys.ai.news_nlp
  - ニュースを LLM（OpenAI）へ投げて銘柄別センチメントを ai_scores へ書き込む
- kabusys.ai.regime_detector
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを統合して market_regime を生成
- kabusys.research
  - ファクター計算（momentum/value/volatility）・特徴量解析ユーティリティ
- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
- kabusys.data.stats
  - z-score 正規化等の統計ユーティリティ

ディレクトリ構成（抜粋）
--------------------
src/kabusys/
- __init__.py
- config.py                      - 環境変数 & 設定管理
- ai/
  - __init__.py
  - news_nlp.py                   - ニュース NLP（OpenAI）による ai_scores 書き込み
  - regime_detector.py            - 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py             - J-Quants API クライアント（fetch/save）
  - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
  - etl.py                        - ETL インターフェース（ETLResult の公開）
  - quality.py                    - 品質チェック
  - news_collector.py             - RSS 収集・前処理
  - calendar_management.py        - マーケットカレンダー管理（営業日ロジック）
  - stats.py                      - 統計ユーティリティ
  - audit.py                      - 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py            - モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py        - 将来リターン / IC / 統計サマリー 等

運用上の注意
-----------
- Look-ahead バイアス防止: 多くの関数は内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を渡す設計です。バックテスト／履歴再現の際は target_date を明示してください。
- OpenAI 呼び出し: レスポンスのパース失敗や API エラー時はフェイルセーフとしてスコアを 0.0 にフォールバックする等の防御策が入っています。テストではモック可能な内部関数を patch することが想定されています（例: kabusys.ai.news_nlp._call_openai_api の差し替え）。
- .env の扱い: config.py はプロジェクトルートの .env / .env.local を自動読み込みします。CI／テストでは読み込みを無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- DuckDB executemany の挙動: 一部のコードは DuckDB のバージョン特性（executemany に空リストを渡せない等）を考慮しています。DuckDB の互換性に注意してください。

テスト／開発時ヒント
------------------
- OpenAI 呼び出しやネットワーク I/O 部分はユニットテストでモックしやすい設計です（内部の _call_openai_api、_urlopen、_request 等を patch）。
- ETL の個別関数（run_prices_etl / run_financials_etl / run_calendar_etl）はそれぞれ独立して実行可能で、ログや ETLResult で結果が取得できます。
- audit.init_audit_db を使えば監査用の独立した DuckDB を作成できます。初期化は冪等で、transactional オプションがあります。

ライセンス / 貢献
----------------
本 README はコードベースの概観と利用方法をまとめたものです。実際の配布パッケージでは LICENSE / CONTRIBUTING の追加を推奨します。

お問い合わせ
-----------
問題報告や改善提案は Issue を作成してください。簡単な質問は README に沿った情報（使用中の Python バージョン、DuckDB バージョン、再現手順）を添えて報告していただけると対応が早くなります。

以上。必要であれば README に記載する .env.example や requirements.txt のテンプレート、具体的な SQL スキーマや CLI 実行例を追加で作成します。どの情報を追記しますか？