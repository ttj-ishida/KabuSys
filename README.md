# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
データ収集（J-Quants）、品質チェック、ニュースNLP（OpenAI）による銘柄センチメント評価、マーケットレジーム判定、研究（ファクター計算）および監査ログ（発注→約定のトレーサビリティ）を提供します。

## 主な特徴
- J-Quants API 経由の差分 ETL（株価・財務・市場カレンダー）と品質チェック
- RSS 収集 + 前処理 + 銘柄紐付け（raw_news / news_symbols）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）スコアリング
- マクロニュースと ETF（1321）の200日MA乖離を組み合わせた市場レジーム判定
- 研究用ユーティリティ（モメンタム、ボラティリティ、バリュー、将来リターン、IC 等）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- DuckDB をデータレイクとして採用（冪等保存、トランザクション対応）
- 自動的な .env 読み込み（プロジェクトルートの .env / .env.local を優先）

---

## 機能一覧（要約）
- データ取得/保存
  - J-Quants から株価（daily_quotes）、財務（statements）、上場情報、マーケットカレンダーを取得・保存（jquants_client）
  - 差分 ETL / 日次 ETL（data.pipeline.run_daily_etl）
- データ品質
  - 欠損、重複、未来日、スパイク検出などの品質チェック（data.quality）
- ニュース処理
  - RSS 取得・正規化・脆弱性対策（news_collector）
  - ニュースを銘柄ごとにまとめ OpenAI でスコア（ai.news_nlp.score_news）
- マーケットレジーム
  - ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成（ai.regime_detector.score_regime）
- 研究（research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / zscore_normalize 等
- 監査ログ（audit）
  - 監査用スキーマ作成・初期化（init_audit_schema / init_audit_db）

---

## 必要条件・依存関係
- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

インストール例:
```bash
python -m pip install duckdb openai defusedxml
```
（プロジェクトに requirements.txt がある場合はそれに従ってください）

---

## 環境変数 / 設定
アプリは .env（および .env.local）または環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml の存在）を基準に行われます。自動ロードを無効化するには環境変数を設定します:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（README 用抜粋）:
- JQUANTS_REFRESH_TOKEN … J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY … OpenAI API キー（AI 機能で必須）
- KABU_API_PASSWORD … kabuステーション API パスワード
- KABU_API_BASE_URL … kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN … Slack Bot Token（通知用）
- SLACK_CHANNEL_ID … Slack チャネル ID
- DUCKDB_PATH … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH … SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV … 環境 ("development", "paper_trading", "live")
- LOG_LEVEL … ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

アプリケーションコードからは `from kabusys.config import settings` で参照できます。例:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## セットアップ手順（開発環境向け）
1. リポジトリをクローンして作業ディレクトリに移動
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
4. プロジェクトルートに .env を作成（.env.example を参考）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   ※ 開発時は .env.local を使ってローカル上書きできます（.env.local が優先されます）。

5. DuckDB 用ディレクトリが必要な場合は自動作成されますが、手動で作成しておいてもよいです:
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要なAPI例）

以下は Python スクリプト・REPL からの利用例です。すべて内部の DuckDB 接続（duckdb.connect）を渡して操作します。

共通インポート:
```python
import duckdb
from datetime import date
from kabusys.config import settings
```

1) ETL（日次パイプライン）の実行
```python
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

2) ニュースセンチメント（銘柄別）スコアリング
```python
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n = score_news(conn, target_date=date(2026, 3, 19))  # 前日15:00〜当日08:30 JST の記事をスコア化
print(f"scored {n} symbols")
```
- OpenAI API キーは `OPENAI_API_KEY` 環境変数か `api_key` 引数で指定可能。

3) マーケットレジーム判定
```python
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 19))
```
- 内部で ETF 1321 の MA200 乖離とマクロ記事の LLM スコアを合成。OpenAI キーは環境変数または引数で渡します。API エラー時はフェイルセーフ（macro_sentiment=0.0）。

4) 研究向けファクター取得
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
conn = duckdb.connect(str(settings.duckdb_path))
moms = calc_momentum(conn, date(2026, 3, 19))
vals = calc_value(conn, date(2026, 3, 19))
vols = calc_volatility(conn, date(2026, 3, 19))
```

5) 監査ログ DB 初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
# これで signal_events, order_requests, executions テーブルとインデックスが作成されます
```

6) カレンダー・営業日ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
conn = duckdb.connect(str(settings.duckdb_path))
is_trade = is_trading_day(conn, date(2026,3,20))
next_trade = next_trading_day(conn, date(2026,3,20))
```

---

## 注意点 / 実装上の要約
- Look-ahead バイアス対策:
  - 多くの関数は内部で date.today()/datetime.today() を直接参照しないか、target_date を明示的に取ります（バックテストでの誤用を防止）。
  - J-Quants レコードは fetched_at を UTC で保存することで「いつデータが利用可能になったか」を追跡できます。
- OpenAI 呼び出し:
  - gpt-4o-mini（JSON Mode）を利用。
  - レスポンスパースエラーや API エラー時はフェイルセーフ（0.0）で継続する設計。
- .env の自動読み込み:
  - OS 環境 > .env.local > .env の順で読み込み。自動ロードはプロジェクトルートが検出できない場合スキップされます。
- J-Quants API:
  - Rate limit（120 req/min）に合わせた RateLimiter を内蔵。
  - 401 時は自動でトークン再取得（1回のみ）してリトライ。
  - ページネーション対応してデータをまとめて取得。

---

## ディレクトリ構成（主要ファイル）
（抜粋・要約）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py  — ニュースセンチメント（銘柄別）
    - regime_detector.py  — マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得＋保存）
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - etl.py  — ETL 型再エクスポート（ETLResult）
    - news_collector.py  — RSS 収集・前処理
    - quality.py  — 品質チェック
    - calendar_management.py  — 市場カレンダー / 営業日判定
    - stats.py  — 汎用統計（zscore_normalize）
    - audit.py  — 監査ログスキーマ/初期化
  - research/
    - __init__.py
    - factor_research.py  — momentum / volatility / value
    - feature_exploration.py  — forward returns / IC / factor summary

---

## よくある操作のヒント
- OpenAI 呼び出しのテストでは、モジュール内の _call_openai_api をモックしてテストを容易にできます（news_nlp/regime_detector にそれぞれ独立実装があります）。
- DuckDB executemany は空のリストを渡せない部分があるため、パラメータが空でないか事前チェックしています（互換性対策）。
- news_collector は SSRF・XML Bomb・大容量レスポンス等に対する保護を行っています（defusedxml, 許可スキームチェック, レスポンスサイズ上限など）。

---

この README はコードベースの主要な利用方法・注意点をまとめたものです。実行時の詳細なログや追加のユーティリティは各モジュールの docstring を参照してください。必要でしたら、具体的なワークフロー（例: daily ETL を cron で回す設定、Slack 通知を組み合わせる例）や CLI ラッパーの雛形も作成します。ご希望あれば教えてください。