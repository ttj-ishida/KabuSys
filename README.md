# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
このリポジトリはデータ収集（J-Quants）、ニュース収集/NLP（OpenAI）、市場レジーム判定、ファクター計算、ETL パイプライン、監査ログ（約定トレーサビリティ）などを含む内部ライブラリを提供します。

---

## 概要

KabuSys は主に次の用途を想定したモジュール群です。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への永続化（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）の初期化・管理

設計上の特徴：
- ルックアヘッドバイアス回避（内部で date.today() 等の参照を最小化）
- DuckDB を中心としたクエリベース処理（外部依存を抑制）
- API 呼び出しに対するリトライ・レート制御・フェイルセーフの実装
- 冪等処理（ON CONFLICT / INSERT/DELETE の扱い）を重視

---

## 機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系関数）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days）
  - ニュース収集（fetch_rss, トラッキング除去、SSRF 対策）
  - 品質チェック（missing_data / spike / duplicates / date_consistency / run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - 銘柄別ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター算出（calc_momentum / calc_value / calc_volatility）
  - 特徴量解析（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込み・管理（Settings クラス、.env 自動読み込み機能）
  - 必須設定の取得（例: settings.jquants_refresh_token）

---

## セットアップ手順

前提
- Python 3.10 以上（タイプヒントに | 演算子等を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

推奨手順（例）:

1. リポジトリをクローンし、仮想環境を作成

   ```bash
   git clone <このリポジトリのURL>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要なパッケージをインストール

   主要依存（例）:
   - duckdb
   - openai
   - defusedxml

   requirements.txt がない場合は手動でインストールしてください：

   ```bash
   pip install duckdb openai defusedxml
   ```

   （このコードベースで使用している他の標準ライブラリ依存は標準に含まれます）

3. パッケージを編集可能モードでインストール（任意）

   ```bash
   pip install -e src
   ```

4. 環境変数を設定する（.env をプロジェクトルートに配置することで自動読み込みされます）

   自動ロードについて:
   - config.py はプロジェクトルート（.git または pyproject.toml を探索）に `.env` / `.env.local` があれば自動で読み込みます。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

   例: `.env`（※実際の値は適切に設定）

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須環境変数（Settingsで _require が呼ばれるもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意（デフォルト値あり）:
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## 使い方（代表的な呼び出し例）

以下は Python REPL やスクリプトからライブラリを利用する例です。DuckDB の接続に settings.duckdb_path を使う前提です。

- ETL（日次パイプライン）を実行する

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 銘柄ニュースの AI スコアを算出して ai_scores テーブルへ書き込む

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))  # 日付は例
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム（日次）を判定して market_regime テーブルへ保存する

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化する（監査スキーマを作成）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # または別パスを指定
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

- OpenAI API キーの取り扱い
  - score_news / score_regime は引数 api_key を受け取れます（渡さない場合は環境変数 OPENAI_API_KEY を参照）。
  - API 呼び出しは内部でリトライ・バックオフ処理を実装しています。失敗時はフェイルセーフとして（多くの箇所で）スコア0やスキップを行い、完全停止しない設計です。

---

## 注意点 / 運用メモ

- ルックアヘッドバイアス対策:
  - 多くの関数は内部で date.today() を参照せず、明示的に target_date を受け取る設計です。バックテスト用途では必ず適切な target_date を渡してください。
- .env の自動読み込み:
  - プロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）を探索して `.env` / `.env.local` を読み込みます。
  - テストなどで自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- リトライや API レート制御:
  - J-Quants クライアントは固定間隔スロットリング（120 req/min）とリトライを実装しています。
  - OpenAI 呼び出しもリトライ・バックオフの考慮がありますが、API の仕様変更には注意してください。
- DuckDB の executemany の仕様:
  - 一部の処理は DuckDB のバージョンに依存する動作（executemany の空リスト不可等）を考慮しています。DuckDB のバージョン互換性に注意してください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py
    - パッケージ初期化・バージョン定義
  - config.py
    - Settings クラス、.env 自動読み込み、必須環境変数取得ユーティリティ
  - ai/
    - __init__.py
      - score_news を公開
    - news_nlp.py
      - 銘柄別ニュースセンチメント算出（OpenAI 呼び出し、レスポンス検証、ai_scores 書込）
    - regime_detector.py
      - ETF 1321 の MA とマクロニュースセンチメントを合成して market_regime を書き込む
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch / save / 認証 / rate limit / retry）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）と ETLResult 定義
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS フィード収集、URL 正規化、SSRF 対策、raw_news への保存ロジック
    - calendar_management.py
      - market_calendar 管理、営業日判定、calendar_update_job
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）DDL と初期化ユーティリティ
  - research/
    - __init__.py
      - 研究用関数の公開
    - factor_research.py
      - momentum / value / volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC 計算、統計サマリー
  - monitoring / strategy / execution / その他（__all__ で公開される可能性のあるモジュール群）
    - （このスナップショットでは主に data / ai / research が実装されています）

---

## 最後に

この README はコードの概要・導入・代表的利用方法をまとめたものです。実運用前には次を確認してください。

- 環境変数（特に API トークン類）が正しく安全に管理されていること
- DuckDB / OpenAI / J-Quants の API 利用制限・課金設定
- 必要に応じてログ設定を追加しログローテーション等を構成すること

必要であれば README に含める実行スクリプト例（systemd / cron / Airflow / Prefect など）やテーブルスキーマの詳細、.env.example を作成できます。ご希望があれば追記します。