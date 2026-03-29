# KabuSys — 日本株自動売買プラットフォーム（簡易 README）

短い概要と使い方をまとめた README です。プロジェクトは日本株向けのデータプラットフォーム・リサーチ・AIスコアリング・監査ログ・ETL を含むライブラリ群で、主に DuckDB と外部 API（J-Quants / OpenAI / RSS）を組み合わせてデータ収集・品質管理・特徴量作成・シグナル→発注の監査までをサポートします。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- 必要な環境変数（.env）
- セットアップ手順
- 使い方（代表的な API / ワークフロー例）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は以下の要素を含む日本株向けの自動売買／データ分析基盤用 Python パッケージです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL（duckdb へ保存、冪等化）
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去、記事 ID のハッシュ化）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント解析（銘柄別 / マクロ）
- 市場レジーム判定（ETF 1321 の MA200 乖離 × LLM マクロスコアの合成）
- リサーチ用ファクター計算（Momentum / Value / Volatility 等）と特徴量探索（forward returns, IC）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events / order_requests / executions）と初期化ユーティリティ

設計上の特徴:
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() に依存しない設計）
- DuckDB ベースの効率的なバッチ処理（SQL + Python）
- 冪等性と堅牢なリトライ戦略（API 呼び出し時の指数バックオフ等）
- セキュリティ考慮（RSS の SSRF 対策、defusedxml 等）

---

## 主な機能一覧
- data/jquants_client: J-Quants からのデータ取得および DuckDB へ保存（raw_prices, raw_financials, market_calendar 等）
- data/pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（ETL パイプライン）
- data/news_collector: RSS 収集・正規化・raw_news / news_symbols への保存ロジック
- ai/news_nlp: ニュースを LLM で銘柄別にスコアリング（score_news）
- ai/regime_detector: ETF + マクロニュースを組み合わせて市場レジームを判定（score_regime）
- research: ファクター計算（calc_momentum, calc_value, calc_volatility 等）と特徴量解析（forward returns, IC）
- data/quality: 品質チェック（欠損、重複、スパイク、日付不整合）
- data/audit: 監査テーブル定義・初期化ユーティリティ（init_audit_schema / init_audit_db）
- config: .env 自動読み込み、設定ゲッター（settings オブジェクト）

---

## 必要な環境変数（.env）
プロジェクト起点で `.env` / `.env.local` を置くことで自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主要な必須キー（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注・ブローカー連携用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（AI スコアリングで使用）

その他（任意/デフォルトあり）:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

例（.env.example）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

前提:
- Python 3.10 以上（Union types・型注釈に | を使用）
- ネットワーク接続（J-Quants / OpenAI / RSS ソース）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（最低限の依存）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。

4. `.env` を作成して必要な環境変数を設定
   - リポジトリルートに `.env` / `.env.local` を置くと自動で読み込まれます（config モジュール）
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

5. DuckDB の初期テーブル作成（監査テーブルなど）
   - 監査テーブルのみ初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # ファイルパスまたは ":memory:"
     conn.close()
     ```
   - 実際のスキーマ初期化は各モジュールに対応する DDL 初期化関数を呼んでください（例: data.schema.init_schema() を用意している可能性）

---

## 使い方（代表例・コードスニペット）

以下は代表的な操作例です。全て Python スクリプトから呼び出せます。

- DuckDB に接続して日次 ETL を実行する
```python
from kabusys.config import settings
import duckdb
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニュースの AI スコアリングを実行する（score_news）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env の OPENAI_API_KEY を使う
print("scored:", n_written)
conn.close()
```

- 市場レジーム判定を実行する（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を使用
conn.close()
```

- 監査 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルなどが作成されます
conn.close()
```

- ファクター計算・IC 計算（研究用）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026,3,20)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
conn.close()
```

注意点:
- API キーは必須（OpenAI / J-Quants）。score_* 関数には api_key を明示的に渡せますが、省略すると環境変数 `OPENAI_API_KEY` を参照します。
- DuckDB の接続オブジェクトは各関数へ直接渡す設計です（トランザクション管理に注意）。
- LLM 呼び出しの失敗はフェイルセーフでスコアを 0 にする等の設計が一部にあります（ログを確認してください）。

---

## ディレクトリ構成（主要ファイル）
リポジトリの `src/kabusys` 以下の主要モジュールを抜粋します。

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py        # 銘柄別ニューススコアリング（score_news）
  - regime_detector.py # マクロ + ETF による市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py  # J-Quants API クライアント（取得 & DuckDB 保存）
  - pipeline.py        # ETL パイプライン（run_daily_etl 等）
  - etl.py             # ETLResult の再エクスポート
  - news_collector.py  # RSS 収集と前処理
  - quality.py         # データ品質チェック
  - audit.py           # 監査テーブル定義・初期化
  - calendar_management.py # 市場カレンダー管理・営業日ユーティリティ
  - stats.py           # 共通統計ユーティリティ（zscore_normalize）
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記以外に strategy / execution / monitoring 等のパッケージ境界が想定されています。パッケージの __all__ は kabusys/__init__.py を参照してください。）

---

## 運用上の注意
- 実口座（live）環境での発注・取引を行う場合は `KABUSYS_ENV=live` に設定し、十分なテストと監査ログの整備を行ってください。
- OpenAI API の利用はレート・コストが発生します。バッチサイズや呼び出し頻度は運用ポリシーに合わせて調整してください（news_nlp 内でバッチ上限や再試行ロジックを実装済み）。
- J-Quants API はレート制限（120 req/min）があるため jquants_client の RateLimiter を使って安全に制御しています。独自で API を呼ぶ場合は注意してください。
- RSS の取得は外部 URL の扱いと SS R F 対策（ホストプライベートチェック、リダイレクト検査）を行っていますが、運用時は信頼できるソースリストのみを利用することを推奨します。

---

この README はコードベースからの要点を抜粋して作成しました。詳細な API ドキュメントや運用手順は個別モジュール（src/kabusys/**）の docstring とログメッセージを参照してください。必要であれば README に CI / デプロイ手順や更に詳しいサンプルを追記します。