# KabuSys

KabuSys は日本株の自動売買・データ基盤・リサーチを支えるライブラリ群です。  
ETL（J-Quants からの株価/財務/カレンダー取得）、ニュース収集と LLM によるセンチメント評価、ファクター計算、監査ログ（注文→約定のトレーサビリティ）、市場レジーム判定などを提供します。

バージョン: 0.1.0

---

## 主要な特徴

- データ取得・ETL
  - J-Quants API からの株価日足（OHLCV）、財務データ、JPX マーケットカレンダー取得（ページネーション・リトライ・レート制御対応）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）をサポート
  - 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース処理 & LLM 評価
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別 ai_score）およびマクロセンチメント（市場レジーム判定）
  - バッチ処理・リトライ・レスポンス検証・スコアクリップ等の堅牢な実装
- リサーチ機能
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー、Z スコア正規化ユーティリティ
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue オブジェクトで収集）
- 監査（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブル定義・初期化（DuckDB）
  - 発注の冪等キー（order_request_id）や各種インデックスを提供
- 環境設定管理
  - .env / .env.local / OS 環境変数から自動読み込み（必要に応じて無効化可）
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN 等）

設計上の留意点:
- ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を直接参照しない関数実装）
- フェイルセーフ（API エラー時はスキップして継続する等）
- DuckDB を中心としたローカル軽量 DB 設計

---

## 必要環境 / 依存ライブラリ（主要）

- Python 3.10+
- duckdb
- openai
- defusedxml

（プロジェクトに合わせて追加の依存がある場合があります。setup ファイルや requirements を参照してください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# その他プロジェクト固有の依存があれば追加
```

---

## 環境変数

自動でプロジェクトルートの `.env` → `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（使用機能があれば）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news/scoring に必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

例（.env）:
```env
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカルでの開始手順例）

1. リポジトリをクローンして仮想環境を用意する
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   # プロジェクトの setup.py / pyproject.toml があれば `pip install -e .` も検討
   ```

2. 環境変数を設定（.env ファイルをプロジェクトルートに作成）
   - 上記の必須値を `.env` へ記入

3. DuckDB（監査用 DB 等）の初期化（オプション）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

4. 日次 ETL の実行（例）
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

注意: J-Quants の API 呼び出しには JQUANTS_REFRESH_TOKEN、OpenAI 呼び出しには OPENAI_API_KEY が必須です。

---

## 使い方（代表的な API）

- ETL（日次パイプライン）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  ```

- ニューススコアリング（指定日）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（オプション）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

---

## 設計上の注意 / トラブルシューティング

- Look-ahead バイアス対策:
  - 多くの関数は target_date を明示的に受け取り、内部で現在時刻を参照しない設計です。バックテストや再現性のために target_date を明示してください。
- 環境変数の自動読み込み:
  - .env/.env.local の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテストで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants API のエラー:
  - LLM 呼び出しはリトライやフォールバック値（例: macro_sentiment=0.0）を持ちますが、APIキー未設定時は ValueError を送出します。
- DuckDB executemany に関する互換性:
  - 一部の場所で空の executemany 呼び出しを回避するために事前チェックを行っています（DuckDB のバージョン差異に対応）。
- RSS ニュース収集:
  - SSRF 対策、受信サイズ制限、gzip 解凍の検査など防御処理を実装しています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュール構成（抜粋）:

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
    - etl.py (re-export)
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (存在が示唆されるが実装は省略される可能性あり)
  - strategy/, execution/ (パッケージ公開名に含まれるがここに示されたコードは data/research/ai が中心)

ファイル群は次の責務で整理されています:
- data/* : データ取得・ETL・品質・カレンダー・監査
- ai/* : ニュース NLP と市場レジーム判定（OpenAI 連携）
- research/* : ファクター設計・探索・統計ユーティリティ
- config.py : 環境設定と .env 自動読み込み

---

## 開発者向けメモ

- テスト時には .env 自動読み込みを抑止するか、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI の呼び出し点（news_nlp._call_openai_api / regime_detector._call_openai_api）はテストで patch してスタブ化しやすいように設計されています。
- DuckDB 接続は外部から注入する設計で、関数は副作用を持つ DB 操作を明示しています（BEGIN/COMMIT/ROLLBACK を内部で管理する箇所あり）。

---

この README はコードベースの主要ポイントを抜粋した概要です。より詳細な実装や API の仕様（テーブルスキーマ、ETL の細部、Research の運用フロー等）は各モジュールの docstring とソースコードを参照してください。質問や追加のドキュメント化が必要であればお知らせください。