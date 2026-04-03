# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
DuckDB をデータ層に用い、J-Quants からのデータ取得、ニュースの NLP 評価（OpenAI）、ファクター計算、ETL／品質チェック、監査ログ（オーダー／約定トレーサビリティ）等のユーティリティを提供します。

バージョン: 0.1.0

---

## 主要機能

- 環境変数管理（.env の自動ロード、保護機構）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX カレンダー取得（ページネーション／リトライ／レート制限対応）
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - 差分取得（バックフィル対応）、保存、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、前処理）、raw_news への保存補助
- ニュース NLP / LLM 統合
  - 銘柄ごとのニュースセンチメント算出（score_news）
  - マクロニュース + ETF(1321)の MA乖離 による市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を JSON mode で使用、リトライ/フェイルセーフ設計
- リサーチ用ユーティリティ
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリ、Z-score 正規化
- 監査ログスキーマ（監査テーブルの初期化・専用 DB 初期化）
  - signal_events / order_requests / executions を含むスキーマ、冪等・トレーサビリティ対応

---

## 要求環境 / 依存ライブラリ（代表例）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- そのほか標準ライブラリ

（プロジェクトに requirements.txt があればそれを使用してください）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または手動で: pip install duckdb openai defusedxml

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を配置できます。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須: JQUANTS_REFRESH_TOKEN（J-Quants の refresh token）
   - OpenAI を使う場合: OPENAI_API_KEY（score_news / score_regime の api_key 引数でも指定可）
   - その他オプション設定は下記の .env 例を参照

5. DuckDB / データディレクトリ準備
   - デフォルトの DuckDB ファイルパスは `data/kabusys.duckdb`（settings.duckdb_path）
   - 必要に応じて .env で `DUCKDB_PATH` を上書き

---

## .env 例 (.env.example)

以下をプロジェクトルートに作成してください（値は適宜設定）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# DB パス 等（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行監視
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
KILL_FLAG_CLEAR_ON_START=0

# システム設定
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO

---

## 使い方（主要例）

※ すべて Python API 経由で呼び出します。CLI は本コードベースに含まれていません。

### DuckDB 接続を作る

import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))

### 日次 ETL を実行する

from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

説明:
- 市場カレンダー → 株価日足 → 財務データ → 品質チェック の順で実行します。
- ETLResult に取得件数・保存件数・品質問題・エラー情報が入ります。

### ニュースのスコアリング（AI）

from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは api_key 引数、または環境変数 OPENAI_API_KEY を使用
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {n} codes")

説明:
- 前日15:00 JST〜当日08:30 JST のウィンドウの記事を対象に、銘柄ごとのセンチメントを ai_scores テーブルへ保存します。
- OpenAI 呼び出しが失敗した場合はスキップして他の銘柄処理を継続します（フェイルセーフ）。

### 市場レジーム評価（ETF 1321 の MA + マクロニュース）

from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

説明:
- ma200 の乖離（重み70%）とマクロセンチメント（重み30%）を合成して market_regime テーブルへ書き込みます。
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY。

### 監査ログスキーマ初期化（監査専用 DB）

from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions が作成されます

### リサーチ系ユーティリティ使用例

from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))

forward = calc_forward_returns(conn, date(2026, 3, 20))
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])

説明:
- 各関数は DuckDB 接続を受け取り、prices_daily / raw_financials 等のテーブルを参照します。
- datetime.today() 等は参照せず、引数の target_date に依存するためバックテストでの利用に配慮されています。

---

## 注意点 / 設計上のポイント

- Look-ahead バイアス対策:
  - ほとんどの処理で datetime.today() を直接参照せず、target_date を明示的に渡すことを想定しています。
  - prices_daily 等クエリでは date < target_date のようにルックアヘッドを防止する設計が取られています（モジュールにより実装差あり）。
- LLM 呼び出し:
  - OpenAI JSON mode を使い厳密な JSON 出力を期待する実装です。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを組み込んでいます。
  - API 失敗時はフェイルセーフ（スコア＝0 やスキップ）で続行する方針。
- ETL / データ品質:
  - 品質チェックは Fail-Fast ではなく全チェック結果を返し、呼び出し元で判断できるようにしています。
- セキュリティ:
  - RSS 取得時は SSRF 対策（リダイレクト検査・プライベート IP の検出）を実装。
  - .env の自動読み込み時に OS 環境変数を保護するロジックあり。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      # 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py                  # ニュース NLP スコアリング
  - regime_detector.py           # 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            # J-Quants API クライアント + 保存関数
  - pipeline.py                  # ETL パイプライン / run_daily_etl / run_*_etl
  - etl.py                       # ETLResult 再エクスポート
  - calendar_management.py       # 市場カレンダー管理
  - stats.py                     # 統計ユーティリティ（zscore）
  - quality.py                   # データ品質チェック
  - audit.py                     # 監査ログスキーマ初期化
  - news_collector.py            # RSS 収集・前処理
- research/
  - __init__.py
  - factor_research.py           # Momentum/Value/Volatility 等
  - feature_exploration.py       # forward returns / IC / summary / rank
- research/...                    # その他リサーチ用モジュール

---

## ログ / 実行環境設定

- 環境変数 `LOG_LEVEL` でログレベルを制御（DEBUG / INFO / WARNING / ERROR / CRITICAL）。
- `KABUSYS_ENV` は (development | paper_trading | live) のいずれか。`settings.is_live` などで判定可能。
- 自動で .env を読み込む際、OS 環境変数が優先されます。テスト等で自動読み込みを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 開発 / テスト

- 各モジュールは外部 API（OpenAI, J-Quants, ネットワーク）に依存する箇所があるため、ユニットテストでは依存呼び出し部分をモックすることが想定されています（コード中に patch 用コメントあり）。
- DuckDB を使うことでメモリ内 DB（":memory:"）での高速テストが可能です。

---

## ライセンス / 貢献

この README はコードベースの概要ドキュメントです。実プロジェクトでの利用にあたってはライセンス表記・貢献ルール等をプロジェクトルートに追記してください。

---

必要であれば、この README を README.md として整形したファイル内容や .env.example のフルテンプレート、よく使うユーティリティ関数の具体的なサンプル（さらに詳しいコード例）を追加で作成します。どの部分を詳しく書きますか？