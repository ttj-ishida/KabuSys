# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）→ 品質チェック → AI によるニュース/レジーム評価 → リサーチ用ファクター計算 → 監査テーブル（発注・約定トレーサビリティ）といった機能を提供します。

主な設計方針は「バックテストでのルックアヘッドバイアス排除」「DuckDB によるローカルデータプラットフォーム」「外部 API 呼び出しはフェイルセーフにし部分失敗を許容すること」です。

対応 Python バージョン: 3.10+

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（クイックスタート例）
- 環境変数（.env）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株自動売買システム向けのライブラリ群です。データ取得（J-Quants）、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ用スキーマなど、売買システムとリサーチで必要となる基盤機能をモジュール化して提供します。

設計上の特徴：
- DuckDB を中核データベースとして利用（ファイル or :memory:）
- J-Quants API からの差分 ETL（ページネーション・レート制限・トークンリフレッシュ対応）
- ニュースの収集・前処理・SSRF 対策
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / マクロ判定（JSON Mode）
- 監査（signal → order_request → execution）の冪等設計
- ルックアヘッドバイアス回避（target_date 指定で日付参照を固定）

---

## 機能一覧

主要コンポーネントと機能：

- config
  - .env 自動ロード（プロジェクトルート検出）と Settings オブジェクト
  - 環境変数必須チェック

- data
  - jquants_client: J-Quants API クライアント（取得 / 保存 / 認証リフレッシュ / レート制御）
  - pipeline / etl: 日次 ETL（run_daily_etl）および個別 ETL ジョブ（prices/financials/calendar）
  - calendar_management: JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
  - news_collector: RSS 収集（SSRF 対策・前処理・記事IDの正規化）
  - quality: データ品質チェック（欠損、重複、スパイク、日付整合性）
  - stats: 汎用統計（Zスコア正規化）
  - audit: 監査ログスキーマの初期化（signal_events, order_requests, executions）

- ai
  - news_nlp.score_news: raw_news をまとめて OpenAI に投げて銘柄別 ai_scores を生成
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime を更新

- research
  - factor_research: calc_momentum, calc_value, calc_volatility（prices_daily / raw_financials ベース）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

1. リポジトリをクローン／配置
   (例)
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール  
   下記は代表的な依存ライブラリです。プロジェクトに合わせて pyproject.toml / requirements.txt を参照してください。
   ```
   pip install duckdb openai defusedxml
   ```
   （その他、標準ライブラリ以外の依存がある場合はプロジェクト側の指示に従ってください）

4. 開発インストール（ローカル開発）
   ```
   pip install -e .
   ```

5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置できます。詳細は「環境変数」セクション参照。
   - 自動ロードはデフォルトで有効。テストなどで無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（クイックスタート）

基本的に DuckDB 接続を作成し、公開関数を呼び出す形で利用します。以下はサンプルコード（Python）です。

- DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # デフォルトパスは settings.duckdb_path
```

- 日次 ETL 実行（市場カレンダー取得・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーを環境変数に設定）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None なら OPENAI_API_KEY を環境変数から参照
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査スキーマ初期化（監査用 DB）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 市場カレンダー判定ユーティリティ
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_trade = is_trading_day(conn, date(2026, 3, 20))
next_day = next_trading_day(conn, date(2026, 3, 20))
```

注意点：
- OpenAI 呼び出しは JSON Mode / response_format を利用しています。API レスポンスのフォーマット制約・例外処理が実装されていますが、API キーの管理・利用はユーザ側で適切に行ってください。
- ETL / news NLP / regime 判定は target_date ベースで動作し、内部での datetime.today() 参照を避ける設計になっています（ルックアヘッドバイアス防止）。

---

## 環境変数（.env）

config.Settings で参照する主な環境変数（必須項目とデフォルト）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行プロセス PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視しきい値（%）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（news/regime 関数で参照）

自動ロードについて:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索し、.env → .env.local の順で読み込みます。
- OS 環境変数は .env 上書きを保護します（.env.local は上書き可能）。
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env の一例）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成

主要ファイル／モジュールの一覧（src/kabusys 以下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py        # ニュースセンチメント（銘柄別 ai_scores 生成）
  - regime_detector.py # マクロ+MA200 合成による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py      # J-Quants API クライアント（fetch/save）
  - pipeline.py           # ETL パイプライン（run_daily_etl 等）
  - etl.py                # ETLResult 再エクスポート
  - calendar_management.py# 市場カレンダー管理 / 営業日判定
  - news_collector.py     # RSS 収集（SSRF/サイズ制限/前処理）
  - quality.py            # データ品質チェック（欠損/重複/スパイク/日付不整合）
  - stats.py              # 統計ユーティリティ（zscore_normalize 等）
  - audit.py              # 監査テーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py    # calc_momentum / calc_value / calc_volatility
  - feature_exploration.py# calc_forward_returns / calc_ic / factor_summary / rank

補足:
- モジュール間でプライベート関数を共有しない設計（テスト時のモックが容易）
- DuckDB SQL を活用した高速なクロスセクション処理

---

追加のドキュメント／注意事項
- OpenAI, J-Quants, kabu API の利用にはそれぞれの契約・認証情報が必要です。
- ニュース収集・外部通信部分は SSRF・大容量レスポンス対策等の安全機構を組み込んでいますが、運用環境のネットワークポリシーやプロキシ設定に応じた追加設定が必要な場合があります。
- DuckDB のバージョンや SQL 構文差異に依存する箇所があります。プロジェクトの推奨環境に合わせてテストしてください。

---

問い合わせ / 貢献
- バグや改善提案は issue を立ててください。プルリクエスト歓迎です。

以上。必要があれば README に具体的な .env.example ファイル内容や CLI 実行スクリプト（もし存在すれば）を追記します。