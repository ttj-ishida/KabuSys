# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ集です。ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は日本株向けのトレーディング基盤コンポーネント群です。主に次を目的としています。

- J-Quants API からの差分 ETL（株価 / 財務 / 市場カレンダー）
- ニュース収集・NLP（OpenAI）による銘柄別センチメント算出
- 市場レジーム判定（ETF とマクロニュースの組合せ）
- 研究用ファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → execution）のスキーマ初期化・管理
- データ品質チェック（欠損、重複、スパイク、日付不整合）

設計方針として「ルックアヘッドバイアス回避」「冪等処理」「外部 API のリトライ・レート制御」「DuckDB を用いた効率的な SQL 処理」を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save / 認証・リトライ・レート制御）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - カレンダー管理（営業日判定, next/prev_trading_day）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得し ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースセンチメントを合成して market_regime テーブルへ書き込み
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank（研究用ユーティリティ）
- config.py: .env / 環境変数の自動読み込みと設定クラス（settings）

---

## 必要条件

- Python 3.10 以上（typing の | などを使用）
- 外部ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

requirements.txt はプロジェクトに合わせて用意してください（例: duckdb, openai, defusedxml）。

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（例: venv）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   pip install -r requirements.txt
   （requirements.txt が無ければ最低限: pip install duckdb openai defusedxml）

4. 環境変数 / .env の準備
   プロジェクトルート（.git または pyproject.toml がある階層）配下に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - SLACK_BOT_TOKEN: Slack 通知に使用するボットトークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - KABU_API_PASSWORD: kabuステーション API パスワード（必要な場合）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が必要な場合）

   省略可能・デフォルトあり
   - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   サンプル .env（最低限: JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY が必要な処理があります）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース初期化（監査ログなど）
   Python REPL やスクリプトから init_audit_db を呼び出して監査 DB を作成できます（例は後述）。

---

## 使い方（簡易サンプル）

共通準備:
- DuckDB 接続を作成して関数に渡します。
- 必要な API キー（OpenAI / J-Quants）を環境変数または関数引数で渡します。

例: 日次 ETL 実行
```
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

例: ニュースの NLP スコアリング（ai_scores へ書き込む）
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で参照
print(f"scored {count} codes")
```

例: 市場レジーム判定
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

例: 監査データベース初期化（専用 DB）
```
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査専用に別 DB を使う場合
conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

その他のユーティリティ：
- data.calendar_management: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- data.jquants_client: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_* 関数（ETL から内部で使用）
- research.factor_research: calc_momentum / calc_value / calc_volatility
- research.feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

注意:
- AI 系（news_nlp, regime_detector）は OpenAI API を使用します。ネットワーク失敗や API のエラーはフェイルセーフで処理を継続する実装ですが、API キーは必須です。
- J-Quants の API 呼び出しには rate limit と retry 処理が組み込まれています。get_id_token は JQUANTS_REFRESH_TOKEN から id_token を発行します。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                          # 環境変数 / .env ロード・settings
  - ai/
    - __init__.py
    - news_nlp.py                       # ニュース NLP スコアリング
    - regime_detector.py                # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                 # J-Quants API client + save_* 関数
    - pipeline.py                       # ETL パイプライン（run_daily_etl 等）
    - etl.py                            # ETL インターフェース再エクスポート
    - news_collector.py                 # RSS 収集・前処理
    - calendar_management.py            # マーケットカレンダー管理
    - quality.py                        # データ品質チェック
    - stats.py                          # 統計ユーティリティ（zscore_normalize）
    - audit.py                          # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py                # モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py            # 将来リターン/IC/統計サマリー
  - ai/, data/, research/ にそれぞれテストや補助モジュールが含まれます。

---

## 実装上の注意点 / 運用メモ

- .env 自動読み込み: config.py はプロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を読み込みます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 環境モード: KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかで検証されます。live モード時は運用上の注意（発注処理の扱い）を徹底してください。
- DuckDB: ETL は DuckDB を前提に設計されています。ファイルパスや接続は settings.duckdb_path を利用してください。
- トレーサビリティ: audit モジュールは発注→約定フローを完全に追跡するためのテーブル群とインデックスを提供します。初期化は冪等です。
- API キーの扱い: OpenAI / J-Quants トークンは秘密情報です。CI / デプロイでは適切にシークレット管理（Vault 等）を行ってください。
- テスト: モジュール内では外部呼び出し部（OpenAI, urllib）をモックしやすい設計になっています（内部呼び出し関数を patch 可能）。

---

必要なら、README に入れる追加セクション（API リファレンス、例: 各関数の引数/戻り値、データベーススキーマ定義、CI/デプロイ手順、サンプル .env.example ファイル）を追記します。どの情報を優先して追加しますか？