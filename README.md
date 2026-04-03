# KabuSys

日本株自動売買プラットフォームのコアライブラリ（リサーチ / データパイプライン / AI スコアリング / 監査ログ等）。  
このリポジトリは、J-Quants API・DuckDB・OpenAI（gpt-4o-mini）などを利用して、データ取得（ETL）、品質チェック、ファクター計算、ニュースセンチメント解析、マーケットレジーム判定、監査ログ保持までを行うことを想定したモジュール群を提供します。

バージョン: 0.1.0

----

## 主要な機能（概要）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得・保存（duckdb への冪等保存）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損値、スパイク、重複、将来日付・非営業日データの検出（qualityモジュール）
- ニュース収集 / 前処理
  - RSS フィード収集、防御的な XML パース・SSRF 対策、URL 正規化（news_collector）
- AI ベースのニュース NLP / レジーム判定
  - ニュースをまとめて OpenAI に投げセンチメントを算出して ai_scores に保存（news_nlp.score_news）
  - ETF（1321）200日MA乖離とマクロセンチメントを統合して市場レジームを判定（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（researchモジュール）
  - 将来リターン計算、IC 計算、ファクター統計（feature_exploration）
- 監査ログ（トレース可能な監査テーブル、発注 → 約定の追跡）
  - DuckDB に監査スキーマを初期化する機能（data.audit.init_audit_db / init_audit_schema）
- 設定管理
  - .env ファイル・環境変数の自動読み込み、アプリケーション設定を提供（config.Settings）

----

## 動作前提 / 必要なライブラリ

- Python 3.10+
- 必須 Python パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

pip などでインストールしてください。例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクト配布に pyproject.toml / requirements.txt がある場合はそちらを使用してください）

----

## 環境変数

設定は .env（および .env.local）または環境変数から読み込まれます。自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を探索して行われます。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（代表）:

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OpenAI（AI API）
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime を実行する際に必要）
- kabuステーション API（発注等）
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベース / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PID_FILE_PATH / KILL_FLAG_PATH など監視用設定
- システム
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL（DEBUG/INFO/...）

実際に必須となるのは使用する機能により変わります（例: score_news を使うなら OPENAI_API_KEY が必須）。環境変数が不足すると Settings プロパティで ValueError が投げられます。

サンプル（.env）:

```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-xxx
KABU_API_PASSWORD=your_kabu_pass
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

----

## セットアップ手順（ローカル開発）

1. リポジトリをクローン

```bash
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境作成・依存インストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# その他、プロジェクトで必要なパッケージがあれば追加でインストール
```

3. 環境変数設定

プロジェクトルートに `.env` を作成または環境変数をエクスポートします（上記サンプル参照）。

4. DuckDB データベース（初回）

必要に応じて DB のディレクトリを作成（Settings.duckdb_path の親ディレクトリ）。監査用 DB を作る場合は init 関数を利用できます（後述）。

----

## 使い方（主要な API 例）

以下は Python REPL やスクリプトから呼び出す例です。

- DuckDB 接続して日次 ETL を実行

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings から duckdb パスを取得する場合
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

# 今日の ETL を実行（id_token を渡すことも可能）
result = run_daily_etl(conn, target_date=date.today(), id_token=None)
print(result.to_dict())
```

- ニュースセンチメント（ai.news_nlp.score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("/path/to/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
print(f"scored {count} symbols")
```

- 市場レジーム判定（ai.regime_detector.score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("/path/to/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
```

- 監査ログ DB の初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査関連テーブルが作成されます
```

- 研究用ファクター計算例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとの辞書リスト
```

注意点:
- AI 関連（score_news / score_regime）は OPENAI_API_KEY が必要です。関数呼び出しで api_key を明示的に渡すこともできます。
- ETL / data.jquants_client は J-Quants のトークン（JQUANTS_REFRESH_TOKEN）を利用して id_token を取得します。

----

## よく使うモジュール / 関数一覧

- kabusys.config
  - settings: 設定オブジェクト（settings.jquants_refresh_token 等）
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.news_collector
  - fetch_rss, preprocess_text（RSS の収集・前処理ロジック）
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(path)

----

## ディレクトリ構成

（プロジェクトの src 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - .env / 環境変数読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント分散処理 / OpenAI 結果バリデーション
    - regime_detector.py  — マクロセンチメント + ETF MA200 で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得＋DuckDB保存）
    - pipeline.py         — ETL ワークフロー（run_daily_etl 等）
    - etl.py              — ETLResult の再エクスポート
    - news_collector.py   — RSS 取得・前処理・保存ロジック
    - quality.py          — データ品質チェック
    - calendar_management.py — 市場カレンダー管理 / 営業日判定ユーティリティ
    - stats.py            — zscore_normalize 等の統計ユーティリティ
    - audit.py            — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility ファクター計算
    - feature_exploration.py  — 将来リターン計算 / IC / 統計サマリー
  - ai/, data/, research/ のそれぞれが実務的な処理単位を持ち分離されています。

----

## 開発・運用上の注意

- ルックアヘッドバイアス対策
  - 多くの関数は内部で date.today() を参照しない、または target_date 未満のデータのみを参照するなどバックテストでのリークを防ぐ設計になっています。外部から target_date を明示的に渡して使用してください。
- 冪等性
  - J-Quants の取得結果は DuckDB へ ON CONFLICT DO UPDATE で保存され、再実行に耐える設計です。
- API レート制限・リトライ
  - J-Quants クライアントは固定間隔スロットリングと指数バックオフを組み合わせてリトライします。OpenAI 呼び出しもリトライロジックを備えています。
- セキュリティ
  - news_collector は SSRF 対策、XML パースの安全化（defusedxml）、受信サイズ制限などの保護を実装しています。
- テスト
  - OpenAI / ネットワーク呼び出しはテスト時にモック可能なように設計されています（内部 API 呼び出しを差し替えやすい）。

----

## 例: シンプルなワークフロー

1. .env を用意して J-Quants / OpenAI のキーを設定
2. DuckDB に接続して run_daily_etl を実行
3. run_daily_etl の後に score_news / score_regime を実行して AI スコアを生成
4. 研究用に research モジュールでファクター計算、IC を評価

----

## ライセンス・貢献

リポジトリに LICENSE ファイルがあればそれに従ってください。バグ修正 / 機能追加の提案は Issue / PR を通じて歓迎します。

----

README に記載されていない細かい実装の振る舞いや引数、戻り値などは各モジュールの docstring を参照してください。必要であれば個別の使い方例（スクリプトテンプレート）や .env.example を別途作成できます。