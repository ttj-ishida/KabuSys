# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群です。  
市場データの ETL、ニュースセンチメントの AI スコアリング、ファクター計算、監査ログ用スキーマなど、トレーディングシステムの基盤処理を提供します。

主な設計方針
- ルックアヘッドバイアスを排除（内部で date.today() 等を直接参照しない実装）
- DuckDB を主なオンライングレポジトリとして利用
- J-Quants / OpenAI など外部 API に対してリトライ・レート制御を備えた安全な呼び出し処理
- ETL / 品質チェック / 監査テーブルは冪等性とトレーサビリティを重視

バージョン: 0.1.0

---

## 機能一覧

- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存（jquants_client）
  - 日次 ETL パイプライン（run_daily_etl）
  - 市場カレンダーの取得・問い合わせ（calendar_update_job / is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）

- データ品質チェック
  - 欠損データ検出、スパイク検出、重複検出、日付整合性チェック（quality.run_all_checks）

- ニュース収集 / 前処理
  - RSS から安全に記事取得して raw_news テーブルへ保存（news_collector）
  - URL 正規化、SSRF 対策、XML の安全パースなどの実装

- ニュース NLP / AI スコアリング
  - 銘柄別ニュースセンチメントの算出と ai_scores への保存（news_nlp.score_news）
  - マクロニュースと ETF（1321）の MA200 乖離から市場レジームを判定（ai.regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を JSON-mode で利用。失敗時フォールバックを実装

- 研究（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリーなど（research パッケージ）

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル DDL と初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）

- 共通ユーティリティ
  - 環境設定（kabusys.config.Settings、.env 自動読み込み）
  - 統計ユーティリティ（zscore_normalize）

---

## 動作環境（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

requirements.txt はプロジェクトに含まれていない想定のため、下記を個別にインストールしてください。

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-dir>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージ依存をインストール
   - pip install -e .    （プロジェクトが setuptools/pyproject を持つ場合）
   - もしくは個別に: pip install duckdb openai defusedxml

4. 環境変数（.env）を設定
   - プロジェクトルートに `.env`（および開発用に `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag

ポイント:
- 優先順位: OS 環境変数 > .env.local > .env
- .env のパースはエクスポート形式やクォートをある程度サポート
- 必須値が未設定の場合、Settings プロパティは ValueError を送出します（例: JQUANTS_REFRESH_TOKEN）

---

## 使い方（主要 API と使用例）

以下は簡単な Python スニペット例です。実行前に必要な環境変数（特に API キー）を設定してください。

- DuckDB 接続と日次 ETL 実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を使っても良い
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別センチメントスコアリング）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されていれば api_key は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査専用 DuckDB データベース）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリが無ければ自動作成されます
# 以後 conn を使用して監査用テーブルにアクセスできます
```

- カレンダー関連ユーティリティ（営業日判定など）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

注意点:
- OpenAI 呼び出しは gpt-4o-mini（JSON モード）を想定しており、API エラー時はフォールバック（スコア 0.0 等）で継続する設計です。
- J-Quants API 呼び出しは内部でレート制御・トークン自動リフレッシュ・リトライを行います。
- 研究モジュール（research）や統計ユーティリティ（data.stats）は外部 API に依存しません。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールを抜粋した構成です（完全版ではありません）。

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュースセンチメント計算
    - regime_detector.py            - 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント + 保存ロジック
    - pipeline.py                   - ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - etl.py                        - ETLResult 再エクスポート
    - calendar_management.py        - マーケットカレンダー管理
    - news_collector.py             - RSS ニュース収集
    - quality.py                    - データ品質チェック
    - stats.py                      - 統計ユーティリティ（zscore_normalize）
    - audit.py                      - 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            - モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py        - 将来リターン / IC / 統計サマリー
  - execution/                      - （発注 / 実行関連：このコードベースでは主要実装は含まれていない想定）
  - monitoring/                     - （監視・プロセスマネジメント用モジュール等）
  - data/（上と重複するが、data パッケージ内ファイル群）

それぞれのモジュールは docstring に詳しい設計目的・入出力仕様が記載されています。実装を読むことで細かい挙動（例外ハンドリング、リトライ方針、SQL スキーマ前提など）を把握できます。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須: AI 機能を使う場合) — OpenAI API キー
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視等で使う SQLite のパス（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_ENV — 環境（development / paper_trading / live）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — =1 にすると .env 自動ロードを無効化

詳しくは kabusys/config.py の Settings クラスを参照してください（プロパティに利用可能キーとデフォルト値が示されています）。

---

## 開発・拡張メモ

- テスト可能性を意識して API 呼び出し（OpenAI / J-Quants）や時間依存処理には差し替え用フックやモック可能な内部関数が用意されています（例: _call_openai_api を unittest.mock.patch）。
- DuckDB を使った SQL はパラメータバインド（?）で安全に記述されています。データ保存時は ON CONFLICT DO UPDATE で冪等性を担保しています。
- NewsCollector は SSRF 対策・受信サイズ制限・XML パースの防御を実装しています。RSS 追加ソースは DEFAULT_RSS_SOURCES を拡張してください。
- 監査テーブルは削除を前提としない設計です。init_audit_schema で UTC タイムゾーンを固定します。

---

## ライセンス／貢献

（リポジトリの LICENSE ファイルに従ってください）

貢献方法:
- Issue を立てる、プルリクエストを送る、ドキュメントを改善する等

---

README の内容はコード中の docstring をベースに作成しました。より詳細な使い方や運用手順（プロセス監視、cron / Airflow などでのジョブ運用、kabuステーションとの接続や発注フロー）は運用ポリシーに合わせ追加してください。