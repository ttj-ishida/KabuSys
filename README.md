# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants API からのデータ取得・ETL、ニュースの収集と AI によるセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）、マーケットカレンダー管理など、自動売買システム構築で必要となる主要コンポーネントを提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「DuckDB を中心としたデータ永続化」「冪等性（idempotency）」「外部 API 呼び出しの堅牢なリトライ・レート制御」「監査証跡の確保」です。

---

## 機能一覧

- 環境設定読み込み（.env / OS 環境変数、自動ローディング機能）
- J-Quants API クライアント
  - 日足（OHLCV）取得 / 保存（差分 ETL）
  - 財務データ取得 / 保存
  - JPX マーケットカレンダー取得 / 保存
  - トークン自動リフレッシュ、レート制限対応、リトライ
- ETL パイプライン（run_daily_etl）
  - カレンダー / 株価 / 財務データの差分取得と保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS ベース）
  - URL 正規化、SSRF 防御、トラッキングパラメータ除去、前処理、冪等保存
- AI モジュール（OpenAI）
  - ニュースセンチメント評価（銘柄別 ai_score -> ai_scores テーブル）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
  - JSON Mode を使用した堅牢な API 呼び出しとバリデーション / リトライ
- 研究（research）モジュール
  - モメンタム / ボラティリティ / バリュー等ファクター計算
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化
  - 監査テーブルの冪等初期化ユーティリティ
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）

---

## 前提条件

- Python 3.10+
- 必要なライブラリ（一例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで多くを実装しているため余分な依存は少なめです）

依存はプロジェクトの setup / pyproject に従ってインストールしてください。最低限は以下のようにしてインストールできます：

```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# またはプロジェクトに pyproject/setup があれば:
# pip install -e .
```

---

## セットアップ手順

1. 仮想環境の作成・有効化（推奨）

2. 依存パッケージをインストール

   ```
   pip install -r requirements.txt
   # または個別
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - `.env.local` は `.env` を上書きします。

   主要な環境変数（最低限）：

   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合は必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（実行・発注実装時）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
   - KABUSYS_ENV: development / paper_trading / live
   - DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - その他監視設定（PID_FILE_PATH, KILL_FLAG_PATH 等）

   例 (.env):

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

---

## 使い方（代表的な例）

下記は Python REPL やスクリプト内で利用する例です。各関数の引数に API キーを明示的に渡すこともできます（テスト等で有用）。

- DuckDB 接続の作成（デフォルトファイルを使用）

```py
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行

```py
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を省略すると today が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを作成（ai.news_nlp.score_news）

```py
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されている必要があります
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジームをスコアリング（ai.regime_detector.score_regime）

```py
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化

```py
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# 戻り値は DuckDB 接続
```

- RSS フィードを取得（ニュース収集ユーティリティの一部を直接利用）

```py
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss(
    url="https://news.yahoo.co.jp/rss/categories/business.xml",
    source="yahoo_finance",
)
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意:
- AI 機能（score_news, score_regime）は OpenAI API キーが必要です。関数に `api_key` を明示的に渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- J-Quants API を使う ETL は `JQUANTS_REFRESH_TOKEN` が必須です（settings.jquants_refresh_token が参照されます）。

---

## 環境変数と設定 (settings)

- 自動ロード: パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。無効化は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
- 主要プロパティ（Settings クラス）:
  - jquants_refresh_token -> JQUANTS_REFRESH_TOKEN（必須）
  - kabu_api_password -> KABU_API_PASSWORD（必須 for kabu）
  - kabu_api_base_url -> KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
  - line_channel_access_token, line_user_id -> LINE Messaging 設定（任意）
  - duckdb_path, sqlite_path -> DB ファイルパス（デフォルトを参照）
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start -> 監視設定
  - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct -> 監視閾値
  - env -> KABUSYS_ENV (development / paper_trading / live)
  - log_level -> LOG_LEVEL

設定は `from kabusys.config import settings` で取得します。

---

## ディレクトリ構成（主要ファイル）

以下はソースディレクトリ（src/kabusys）の主要な構成です（抜粋）:

- kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                 -- ニュースセンチメント（銘柄別 ai_scores）
    - regime_detector.py          -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント + 保存処理
    - pipeline.py                 -- ETL パイプライン（run_daily_etl 他）
    - calendar_management.py      -- 市場カレンダー管理
    - news_collector.py           -- RSS 収集・前処理
    - quality.py                  -- データ品質チェック
    - stats.py                    -- zscore_normalize 等ユーティリティ
    - audit.py                    -- 監査ログスキーマ初期化
    - etl.py                      -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py          -- モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py      -- forward_returns, calc_ic, factor_summary, rank
  - monitoring/ (想定)
  - strategy/ (想定)
  - execution/ (想定)

（実際のリポジトリではさらにモジュールやユーティリティ、ドキュメントが含まれる場合があります）

---

## 開発 / テストに関する注意

- DuckDB を利用しているため、ローカル環境での ETL や研究処理はファイルベースの DB（デフォルト: data/kabusys.duckdb）で実行可能です。テスト時は `":memory:"` を使ってインメモリ DB を作成できます。
- OpenAI 呼び出し部は内部でリトライ処理や JSON 検証を行います。ユニットテストでは該当関数（_call_openai_api 等）をモックして外部 API 依存を排除してください。
- news_collector では defusedxml と SSRF 対策（リダイレクト検査、ホストのプライベート判定）を実装しています。実運用ではさらに HTTP クライアント設定やソース管理を検討してください。

---

## 補足 / 設計上の重要ポイント

- ルックアヘッドバイアス防止: AI / ファクタ計算等は target_date 未満のデータのみ参照するよう努めています（date.today()/datetime.today() を直接参照しない等）。
- 冪等性: ETL の保存ロジックは ON CONFLICT DO UPDATE / INSERT の冪等性を考慮しています。
- ロギング: 各モジュールでロガーを利用しているため、LOG_LEVEL を設定すると挙動確認が容易です。
- エラーは段階的に処理して情報を収集する（Fail-Fast ではなく、問題の報告と継続を優先する設計が多い）。

---

必要であれば README のサンプル .env.example の作成、さらなる利用例（kabu 発注フロー・監視プロセスの運用手順）、デプロイ手順（systemd / Docker / cron）なども追加で作成できます。どの情報を優先して詳述しますか？