# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ。  
DuckDB をデータ層に採用し、J-Quants API からの ETL、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ」「API 呼び出しの堅牢化（リトライ/バックオフ/レート制限）」「DuckDB を用いた SQL ベース処理」です。

---

## 機能一覧

- 環境設定管理
  - .env ファイルと OS 環境変数から設定を読み込む（自動ロード・上書きロジックあり）
- データ ETL（J-Quants）
  - 株価（日足：OHLCV）、財務データ、JPX カレンダーの差分取得・保存
  - 差分取得、バックフィル、ページネーション対応、トークンリフレッシュ、レート制御、冪等保存
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などのチェック
- ニュース収集
  - RSS フィードから記事を取得 → 前処理 → raw_news に冪等保存
  - SSRF 対策、XML パースの安全化、受信サイズ制限等を実装
- ニュースNLP（OpenAI）
  - 銘柄ごとのニュースを集約して LLM（gpt-4o-mini）でセンチメントを算出し ai_scores に保存
  - チャンク処理、リトライ、レスポンス検証、±1.0 のクリッピング
- 市場レジーム判定
  - ETF（1321）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime に記録
  - フェイルセーフやリトライ実装あり
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブル定義・初期化を提供
  - UUID ベースのトレーサビリティ、UTC タイムスタンプ管理

---

## 要件

- Python 3.10 以上（型記法（|）やその他構文の利用のため）
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

※ 実際の `pyproject.toml` / `requirements.txt` があればそちらに従ってください。

---

## セットアップ手順

1. リポジトリをクローン / コードを配置

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは pyproject.toml / requirements.txt を用意して pip install -r requirements.txt / pip install . を推奨します。

4. 環境変数 / .env を用意

   自動ロードはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に `.env` と `.env.local` を読み込みます。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API の base URL（省略時: http://localhost:18080/kabusapi）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で利用）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知関連（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（省略時: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視関連
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
   - KABUSYS_ENV: environment。許容値: development, paper_trading, live（省略時: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（省略時: INFO）

   .env の例（プロジェクトルート）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   ```

---

## 使い方（サンプル）

以下は最小の呼び出し例です。各例は DuckDB 接続を受け取るので、ローカルファイルや :memory: でのテストが容易です。

- DuckDB 接続と ETL（日次パイプライン）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# デフォルトの DB パスは settings.duckdb_path を使うか、直接パス文字列を指定
conn = duckdb.connect("data/kabusys.duckdb")

# 日次 ETL の実行（target_date を指定しなければ今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアの算出（score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数または api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

- 市場レジームのスコア算出（score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化

```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# テーブルが初期化された DuckDB 接続が返る
```

- 設定の参照

```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env, settings.is_live)
```

---

## 注意点 / 運用メモ

- OpenAI / J-Quants など外部 API のキーは厳重に管理してください。`.env` はバージョン管理に入れないこと。
- ニュース NLP・レジーム判定は API 呼び出しにコストがかかるため、実行スケジュール・レートに注意してください。
- ETL・保存処理は冪等に設計されていますが、データバックフィルやスキーマ変更時は注意深く運用してください。
- DuckDB の executemany はバージョン依存の挙動があるため、コード内で空リスト送信を回避するガードが入っています。
- 自動で .env を読み込む際、OS 環境変数は保護され `.env.local` の上書き対象外にするロジックが実装されています。自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（概観）

以下は `src/kabusys` 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約して OpenAI でセンチメント計算、ai_scores に書き込む
    - regime_detector.py
      - ETF 1321 MA200 乖離 + マクロニュースセンチメントで市場レジーム判定、market_regime に書き込む
  - data/
    - __init__.py
    - calendar_management.py
      - JPX カレンダー管理、営業日演算、calendar_update_job
    - etl.py
      - ETLResult の公開（pipeline からの再エクスポート）
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等の ETL パイプライン
    - stats.py
      - zscore_normalize 等の共通統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査テーブルの DDL / 初期化（signal_events / order_requests / executions）
    - jquants_client.py
      - J-Quants への HTTP クライアント（トークン取得、fetch/save 各種データ）
    - news_collector.py
      - RSS 取得 / 前処理 / raw_news への保存、SSRF 対策等
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC 計算、統計サマリー、rank 等

---

## 貢献 / 拡張ポイント

- 新しいニュースソース追加（news_collector の DEFAULT_RSS_SOURCES を拡張）
- 追加ファクター実装（research パッケージ内に関数追加）
- 発注・実行フロー（order execution）との連携モジュールを追加
- モニタリング / デプロイ用ユーティリティの追加（systemd / supervisor / containerization）

---

不明点や README に追加したい利用例（例: Docker / systemd ユニット例や CI 設定）があれば教えてください。README をその用途に合わせて追記します。