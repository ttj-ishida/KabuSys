# KabuSys

日本株向けのデータプラットフォーム＋自動売買基盤コンポーネント群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（オーダー追跡）などのユーティリティを含みます。

---

## プロジェクト概要

KabuSys は以下の目的で設計されたモジュール群です。

- J-Quants API からの差分 ETL（株価日足・財務・マーケットカレンダー）  
- RSS ベースのニュース収集と LLM（OpenAI）を用いた銘柄別・マクロセンチメント評価  
- 研究用途のファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量解析ツール  
- 監査ログ（signal → order_request → execution のトレーサビリティ）を保持する DuckDB スキーマ初期化  
- データ品質チェック（欠損・重複・スパイク・日付整合性）  
- 環境設定・.env 自動ロードの仕組み

設計上の共通方針として「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（API障害時の安全なフォールバック）」を重視しています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
  - 必須変数未設定時は例外で通知

- データ取得（jquants_client）
  - 株価日足（ページネーション対応）
  - 財務データ（四半期）
  - JPX マーケットカレンダー
  - 保存は DuckDB に対して冪等（ON CONFLICT DO UPDATE）

- ETL パイプライン（data.pipeline）
  - run_daily_etl による日次一括 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）

- ニュース収集（data.news_collector）
  - RSS 取得（SSRF 対策、gzip 対応、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存

- ニュース NLP（ai.news_nlp）
  - 指定ウィンドウのニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）で JSON 出力を受けて ai_scores テーブルへ書込み
  - バッチ処理、リトライ（429 / ネットワーク / 5xx）やレスポンスの厳格検証を実装

- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）

- 研究用機能（research）
  - calc_momentum / calc_value / calc_volatility（DuckDB を用いたファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索・IC 計算）

- データ品質チェック（data.quality）
  - 欠損・重複・スパイク・日付不整合検出
  - QualityIssue オブジェクトで問題を集約

- 監査ログ（data.audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化関数
  - init_audit_db による DB 初期化（UTC タイムゾーン固定）

---

## 必要条件

- Python 3.10 以上（| 型注釈などを使用）
- 主なライブラリ（例）
  - duckdb
  - openai
  - defusedxml

※ 実行環境によっては追加で network・SSL 等の設定が必要です。

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 例（最低限）:
     - pip install duckdb openai defusedxml

   - 開発パッケージや他依存はプロジェクトの packaging / requirements を参照してください。

3. パッケージをインストール（ローカル開発）
   - pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある親ディレクトリを基準）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN  （J-Quants 用リフレッシュトークン）
   - OPENAI_API_KEY         （OpenAI を直接使う場合。関数引数で指定することも可能）
   - KABU_API_PASSWORD      （kabuステーション API 用）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID （通知用）
   - オプション:
     - KABUSYS_ENV = development | paper_trading | live （デフォルト development）
     - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）

.env の優先順位:
- OS 環境変数 > .env.local > .env
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされます。

（内部の .env パーサは export KEY=VALUE 形式や引用符・インラインコメントに対応しています）

---

## 使い方（代表的な例）

以下はコードから呼び出す簡単な例です。実行前に環境変数や DuckDB の初期スキーマが整っていることを確認してください。

- DuckDB 接続と ETL 実行（日次 ETL）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア付け（OpenAI API キーは環境変数 OPENAI_API_KEY で指定するか、api_key 引数で渡す）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル(signal_events, order_requests, executions) が作成されます
```

- J-Quants の ID トークン取得（内部キャッシュ処理あり）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # JQUANTS_REFRESH_TOKEN を使用して取得
```

注意:
- OpenAI 呼び出しは gpt-4o-mini + JSON Mode を利用する設計です。API レスポンスの検証・リトライを組み込んでいます。
- 実運用環境（live）では KABUSYS_ENV を `live` に設定し、Kabu ステーションやブローカー連携を別モジュール（execution/strategy/monitoring）で実装して下さい。

---

## ディレクトリ構成（主なファイルと説明）

以下は src/kabusys 以下の主要モジュールと概要です（本 README 作成時点での抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（J-Quants / Kabu / Slack / DB パス / 環境判定等）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事を銘柄ごとに集約して LLM に投げ、ai_scores に書き込む
    - regime_detector.py
      - 1321 の MA200 乖離 + マクロニュースで市場レジームを判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API の呼び出し、ページネーション、保存（raw_prices, raw_financials, market_calendar）
    - pipeline.py
      - 日次 ETL と個別 ETL ジョブ（run_prices_etl 等）
    - etl.py
      - ETLResult の公開エントリ（再エクスポート）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存（SSRF 防止やサイズ制限あり）
    - calendar_management.py
      - market_calendar を使った営業日判定、next/prev_trading_day、calendar_update_job
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）と QualityIssue
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログスキーマの DDL と初期化機能
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - （他）
    - strategy, execution, monitoring パッケージは上位 API と連携する箇所（本リポジトリの一部として提供されている場合があります）

---

## 実運用上の注意点

- 環境変数の管理は慎重に。特に J-Quants / OpenAI / Kabu の認証情報は安全なストレージを利用してください。
- DuckDB のファイルパスは settings.duckdb_path で管理されます（デフォルト: data/kabusys.duckdb）。
- OpenAI API 呼び出しにはコストとレート制限が伴います。バッチサイズやリトライ・バックオフはモジュール内で制御されていますが、利用状況に応じた調整を検討してください。
- news_collector は外部 RSS にアクセスするため、SSRF 対策やレスポンスサイズ制限を実装していますが、ネットワーク・ホスト名の制御は導入側で行ってください。
- run_daily_etl 等は DB スキーマ（raw_prices / raw_financials / market_calendar / ai_scores 等）が事前に準備されていることが前提です。初期スキーマ作成手順がある場合はそちらを参照して下さい。

---

README は以上です。必要であれば、各モジュールの API 参考（関数引数の詳細・返り値・例外）やサンプル .env.example を追記します。どの部分を詳細化しましょうか？