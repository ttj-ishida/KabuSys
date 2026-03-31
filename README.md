# KabuSys

KabuSys は日本株向けのデータパイプライン・リサーチ・AI支援市場判定・監査ログ・ETL・ニュース収集・自動売買補助を目的とした Python パッケージです。内部的には DuckDB をデータレイクとして利用し、J-Quants API や RSS、OpenAI（gpt-4o-mini）など外部サービスと連携してデータ収集→品質検査→特徴量生成→AIスコアリング→監査ログまでをカバーします。

主な用途例：
- J-Quants からの株価 / 財務 / カレンダーの差分ETL
- RSS ニュースの収集と銘柄単位の NLP スコアリング（OpenAI）
- マクロセンチメントと MA を組み合わせた市場レジーム判定
- ファクター（Momentum / Value / Volatility 等）の計算と特徴量探索
- データ品質チェック・監査テーブルの初期化・運用補助

---

## 機能一覧

- データ取得・ETL
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動更新、レート制御）
  - run_daily_etl による日次 ETL（株価/財務/カレンダー）
  - ETL 結果を表す ETLResult クラス

- ニュース関連
  - RSS から記事を収集して raw_news に保存（SSRF / Gzip / トラッキング除去対策）
  - ニュースの前処理（URL 除去・空白正規化）
  - OpenAI を用いた銘柄別ニュースセンチメント（kabusys.ai.news_nlp.score_news）

- AI / レジーム判定
  - ニュース NLP（銘柄毎スコア）: gpt-4o-mini を JSON mode で利用、バッチ/リトライ制御
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント合成）: kabusys.ai.regime_detector.score_regime

- Research（研究用）
  - ファクター計算: Momentum / Value / Volatility（prices_daily / raw_financials ベース）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化ユーティリティ

- データ品質
  - 欠損、スパイク、重複、日付不整合などを検出する quality モジュール
  - run_all_checks でまとめて実行

- カレンダー管理
  - market_calendar の取得 / 営業日判定 / next/prev_trading_day / get_trading_days

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル作成・初期化ユーティリティ
  - init_audit_db / init_audit_schema による冪等初期化

- 設定管理
  - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml を基準）
  - 環境変数をラップした settings オブジェクト

---

## 前提・依存関係

必須（一例）
- Python 3.10+
- duckdb
- openai
- defusedxml

インストール後に利用する主なパッケージ：
- duckdb: ローカル DB
- openai: LLM 呼び出し
- defusedxml: RSS パースの安全化

（実際の依存は setup/pyproject に記載してください）

---

## セットアップ手順

1. リポジトリをクローン / コピー
   - 例: git clone <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 開発インストール
   - python -m pip install -e .      # プロジェクトルートに pyproject.toml / setup.py がある前提

4. 依存パッケージを個別にインストール（pyproject がない場合）
   - pip install duckdb openai defusedxml

5. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動的に読み込まれます（読み込み優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabu ステーション API のパスワード（発注連携がある場合）
- SLACK_BOT_TOKEN       : Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知チャンネル ID
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 実行時に必須）

設定項目（デフォルトあり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
- DUCKDB_PATH: DuckDB 保存先のパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）

.env のサンプル（例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本例）

以下は Python REPL やスクリプトでの簡単な利用例です。

1) DuckDB 接続を作って日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB ファイルに接続（ファイルがなければ作成）
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を実行（target_date を指定しないと今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

2) ニュースセンチメントをスコアリング（OpenAI API key が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査専用 DB を初期化（ファイルを指定、":memory:" も可）
audit_conn = init_audit_db(settings.duckdb_path)  # 必要に応じて別パスに変更
```

5) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意点:
- LLM 呼び出し（score_news / score_regime）は OpenAI API キー（OPENAI_API_KEY）を必要とします。関数引数で api_key を明示的に渡すことも可能です。
- ETL / データ保存は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news 等）を前提とします。スキーマ初期化は別途スクリプトで行ってください（本 README には DDL の全体は含めていませんが、data.audit.init_audit_schema のような初期化ヘルパーが用意されています）。

---

## ディレクトリ構成（主なファイル・モジュール）

（ルート: src/kabusys 以下）

- __init__.py
- config.py
  - 環境変数の読み込み・検証・settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py         : 銘柄別ニューススコアリング（OpenAI 呼び出し・バッチ処理）
  - regime_detector.py  : ETF MA + マクロニュースで日次レジーム判定
- data/
  - __init__.py
  - calendar_management.py : JPX カレンダー管理、営業日判定
  - etl.py                 : ETLResult の再エクスポート
  - pipeline.py            : ETL パイプライン（run_daily_etl 等）
  - stats.py               : zscore_normalize 等の統計ユーティリティ
  - quality.py             : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py               : 監査ログテーブル DDL / 初期化ユーティリティ
  - jquants_client.py      : J-Quants API クライアント（取得・保存関数）
  - news_collector.py      : RSS 収集・前処理・保存ユーティリティ
- research/
  - __init__.py
  - factor_research.py     : Momentum / Value / Volatility 等ファクター計算
  - feature_exploration.py : 将来リターン計算 / IC / 統計サマリー 等

---

## 設計・運用に関する注意点

- Look-ahead bias（将来情報の漏洩）対策が各所に組み込まれています（target_date 未満/以前のデータのみ参照、fetched_at の記録など）。
- OpenAI や J-Quants 呼び出しにはリトライ・バックオフ・レート制御が組み込まれています。失敗時はフェイルセーフとしてゼロスコア化やスキップで継続する設計です。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時や特別な状況では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- DuckDB の executemany はバージョンによって挙動が異なるため（空リスト不可等）、コード内で注意してハンドリングしています。

---

## 貢献・拡張

- 新しい ETL ソースの追加（jquants_client の拡張 & save_* の追加）
- 監査/発注のフロー実装（order_requests を発行して broker 経由で執行するロジック）
- 研究用モジュールの追加（ファクター検証・最適化スクリプト）
- テスト追加: 各モジュールは依存性注入（例: OpenAI client / _call_openai_api のモック）を想定した設計になっています。

---

質問・補足や README に追加したい使い方があれば教えてください。README のサンプル .env.example や初期スキーマの作成手順（DDL）を追記することも可能です。