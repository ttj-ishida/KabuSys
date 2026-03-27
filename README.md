# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI 連携）によるセンチメント算出、ファクター・リサーチ、監査ログ（注文 → 約定のトレーサビリティ）、データ品質チェック等を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の定量投資・自動売買に必要となるデータ基盤と研究用ユーティリティ群をまとめた Python パッケージです。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー取得（差分 ETL、ページネーション、リトライ、レート制御）
- RSS 等からのニュース収集と前処理、OpenAI を使ったニュース/マクロセンチメント評価
- 市場レジーム判定（ETF MA と LLM センチメントの合成）
- ファクター計算・将来リターン・IC などのリサーチユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル、発注リクエスト、約定）用スキーマ初期化ユーティリティ
- DuckDB を中心とした永続化インターフェース

設計上の注意点として「ルックアヘッドバイアス」を防ぐ実装方針（日時取得の制御、DB クエリの排他条件など）が随所に組み込まれています。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants からの株価日足、財務データ、JPX マーケットカレンダー取得（fetch_* 系）
  - 差分更新・バックフィル・保存（save_* 系、DuckDB への冪等保存）
  - 日次 ETL パイプライン run_daily_etl

- ニュース収集 / NLP
  - RSS フィード取得と前処理（news_collector）
  - OpenAI（gpt-4o-mini）を用いたニュースごとのセンチメント算出（news_nlp.score_news）
  - マクロニュース + ETF MA を使った市場レジーム判定（regime_detector.score_regime）

- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン算出、IC 計算、統計サマリー（research.feature_exploration）
  - Z スコア正規化などの統計ユーティリティ（data.stats）

- データ品質管理
  - 欠損・スパイク・重複・日付不整合検出（data.quality）
  - run_all_checks による一括実行

- カレンダー管理
  - market_calendar を用いた営業日判定・次/前営業日探索（data.calendar_management）
  - JPX カレンダーの夜間差分更新処理（calendar_update_job）

- 監査ログ（Audit）
  - signal_events / order_requests / executions のテーブル定義・初期化（data.audit）
  - DuckDB 用に冪等でスキーマ作成、監査 DB 初期化 util（init_audit_db）

- 設定管理
  - .env 自動読み込み（プロジェクトルート探索）
  - 環境変数ラッパ（kabusys.config.settings）で各種キー・パスを取得

---

## セットアップ手順

1. 必要環境
   - Python 3.10 以上（型アノテーションの | 演算子等を使用）
   - DuckDB（Python パッケージ）
   - OpenAI SDK（openai）
   - defusedxml（RSS パースの安全対策）
   - その他ネットワーク/HTTP 標準ライブラリを使用

2. リポジトリをクローン（例）
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

3. 仮想環境の作成と有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

4. 依存パッケージをインストール（例）
   - requirements.txt がある場合:
     ```bash
     pip install -r requirements.txt
     ```
   - 主要パッケージ例:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発時はパッケージを編集モードでインストール:
     ```bash
     pip install -e .
     ```

5. 環境変数の設定
   - プロジェクトルート（.git か pyproject.toml がある階層）に `.env` または `.env.local` を置くと自動で読み込まれます（読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID      : 通知先チャンネル ID（必須）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector で使用）
     - KABUSYS_ENV           : environment（development / paper_trading / live）
     - LOG_LEVEL             : ログレベル（DEBUG/INFO/...）

---

## 使い方（基本例）

以下は一例です。各関数はテストしやすいように API キー注入や接続注入が可能です。

- DuckDB 接続を開く（設定からパスを取得）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成（OpenAI API キーは環境変数または api_key 引数で指定）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（モメンタム等）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

- 監査ログ（監査 DB 初期化）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

- RSS を取得して raw_news に保存するフローは news_collector を参照してください（fetch_rss → 保存ロジック）。

---

## .env の自動読み込みと無効化

- パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を順に読み込みます。
- 読み込み優先順位: OS 環境 > .env.local > .env
- 自動ロードを無効化したい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

.env の書式はシェル互換（export を許容、クォートやコメント処理あり）です。

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py  -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py        -- ニュース NLP（OpenAI 統合、ai_scores へ書き込み）
    - regime_detector.py -- マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（fetch/save 系）
    - pipeline.py            -- ETL パイプライン (run_daily_etl 等)
    - etl.py                 -- ETLResult の公開
    - news_collector.py      -- RSS 取得・前処理・保存
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py -- マーケットカレンダー管理
    - audit.py               -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py -- 将来リターン/IC/サマリー/ランク関数

その他: logging 設定や CLI ラッパーはプロジェクト外（または今後追加）を想定しています。

---

## 開発・テスト時の留意点

- OpenAI / J-Quants など外部 API 呼び出しはエラー耐性（リトライ・フェイルセーフ）を備えていますが、ユニットテストではモックを利用してください。コード内にもモック差し替えを想定したポイント（_call_openai_api の差し替え等）が用意されています。
- DuckDB の executemany はバージョン依存の挙動があるため空リストでの呼び出しを避ける実装になっています（pipeline, news_nlp など）。
- 日付・時間はできるだけ明示的に扱い、ルックアヘッドバイアスを避けるために date 引数を外部から注入する設計です。内部で date.today() や datetime.today() を直接使わない関数を優先して使用してください。

---

## ライセンス・貢献

（このテンプレートにはライセンス表記が含まれていません。実際のリポジトリでは LICENSE を追加してください。）  

バグ報告、改善提案、プルリクエスト歓迎です。大きな変更を加える前に issue を立てて概要を共有してください。

---

必要であれば、README に具体的な例（.env.example、CLI 実行例、データベーススキーマの詳細）を追記できます。どの部分を詳しく追加したいか教えてください。