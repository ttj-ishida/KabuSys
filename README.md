# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys のリポジトリ README（日本語）

概要
---
KabuSys は日本株のデータパイプライン、特徴量・ファクター計算、AI を用いたニュースセンチメント・市場レジーム判定、監査ログと発注トラッキング準備まで含む、研究⇄実運用を想定したモジュール群です。DuckDB をデータストアとして利用し、J-Quants API からのデータ取得、OpenAI（gpt-4o-mini 等）を用いる NLP 処理、JPX カレンダー管理、ETL パイプライン、品質チェック、監査テーブル初期化などを提供します。

主な機能
---
- データ取得／ETL
  - J-Quants API からの株価日足、財務データ、上場銘柄・カレンダー取得（差分取得・ページネーション対応）
  - ETL パイプライン（run_daily_etl）による市場カレンダー・株価・財務の差分取得および品質チェック
- データ品質管理
  - 欠損、重複、スパイク、日付不整合などを検知する品質チェック群（quality モジュール）
- カレンダー管理
  - JPX カレンダー管理／営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - 夜間バッチ更新 job（calendar_update_job）
- 研究／ファクターモジュール
  - モメンタム、ボラティリティ、バリュー系ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化
- AI（ニュース NLP / レジーム判定）
  - ニュース記事を銘柄ごとに集約し OpenAI でセンチメント（score_news）
  - ETF（1321）200日MA乖離とマクロニュースセンチメントを合成して市場レジーム判定（score_regime）
  - OpenAI 呼び出しはリトライ・フェイルセーフを備え、レスポンス検証を実施
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを含む監査スキーマの自動初期化（init_audit_schema / init_audit_db）
- ニュース収集
  - RSS 取得・前処理・SSRF 対策・トラッキングパラメータ除去・raw_news への保存ロジック

セットアップ手順
---
1. Python バージョン
   - Python 3.10+ を推奨（コードは型ヒントやモダン機能を使用）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを利用してください。）

4. パッケージのインストール（editable）
   - pip install -e .

5. 環境変数 / .env 設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（settings より）
- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（ETL で必須）
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（発注連携などで使用）
- KABU_API_BASE_URL (任意)
  - デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY (必須: AI を利用する場合)
  - OpenAI API キー
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意)
  - 通知用途
- DUCKDB_PATH (任意)
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)
  - デフォルト: data/monitoring.db
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START (監視用)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT (監視閾値)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

使い方（概要とコード例）
---
※ ここでは主要なユースケースの呼び出し例を示します。すべての API は DuckDB の接続オブジェクト（duckdb.connect(...) が返すオブジェクト）を受け取る設計です。

1) ETL を実行する（日次 ETL）
- 例:
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を渡さなければ今日（ただしカレンダー調整あり）
print(result.to_dict())
```

2) ニュースセンチメントをスコアリングする
- 例:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```
- OpenAI API キーを関数引数で渡すことも可能: score_news(..., api_key="sk-...")

3) 市場レジーム判定
- 例:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定しておく
```

4) 監査データベースを初期化する（監査ログ専用 DB）
- 例:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリがなければ自動作成
```

5) ファクター計算 / 研究ユーティリティ
- 例:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
vol = calc_volatility(conn, date0)
val = calc_value(conn, date0)

# Zスコア正規化（例）
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

ディレクトリ構成（主要ファイル）
---
以下はソースツリー（src/kabusys）の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 # ニュースセンチメント（score_news）
    - regime_detector.py          # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           # J-Quants API クライアント（fetch / save）
    - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
    - etl.py                      # ETLResult 再エクスポート
    - quality.py                  # データ品質チェック
    - stats.py                    # 共通統計ユーティリティ（zscore_normalize）
    - news_collector.py           # RSS ニュース収集・前処理
    - calendar_management.py      # JPX カレンダー管理・営業日判定
    - audit.py                    # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py          # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py      # calc_forward_returns / calc_ic / factor_summary / rank

運用上の注意・トラブルシューティング
---
- .env の自動読み込み
  - プロジェクトルートに .env/.env.local がある場合、自動で読み込まれます。テスト等で自動読み込みを抑えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants の API キー
  - AI モジュールや ETL の J-Quants 呼び出しにはそれぞれ有効なキーが必要です。キーが未設定の場合、多くの関数は ValueError を送出します。
- レート制限とリトライ
  - jquants_client は API レート制限（120 req/min）に合わせた内部 rate limiter と再試行ロジックを備えています。OpenAI 呼び出しもリトライ・指数バックオフを実装していますが、運用環境では呼び出し頻度に注意してください。
- DuckDB ファイルパス
  - デフォルトの DUCKDB_PATH は data/kabusys.duckdb です。ディレクトリが存在しない場合は事前に作成するか、init_audit_db 等の関数が親ディレクトリを自動作成する点を参照してください。
- フェイルセーフ設計
  - AI 呼び出し失敗時にはスコアを 0 にフォールバックする等、バックテストや日次バッチで過度に停止しない設計にしています。ただし、重要な決定を行う前にログや監視で失敗状況を確認してください。

ライセンス / 貢献
---
（このリポジトリにライセンスファイルがあればそこを参照してください。貢献方法・コードスタイルなどのルールがある場合はプロジェクトの CONTRIBUTING.md を参照してください。）

補足
---
- ドキュメント中の設計方針や安全対策（SSRF 対策、JSON レスポンス検証、ルックアヘッドバイアス回避など）は各モジュールの docstring に詳細を記載しています。実装や挙動を詳しく確認したい場合は該当モジュールの docstring を参照してください。
- 具体的な運用コマンドやデプロイ手順（systemd / Docker / CI/CD 等）はリポジトリの運用方針に依存するためここでは記載していません。必要であればそれら向けに別途ドキュメントを作成できます。

必要であれば、README に次の内容を追加できます:
- さらに詳しい API リファレンス（関数ごとの引数・返り値一覧）
- デプロイ / systemd / Docker のサンプル
- CI / テストの実行手順
- サンプル .env.example

必要な追加事項があれば教えてください。