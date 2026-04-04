KabuSys — 日本株自動売買基盤
=======================

概要
----
KabuSys は日本株のデータ収集・品質管理・ファクター計算・AI によるニュースセンチメント解析・市場レジーム判定・監査ログなどを含む、バックテスト / 研究 / 運用向けのコンポーネント群です。  
主に DuckDB をデータレイクとして用い、J-Quants API からのデータ取得や OpenAI（gpt-4o-mini）を用いたニュース NLP を組み合わせて運用・分析パイプラインを提供します。

特徴（主な機能）
----------------
- データ ETL:
  - J-Quants から株価日足（OHLCV）・財務データ・JPXカレンダーを差分取得・保存（冪等）
  - 差分取得、バックフィル、ページネーション、トークン自動リフレッシュ対応
- データ品質検査:
  - 欠損、重複、スパイク（急騰/急落）、将来日付/非営業日データ検出
- ニュース収集:
  - RSS の安全な取得（SSRF対策、XML攻撃対策、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存ロジック
- ニュース NLP:
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメント（ai_scores）算出（バッチ・リトライ・レスポンス検証）
  - 記事ウィンドウの定義（JST基準）
- 市場レジーム判定:
  - ETF (1321) の 200 日MA乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を組み合わせて日次で bull/neutral/bear を算出
  - LLM 呼び出しは冪等・リトライ・フェイルセーフ設計
- リサーチ支援:
  - モメンタム / バリュー / ボラティリティ等のファクター算出
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化等
- 監査ログ（トレーサビリティ）:
  - signal_events / order_requests / executions テーブルを持つ監査スキーマの初期化・管理
- 設定管理:
  - .env / .env.local / OS 環境変数から設定を自動読み込み（プロジェクトルート検出）

セットアップ
----------

前提
- Python 3.9+（型・依存ライブラリが必要）
- ネットワークアクセス（J-Quants / OpenAI）

推奨パッケージ（主要）
- duckdb
- openai
- defusedxml

インストール（開発時）
```
# プロジェクトルートで
python -m pip install -e .          # setuptools-based package がある想定
python -m pip install duckdb openai defusedxml
```

環境変数（.env）
- プロジェクトルートの .env / .env.local を自動で読み込みます（優先: OS env > .env.local > .env）。
- 自動読み込みを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主な環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu ステーションのベース URL（既定: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知等に使用
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（既定: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視制御
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development | paper_trading | live（既定: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（既定: INFO）

例 (.env.example)
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

使い方（簡単なコード例）
--------------------

共通準備
```
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL の実行
```
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しない場合は今日が対象
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュース NLP（銘柄別 ai_scores 作成）
```
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数か api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

市場レジーム判定
```
from kabusys.ai.regime_detector import score_regime

res = score_regime(conn, target_date=date(2026, 3, 20))
print("score_regime: done")
```

監査ログ DB 初期化
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# またはメイン DB 内にスキーマを作る場合は conn をそのまま渡して init_audit_schema を呼ぶ
```

J-Quants クライアント利用例
```
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
# save は pipeline / etl 側で行われます
```

設計上の注意点
- ルックアヘッドバイアス防止:
  - 各 AI / リサーチ関数は内部で datetime.today() を参照しないなど、過去データのみを使う設計になっています。バックテストで利用する際はこの点を尊重してください。
- OpenAI 呼び出し:
  - news_nlp と regime_detector は gpt-4o-mini を JSON Mode で利用します。API の失敗時はフェイルセーフ（ゼロスコア等）で継続する設計です。
- DuckDB executemany の挙動:
  - 一部コードは DuckDB のバージョン依存（executemany の空引数など）に配慮して実装されています。DuckDB の互換性に注意してください。

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント算出
    - regime_detector.py            — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                   — ETL パイプライン / run_daily_etl 等
    - etl.py                        — ETL 型のエクスポート
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - news_collector.py             — RSS 収集・前処理・保存
    - calendar_management.py        — JPX カレンダー管理 / 営業日判定
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — momentum/value/volatility 等
    - feature_exploration.py        — 将来リターン / IC / summary / rank

開発・運用のヒント
------------------
- ローカルでのテスト時は OPENAI_API_KEY を設定するか、score_news/score_regime の api_key 引数にモックキーを渡してモックを使うとよいです。
- 自動 .env 読み込みはプロジェクトルート（.git か pyproject.toml を基準）を探索して行います。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化して明示的に設定することを推奨します。
- ETL は個々のステップで例外を吸収しつつ結果を集約するため、一部失敗しても他のステップは継続されます。ETLResult の has_errors / has_quality_errors をチェックして運用判断してください。

ライセンス・貢献
----------------
- （ここにプロジェクトのライセンス情報や貢献方法を記載してください）

お問い合わせ
------------
不具合や改善提案は Issue を立てるか、プロジェクトの連絡先へお願いします。