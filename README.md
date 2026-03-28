# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータプラットフォームと研究・自動売買の基盤ライブラリです。J-Quants API から市場データを取得して DuckDB に保存・品質チェックを行い、NLP（OpenAI）を用いたニュースセンチメントや市場レジーム判定、ファクター計算・分析、監査ログ（発注〜約定のトレース）などの機能を提供します。

主な設計方針:
- ルックアヘッドバイアスを防ぐ（日時を直接参照しない設計）
- DuckDB を主要なローカル DB として採用
- API 呼び出しはレート制御・リトライを備える
- 冪等性（idempotent）を重視した保存処理
- フェイルセーフ（API 失敗時は安全なデフォルトで継続）

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants から株価日足、財務データ、JPX マーケットカレンダーを差分取得・保存（`kabusys.data.jquants_client`, `kabusys.data.pipeline`）
  - ETL の品質チェック（欠損・スパイク・重複・日付不整合）（`kabusys.data.quality`）
- ニュース収集 / NLP
  - RSS 取得・正規化・raw_news への保存（`kabusys.data.news_collector`）
  - ニュースを銘柄ごとに集約して OpenAI でセンチメント評価（`kabusys.ai.news_nlp`）
- 市場レジーム判定
  - ETF（1321）の200日移動平均乖離 + マクロニュースの LLM センチメントを合成（`kabusys.ai.regime_detector`）
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクター算出（`kabusys.research`）
  - 将来リターン・IC・統計サマリー等のユーティリティ（`kabusys.research.feature_exploration`）
- カレンダー管理
  - JPX カレンダーの管理と営業日判定ユーティリティ（`kabusys.data.calendar_management`）
- 監査ログ / トレーサビリティ
  - シグナル → 発注 → 約定まで追跡する監査テーブル定義と初期化（`kabusys.data.audit`）
- 設定管理
  - .env / 環境変数の自動読み込み、必須設定チェック（`kabusys.config`）

---

## 必須環境変数（例）
以下は本ライブラリが参照する主な環境変数の一覧です（README 用要約）。

- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（必須）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live。デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

自動で .env ファイルをルートから読み込みます（優先度: OS 環境 > .env.local > .env）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## インストール

pip と Python 環境（3.10+ 推奨）が必要です。主要な依存例:

- duckdb
- openai
- defusedxml

ローカル開発時はプロジェクトルートで:
```bash
pip install -e ".[dev]"   # もし pyproject / extras が定義されている場合
# または最低限:
pip install duckdb openai defusedxml
pip install -e .
```

（プロジェクトパッケージ化方法に合わせて適宜調整してください）

---

## セットアップ手順

1. リポジトリをクローンし、環境を整える
2. 必要な環境変数を .env に設定（上記参照）
3. DuckDB ファイルの格納先ディレクトリを作成（例: data/）
4. 監査ログ DB 初期化（必要に応じて）

監査 DB を初期化する例:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

ETL 用 DuckDB を用意する例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 必要に応じてスキーマ初期化関数を呼ぶ（本リポジトリに schema 初期化ロジックがある想定）
```

---

## 使い方（主な API と実行例）

以下は代表的な利用例です。各モジュールの関数は DuckDB 接続および target_date を受け取る設計です（ルックアヘッドバイアス対策のため）。

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアを生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で利用
print(f"scored: {count}")
```

- 市場レジームをスコアリングする
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究用ファクター計算（例：モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]
```

- カレンダー周りユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## 注意点 / 運用メモ

- OpenAI 利用
  - gpt-4o-mini を想定したプロンプトと JSON mode を用いる実装が含まれます。API エラーはフェイルセーフでスコア0や空スコアにフォールバックしますが、API キーは必要です。
- J-Quants API 利用
  - リフレッシュトークンを設定しておくと自動で ID トークンを取得・キャッシュします。API はレート制御・リトライを行います。
- DuckDB の executemany やバインドに関する挙動（古いバージョンでの空パラメータの扱いなど）に注意しています。DuckDB のバージョンを合わせておくことを推奨します。
- 自動で .env をプロジェクトルートからロードします。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- ログレベルや KABUSYS_ENV（development/paper_trading/live）によって動作やログ出力を切り替えられます。特に live 環境での実行は十分な注意のうえで行ってください。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールの位置と概要です（src/kabusys 以下）。

- kabusys/
  - __init__.py — パッケージ初期化、バージョン情報
  - config.py — 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（OpenAI）による ai_scores 生成
    - regime_detector.py — マクロ + ETF MA の合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py — ETL パイプラインのエントリポイント（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダーの管理と営業日判定
    - news_collector.py — RSS 取得と前処理・raw_news 保存
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py — z-score 正規化など統計ユーティリティ
    - audit.py — 監査ログ（signal / order_request / executions）定義と初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリーなど

---

## 開発・テスト

- 各モジュールには外部 API 呼び出しやネットワーク依存箇所に対して差し替え（モック）しやすい設計になっています（例: _call_openai_api の差し替え、_urlopen の差し替え等）。
- 単体テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで .env の自動読み込みを無効化できます。

---

この README はコードベースの主要機能と利用方法の概要をまとめたものです。詳細は各モジュールの docstring を参照してください。必要であれば、セットアップに使う具体的な requirements.txt、スキーマ初期化 SQL、運用手順（cron / Airflow など）についても追記できます。