KabuSys
=======

日本株向けの自動売買 / データパイプライン用ライブラリです。  
本リポジトリはデータ収集（J-Quants / RSS）、品質チェック、ファクター計算、AI を使ったニュースセンチメント解析、監査ログ（発注トレーサビリティ）、および市場レジーム判定を含む機能群を備えています。

主な目的
- J-Quants からの株価・財務・カレンダーの差分 ETL
- RSS ベースのニュース収集と LLM による銘柄センチメント算出
- ファクター（モメンタム/バリュー/ボラティリティなど）算出・解析ツール
- 監査ログ（signal → order_request → executions）のスキーマ初期化と操作
- 市場レジーム（bull/neutral/bear）判定（MA と マクロニュースの合成）

機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート判定）
  - 必須設定の取得ヘルパー settings
- データ ETL（kabusys.data.pipeline, jquants_client）
  - 日次差分 ETL 実行 run_daily_etl
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - 市場カレンダーの取得 / 営業日判定（calendar_management）
  - データ品質チェック（quality）
  - ニュース収集（news_collector）：RSS 正規化・SSRF 対策・前処理
  - 監査ログスキーマ初期化（audit）
  - 汎用統計ユーティリティ（stats.zscore_normalize）
- 研究・リサーチ（kabusys.research）
  - ファクター計算（momentum/value/volatility）
  - 特徴量探索・将来リターン計算・IC 計算・統計サマリー
- AI モジュール（kabusys.ai）
  - ニュース NLP による銘柄ごとのセンチメント付与（score_news）
  - マクロニュースと ETF MA200 を合成した市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini 等）への呼び出しは安全策（リトライ・パース検証）を組込
- その他ユーティリティ（設定・監視パラメータ等）

セットアップ手順（開発環境）
- 前提
  - Python 3.10+ を想定（typing の | などを利用）
  - システムに git がインストール済みであること

1) ソース取得
- リポジトリをクローンしてください。

2) 仮想環境作成（任意だが推奨）
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3) 依存関係インストール
- pip install -U pip
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 例:
  pip install duckdb openai defusedxml

（プロジェクトに requirements.txt がある場合はそれを使用してください）

4) 環境変数設定
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - KABU_API_PASSWORD=your_kabu_station_password
  - KABU_API_BASE_URL=http://localhost:18080/kabusapi
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=C0123456789
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PID_FILE_PATH=data/execution.pid
  - CPU_THRESHOLD_PCT=90.0
  - MEMORY_THRESHOLD_PCT=85.0
  - DISK_THRESHOLD_PCT=90.0
  - OPENAI_API_KEY=sk-...
  - KABUSYS_ENV=development   # 開発: development / paper_trading / live
  - LOG_LEVEL=INFO

- .env の読み込みルール:
  - OS 環境 > .env.local > .env の優先順位
  - export KEY=VALUE 形式をサポート
  - 引用符・コメント・エスケープに対応

使い方（簡単な例）
- Python から直接呼び出すケースを示します。

1) DuckDB 接続を準備して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を使用しても良い
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) AI によるニューススコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込件数:", n_written)
```
- 注意: OPENAI_API_KEY が環境変数または api_key 引数で必要です。

3) 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（監査用 DuckDB を作る）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# 以降 conn を使って監査テーブルにレコードを挿入/検索できます
```

設定（settings）の利用
- kabusys.config.settings をインポートして設定値を参照できます。
  例: from kabusys.config import settings; settings.duckdb_path

- settings は .env / 環境変数に依存します。必須キーが未設定の場合は ValueError を投げます。

ディレクトリ構成（主なファイル / モジュール）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント + 保存関数
    - pipeline.py                  — ETL パイプライン & run_daily_etl, run_*_etl
    - etl.py                       — ETLResult の公開
    - news_collector.py            — RSS 収集・正規化（SSRF 対策等）
    - calendar_management.py       — market_calendar 管理 / 営業日ロジック
    - quality.py                   — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                     — zscore_normalize 等
    - audit.py                     — 監査ログ（テーブル定義・初期化ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py           — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py       — calc_forward_returns / calc_ic / factor_summary / rank
  - ai/、research/、data/ の各モジュールはさらに細かな責務で分かれています（コメントに処理フロー・設計方針あり）。

注意事項 / 補足
- Look-ahead バイアス対策:
  - 多くの関数は date パラメータを明示的に受け取り、内部で datetime.today()/date.today() を直接参照しない設計です。バックテストや再現性が求められるワークフローで安全に使えます。
- OpenAI・外部 API 呼び出し:
  - OpenAI は JSON Mode を用いた厳密なパースを行い、リトライやフェイルセーフ（失敗時にスコアを 0 にフォールバック）を実装しています。
  - J-Quants クライアントはレート制御・リトライ・トークン自動リフレッシュを備えています。
- セキュリティ:
  - news_collector は SSRF や XML bomb、受信サイズ制限、トラッキングパラメータ削除などの防御策を実装しています。
- DuckDB バインド注意:
  - 一部の場所で DuckDB の executemany に空リストを渡すと失敗するため、呼び出し前に空チェックをしています。

貢献・開発
- 新しい ETL や品質チェック、研究用の関数を追加する際は、関数が外部 API を直接叩かないこと（テスト容易性のため）や、ルックアヘッドバイアスを生まない設計であることに留意してください。
- テストでは設定の自動読み込みを無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用すると便利です。

ライセンス / 著作権
- 本リポジトリに付随するライセンス・著作情報をご確認ください（ここではコードの断片を元に README を生成しています）。

以上。導入や個別 API の使い方で具体的なコード例が必要であれば用途（ETL Cron 設定、監査ログ挿入例、news_collector の保存フロー等）を指定して伝えてください。