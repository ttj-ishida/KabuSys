# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
J-Quants からのマーケットデータ取得・ETL、ニュース収集と LLM によるニュースセンチメント評価、ファクター計算・リサーチユーティリティ、監査ログ（オーダー〜約定のトレーサビリティ）などを備えたモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアスを避ける」「DuckDB を中心としたローカルデータ管理」「API 呼び出しに対する堅牢な再試行／フェールセーフ」「ETL と品質チェックの分離」です。

バージョン: 0.1.0

---

## 主な機能

- データ収集・ETL（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存（ページネーション対応、冪等保存）
  - ETL 結果を集約した ETLResult を返す run_daily_etl
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合などのチェック（QualityIssue 型で報告）
- ニュース収集と前処理
  - RSS フィード収集（SSRF 対策、URL 正規化、トラッキング除去）
  - raw_news / news_symbols テーブルへの冪等保存を想定
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に投げてセンチメントを算出し ai_scores に保存（score_news）
  - マクロニュースを評価して市場レジーム（bull/neutral/bear）を判定（score_regime）
  - LLM 呼び出しは冪等的かつリトライ付き、失敗時はフォールバックを行う設計
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（スピアマン相関）計算、ファクター統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義・初期化（init_audit_schema / init_audit_db）
  - 発注→約定の UUID ベースのトレーサビリティ設計
- カレンダー管理
  - market_calendar を使った営業日判定、next/prev_trading_day、get_trading_days、calendar_update_job

---

## 動作要件（推奨）

- Python 3.10+
- 依存パッケージ（少なくとも下記が必要）
  - duckdb
  - openai (OpenAI の Python SDK)
  - defusedxml
  - （標準ライブラリ以外の追加があれば requirements.txt を参照してください）

※実行する機能に応じて外部 API キー（J-Quants, OpenAI, kabu ステーション 等）やネットワークアクセスが必要です。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンしてワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール  
   （プロジェクトに requirements.txt がある場合はそれを使用。なければ最低限下記をインストール）
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config モジュールの自動ロード）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限設定が必要な環境変数（一部）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須: J-Quants API を使う場合）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注系を使う場合）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を使う場合
   - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH: Paper Trading 設定
   - KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")
   - LOG_LEVEL: ログレベル ("DEBUG","INFO",...)

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡単なサンプル）

下記はライブラリを直接利用する Python コードの例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続の作成と ETL 実行（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# DuckDB ファイルへ接続
conn = duckdb.connect("data/kabusys.duckdb")

# ETL を実行（target_date を指定しない場合は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア計算（OpenAI が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

- 市場レジームの判定（ETF 1321 の MA200 とマクロ記事）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ（audit）DB 初期化
```python
from kabusys.data.audit import init_audit_db

# :memory: も可、ファイルパスを指定すると親ディレクトリを自動作成する
conn = init_audit_db("data/audit_duckdb.db")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- J-Quants データ取得の直接利用例
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

# id_token を明示的に取得するか、モジュールキャッシュを使う
token = get_id_token()  # settings.jquants_refresh_token が必要
records = fetch_daily_quotes(id_token=token, date_from=date(2026, 3, 1), date_to=date(2026, 3, 20))
```

---

## 自動 .env ロードの挙動

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `.env` のパースはシェルライク（export を許容、クォート・コメント処理あり）です。

---

## 開発時の注意点・設計上のポイント

- ルックアヘッドバイアス防止: 多くのモジュール（news_nlp, regime_detector, research 等）は date / target_date を明示的に受け取り、内部で datetime.today() や date.today() を直接参照しないよう設計されています。バックテストでは必ず過去のデータのみを利用するよう注意してください。
- API 呼び出しはリトライやバックオフを備えており、致命的な失敗時はフォールバック（スコア 0.0 など）する実装が多くあります。これによりバッチ処理が途中で止まらないように設計されています。
- DuckDB を中心としたテーブル設計（raw_prices, raw_financials, market_calendar, raw_news, ai_scores, market_regime, audit テーブル等）を前提に実装されています。初回はスキーマを用意する必要があります（schema 初期化機能は別モジュール想定）。

---

## ディレクトリ構成（主要ファイル）

以下はソースの主要モジュールと役割の概要です（src/kabusys 以下）。

- __init__.py
  - パッケージ定義、version
- config.py
  - 環境変数 / .env 読み込み、Settings クラス（各種設定プロパティ）
- ai/
  - news_nlp.py : ニュースの LLM ベースのセンチメント付与（score_news）
  - regime_detector.py : ETF MA200 とマクロ記事の LLM 評価で市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py : ETL パイプライン実装（run_daily_etl 等）、ETLResult
  - etl.py : ETLResult を再エクスポート
  - news_collector.py : RSS 取得・前処理・SSRF 対策
  - calendar_management.py : market_calendar 管理、営業日判定、calendar_update_job
  - quality.py : データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - audit.py : 監査ログテーブル定義と初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py : Momentum / Volatility / Value のファクター計算
  - feature_exploration.py : 将来リターン、IC、rank、summary 等

（上記以外にも strategy / execution / monitoring のパッケージ用意を想定する設計になっていますが、今回提示されたコードでは主に data / ai / research 周りの実装が含まれています）

---

## 追加情報 / TODO

- テストスイート、CI、requirements.txt / pyproject.toml の整備を推奨します。
- 実運用で発注・約定を行う場合は、kabu ステーション API 周りのクライアント実装・安全対策（逆指値・成行の挙動等）と実証（Paper Trading）を十分に行ってください。
- ニュース取得元や OpenAI API 呼び出しはコストがかかるため、バッチ頻度・バッチサイズの設計を検討してください。

---

必要であれば、README に含める .env.example のテンプレートや、DuckDB 用のスキーマ初期化サンプル、よく使う CLI スクリプト例（etl_runner.py など）の雛形も作成できます。どの追加情報が要りますか？