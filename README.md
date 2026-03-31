# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを含むモジュール群を提供します。

主なユースケース:
- J-Quants API からの株価・財務・カレンダーの差分 ETL
- RSS ニュース収集と LLM による銘柄ごとのセンチメント付与
- ETF / マクロ情報を組み合わせた市場レジーム判定
- ファクター計算・特徴量探索（リサーチ用途）
- 発注監査ログ用の DuckDB スキーマ初期化

---

## 機能一覧

- 環境・設定管理
  - .env ファイル / OS 環境変数から設定を読み込む（自動読み込み機能あり）
- データ ETL（kabusys.data.pipeline）
  - J-Quants API から日次株価、財務、JPX カレンダーを差分取得して DuckDB に保存
  - 品質チェック（欠損・スパイク・重複・日付不整合検出）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの収集、前処理、raw_news への冪等保存
  - SSRF 対策、受信サイズ制限、トラッキングパラメータ除去 等の堅牢化
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコア付与
  - バッチ/リトライ/レスポンス検証を含む堅牢な実装
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成してレジーム判定
  - LLM 呼び出しのフェイルセーフ、冪等 DB 書き込み
- リサーチ（kabusys.research）
  - momentum, value, volatility 等のファクター計算
  - 将来リターンの計算、IC（Information Coefficient）や統計サマリー
  - z-score 正規化ユーティリティ（kabusys.data.stats）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化ヘルパー
  - 監査用 DuckDB の初期化関数を提供
- J-Quants クライアント（kabusys.data.jquants_client）
  - API レート制御、リトライ、ID トークン自動更新、DuckDB への冪等保存

---

## 要求事項 / 前提

- Python 3.10+
  - （型ヒントに | 演算子を使用しているため）
- 主な外部依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- J-Quants API（リフレッシュトークン）と OpenAI API キーが必要
- DuckDB をローカルファイルまたは :memory: で利用

---

## 環境変数 / .env

パッケージは起動時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動読み込みします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使用する環境変数（必須は README 内で明示）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（設定インターフェース用）
- SLACK_BOT_TOKEN (必須)
  - Slack 通知に利用する Bot トークン
- SLACK_CHANNEL_ID (必須)
  - 通知先チャンネル ID
- OPENAI_API_KEY
  - OpenAI を利用する関数に渡す API キー（引数で上書き可能）
- DUCKDB_PATH (任意, デフォルト data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト INFO)

必須変数が未設定の場合、kabusys.config.Settings の該当プロパティ参照時に ValueError が発生します。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）
   - 開発中は editable install:
     - pip install -e .

4. .env を作成
   - リポジトリルートに `.env`（または `.env.local`）を作成し、上記の必須値を設定

5. DuckDB 用データディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要 API と実行例）

※ いくつかの関数は DuckDB 接続オブジェクトを受け取ります。以下は簡単な使用例です。

1) DuckDB 接続を作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) ETL（日次）を実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- ETL は市場カレンダー → 株価 → 財務 → 品質チェックの順で実行します。
- J-Quants の id_token は settings.jquants_refresh_token を使って自動取得します。

3) ニュースセンチメント（銘柄ごと）を取得して ai_scores テーブルに格納
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数 or api_key 引数
print(f"wrote scores for {n_written} codes")
```

4) 市場レジーム判定を実行
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 研究用ファクター計算例
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)

# z-score 正規化
mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

6) 監査ログスキーマ初期化（発注監査用 DB）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# conn_audit は監査ログ用の接続
```

---

## 補足・設計上の注意点

- Look-ahead バイアス対策
  - 多くの関数（ETL、NLP、レジーム判定、リサーチ）は datetime.today()/date.today() を内部参照しない設計です。target_date を明示的に渡すことでバックテスト等でのルックアヘッドを防止します。
- OpenAI 呼び出し
  - OpenAI API 呼び出しは gpt-4o-mini を使用想定（JSON Mode で厳密な JSON 応答を期待）。リトライ・バックオフ処理、レスポンス検証を含みます。API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用します。
- J-Quants API
  - rate limit（120 req/min）遵守のため内部で簡易レートリミッタを実装しています。401 受信時はリフレッシュトークンを使って自動リフレッシュします。
- ニュース収集の安全対策
  - RSS フェッチ時に SSRF 対策、最大受信バイト数制限、Gzip 解凍後のサイズ検査等を行っています。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - etl.py (公開インターフェース; ETLResult を再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (パッケージトップで __all__ に含めているが、実装はプロジェクト内を参照してください)
  - strategy/, execution/, など（パッケージ公開用 __all__ に含まれています）

---

## 開発・テスト時のヒント

- 自動で .env ファイルを読み込みます。テスト時に自動ロードを無効化するには:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- OpenAI / J-Quants の外部呼び出し部分は関数が分離されているため unittest.mock でモックしやすく、CI ではネットワーク呼び出しを遮断してテスト可能です。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン依存の問題に注意（コード内でチェック済み）。

---

必要があれば、README に実行可能なサンプルスクリプトや docker-compose / GitHub Actions 用のワークフロー例を追記できます。どの部分の利用例を詳しく載せるか指定してください。