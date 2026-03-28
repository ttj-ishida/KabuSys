# KabuSys

KabuSys は日本株のデータパイプライン、ファクター研究、AI ベースのニュース解析、監査ログ、マーケットカレンダー管理、および ETL/保存ロジックを備えた日本株自動売買支援ライブラリです。DuckDB をデータストアに利用し、J-Quants / JPX / RSS / OpenAI などを組み合わせたデータ取得・処理基盤を提供します。

概要
- 設計方針は「ルックアヘッドバイアスの排除」「ETL の冪等性」「フェイルセーフ（API失敗時はスキップやデフォルト値で継続）」です。
- データ取得（J-Quants）、ニュース収集（RSS）、ニュースの LLM によるセンチメント解析、ファクター計算、品質チェック、監査ログ（注文/約定トレース）などの機能を含みます。

主な機能
- データ取得／ETL
  - J-Quants からの株価（日足）・財務・上場情報・マーケットカレンダー取得（ページネーション・リトライ・レート制御）
  - 差分取得・バックフィル・品質チェック付きの日次 ETL（run_daily_etl）
- ニュース関連（News Collector）
  - RSS フィードの取得・前処理・raw_news への冪等保存（SSRF や XML 攻撃対策、トラッキングパラメータ削除）
- AI（OpenAI）連携
  - 銘柄ごとのニュースセンチメント算出（score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメント合成 → score_regime）
  - gpt-4o-mini を JSON mode で使用（リトライ / レスポンス検証 / フェイルセーフ実装）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター算出（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計、Zスコア正規化
- データ品質チェック
  - 欠損・スパイク・重複・日付整合性チェック（run_all_checks）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などのテーブルを生成・初期化する機能（init_audit_schema / init_audit_db）

セットアップ手順（開発向け）
1. Python 環境を用意（推奨: 3.10+）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（代表的なもの）
   - pip install duckdb openai defusedxml
   - 追加でテストや開発ツールが必要なら適宜インストールしてください
   - （実プロジェクトでは requirements.txt または pyproject.toml を用意して pip install -e . を推奨）
4. 環境変数（.env）を用意
   - プロジェクトルートに .env または .env.local を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN: J-Quants 更新トークン
     - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID
     - KABU_API_PASSWORD: kabuステーション API パスワード（使用する場合）
     - OPENAI_API_KEY: OpenAI を使う場合（score_news / score_regime など）
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env の自動ロードを無効化
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

例: .env（サンプル）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_kabu_pw
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

基本的な使い方（Python API）
- DuckDB 接続例:
```py
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行:
```py
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントを算出（指定日）:
```py
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定:
```py
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査 DB の初期化（専用 DB を作る場合）:
```py
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

- ファクター計算（研究用）:
```py
from kabusys.research.factor_research import calc_momentum
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
# mom は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

注意点
- OpenAI 呼び出しは外部 API です。API キーを環境変数か引数で渡してください。API 失敗時は多くの場所でフェイルセーフ（0 やスキップ）を採用しています。
- J-Quants の API レート制限（120 req/min）に合わせた内部レートリミッタがあります。ID トークンの自動リフレッシュとリトライロジックを実装済みです。
- ETL / DB 書き込みは冪等性を意識しており、ON CONFLICT を利用して上書き保存します。
- テスト環境では自動 .env ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用できます。

主要ディレクトリ構成（src/kabusys）
- kabusys/
  - __init__.py (パッケージ初期化: __version__ 等)
  - config.py (環境変数 / .env ロード / Settings)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースセンチメント解析: score_news)
    - regime_detector.py (市場レジーム判定: score_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント: fetch_*/save_*)
    - pipeline.py (ETL パイプラインの実装: run_daily_etl ほか)
    - etl.py (ETL の公開インターフェース: ETLResult)
    - calendar_management.py (市場カレンダー管理・営業日関連)
    - stats.py (統計ユーティリティ: zscore_normalize)
    - quality.py (品質チェック: run_all_checks 他)
    - audit.py (監査ログテーブル定義・初期化)
    - news_collector.py (RSS 収集・前処理)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum / calc_value / calc_volatility)
    - feature_exploration.py (calc_forward_returns / calc_ic / factor_summary / rank)
  - (その他: strategy / execution / monitoring パッケージを __all__ に含む設計想定)

開発・貢献
- コードの追加や改善は、設計方針（ルックアヘッドバイアス回避、冪等性、フェイルセーフ）を尊重してください。
- 外部キーやトランザクションの扱い（DuckDB の制約）に注意して実装してください。
- テスト時は外部 API 呼び出しをモックすることを推奨します（news_nlp._call_openai_api 等はモック可能な設計）。

免責事項
- 本リポジトリは自動売買ロジックを直接含むのではなく、データプラットフォームと研究 / 支援機能群を提供します。実際の発注や運用に利用する場合は十分な検証とリスク管理を行ってください。

以上。必要であれば README にサンプル .env.example や依存関係リスト（requirements.txt）を追加したり、具体的な CLI や Systemd ジョブ例、CI 設定例を追記できます。どの情報を追加しますか？