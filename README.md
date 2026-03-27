# KabuSys

日本株向けのデータプラットフォーム兼自動売買（リサーチ・ETL・AIスコアリング・監査ログ）ライブラリです。  
ETL（J-Quants）→ データ品質チェック → ファクター計算 → ニュース/NLP スコアリング → 市場レジーム判定 → 発注監査ログまでを一貫して提供することを目標としています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能群を提供します：

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL（ページネーション・レート制御・リトライ付き）
- DuckDB をバックエンドにしたデータ保存（冪等保存、ON CONFLICT 処理）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュースの収集（RSS）と前処理、AI（OpenAI）を使った銘柄別ニュースセンチメント算出
- マクロニュースと ETF の移動平均乖離から市場レジーム（bull/neutral/bear）判定
- 研究用ファクター（モメンタム / バリュー / ボラティリティ等）とファクター解析ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマ定義と初期化ユーティリティ
- 環境設定管理（.env の自動読込、必須変数チェック）

設計上のポイント：
- ルックアヘッドバイアス回避（内部処理で datetime.today() を直接参照しない等）
- 冪等性／フォールトトレラント（部分失敗時に他データを保護、API リトライ／フォールバック）
- 外部 SDK 依存は必要最小限（例: OpenAI, duckdb, defusedxml）

---

## 機能一覧

- データ収集 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）
- データ品質チェック
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency（kabusys.data.quality）
- ニュース収集 / 前処理
  - RSS フェッチ、URL 正規化、SSRF 対策、テキスト前処理（kabusys.data.news_collector）
- AI（OpenAI）連携
  - 銘柄別ニューススコアリング（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - ファクター計算（momentum/value/volatility）（kabusys.research）
  - 将来リターン・IC・統計サマリ（feature_exploration）
  - Zスコア正規化（kabusys.data.stats.zscore_normalize）
- 監査ログスキーマ初期化
  - init_audit_schema / init_audit_db（kabusys.data.audit）
- 環境設定
  - Settings（kabusys.config.settings）: .env の自動読込、必須環境変数チェック

---

## 要件（推奨）

- Python >= 3.10（型アノテーションの union 演算子などを使用）
- 必須パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）

具体的な requirements.txt/pyproject.toml はプロジェクトに合わせて作成してください。

---

## セットアップ手順

1. リポジトリをクローン／ダウンロード
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)
3. パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクト配布用に setuptools/pyproject がある場合）pip install -e .
4. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を作成することで自動読み込みされます。
   - 必須の環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN
     - OPENAI_API_KEY (または関数に直接 api_key を渡す)
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション:
     - KABUSYS_ENV = development | paper_trading | live (デフォルト development)
     - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト data/monitoring.db）
   - 自動 .env 読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）
5. DuckDB の初期化（監査DB等）
   - 監査DBを個別に初期化する例は下記 Quickstart を参照

---

## 使い方（クイックスタート）

以下は代表的な操作の例です。

- DuckDB 接続を作成して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ai スコアリング（ニュース）を実行する

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {written}")
```

- 市場レジーム判定を実行する

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化する（専用 DB を使う場合）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って audit テーブルが作成済み
```

- Settings 経由で環境変数にアクセスする

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

注意点：
- OpenAI API キーが必要です（score_news / score_regime）。api_key を関数引数で指定することもできますが、環境変数 OPENAI_API_KEY を設定しておくのが一般的です。
- モジュールの多くはルックアヘッドバイアスを避けるよう設計されています（target_date を明示的に渡す等）。

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に利用）
  - KABU_API_PASSWORD: kabu API パスワード（発注モジュールと連携する場合）
  - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID
- 任意 / 既定値あり
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: INFO（デフォルト）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（デフォルト）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env 読込を無効化

.env ファイルはプロジェクトルート（.git または pyproject.toml の親）を起点に自動読込されます。自動読込は .env → .env.local の順で読み込み、OS 環境変数は優先されます。

---

## ディレクトリ構成

主なファイル／モジュール構成（src/kabusys 配下）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py  — 市場カレンダー管理・営業日判定
    - etl.py                  — ETL インターフェース（ETLResult 再エクスポート）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - stats.py                — z-score 正規化など統計ユーティリティ
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログスキーマ定義 / 初期化
    - jquants_client.py       — J-Quants API クライアント（fetch/save 系）
    - news_collector.py       — RSS ニュース収集／前処理
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ 等

---

## API（代表的な公開関数）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.log_level, settings.is_live, ...
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.quality
  - run_all_checks(conn, ...)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

詳細は各モジュールの docstring を参照してください。

---

## 運用上の注意 / 設計注記

- 多くの箇所で「冪等」「フェイルセーフ」「ルックアヘッドバイアス防止」を重視しています。バックテストや本番環境での利用時は target_date や API キーの扱いに注意してください。
- J-Quants API と OpenAI API の両方でレート／コストの制約があります。大量のバッチ処理は料金・レート制限に配慮して行ってください。
- news_collector は外部 URL を取得するため SSRF や圧縮爆弾等の対策を組み込んでいますが、実際の運用ではフェッチ先の管理と監視が重要です。
- DuckDB の executemany 等の挙動はバージョンによって違いがあるため、パフォーマンスや互換性の確認を行ってください。

---

## 貢献 / ローカル開発ヒント

- テスト時に .env 自動読込を避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants の呼び出し部分は内部で小さなラッパー関数にまとまっており、ユニットテストでは該当関数を patch/mocking して外部呼び出しを遮断できます（例: kabusys.ai.news_nlp._call_openai_api の差し替え等）。
- DuckDB を使った統合テストでは ":memory:" を渡してインメモリ DB を使用できます（監査 DB の初期化関数が対応）。

---

必要であれば、README に含めるサンプル .env.example、依存関係ファイル（requirements.txt / pyproject.toml）のテンプレート、または各モジュールのより詳細な API リファレンスを作成します。どれを追加しましょうか？