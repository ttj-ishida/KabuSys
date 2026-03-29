# KabuSys

日本株向け自動売買・データプラットフォーム（ライブラリ）

KabuSys は日本株のデータ収集・品質チェック・ETL、AI ベースのニュース解析・市場レジーム判定、研究・ファクター計算、監査ログ（トレーサビリティ）などを含む統合ライブラリです。DuckDB を用いたローカルデータベースと J‑Quants / OpenAI を組み合わせ、バックテスト／運用パイプラインの基盤処理を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数（必須 / 任意）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の領域をカバーします。

- データプラットフォーム（J‑Quants からの日次株価・財務・カレンダー取得、ETL パイプライン、品質チェック）
- ニュース収集（RSS）とニュースの NLP（OpenAI）による銘柄センチメント評価
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを融合）
- リサーチ用ユーティリティ（ファクター計算、将来リターン計算、IC / 統計サマリー）
- 監査ログ（signal → order_request → execution のトレーサビリティ用スキーマ）
- 設定管理（.env の自動ロード、環境による動作切替）

設計上の留意点（抜粋）:
- ルックアヘッドバイアス回避: 内部ロジックは `date` / `target_date` を明示的に受け取り、`datetime.today()` 等を直接参照しないように設計されています。
- 冪等性: DB への保存（ETL 保存/監査テーブル初期化 等）は基本的に冪等で行います。
- フェイルセーフ: 外部 API（OpenAI, J‑Quants）失敗時は例外で即終了させず、安全なフォールバックやログ出力で継続する設計箇所があります。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J‑Quants API クライアント（取得・保存用、トークンリフレッシュ・レート制御・リトライ対応）
  - market calendar 管理 / 営業日ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS）と前処理（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 統計ユーティリティ（Z スコア正規化）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
- ai
  - ニュース NLP（score_news）：銘柄毎にニュースを集約して LLM でスコア化し ai_scores に保存
  - 市場レジーム判定（score_regime）：ETF 1321 の MA200 乖離とマクロニュース（LLM）を合成して market_regime に保存
- research
  - ファクター計算（Momentum / Value / Volatility 等）
  - 特徴量探索（将来リターン計算 / IC / 統計サマリー / ランク関数）
- config
  - .env 自動読み込み / 環境設定ラッパー（Settings）

---

## セットアップ手順

前提:
- Python 3.10 以上（ソース中に union 型や型注釈を使用）
- ネットワークアクセス (J‑Quants / OpenAI 等) が必要な機能を使う場合は適切な API キーが必要

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要な主要ライブラリ（例）
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成すると、自動的に読み込まれます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須の環境変数や例については次節「環境変数」を参照してください。

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API を使う場合のパスワード（設定経由で参照）
- SLACK_BOT_TOKEN: Slack 通知を行う場合に必要
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

OpenAI 関連:
- OPENAI_API_KEY: score_news / score_regime 等で使用（引数でキーを渡すことも可能）

任意・デフォルト値あり:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）

注意:
- .env 自動ロードはプロジェクトルート（.git もしくは pyproject.toml が存在するディレクトリ）を基に行われます。
- テスト等で自動ロードを抑止する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡易サンプル）

以下は主要なユースケースの最小例です。実際は例外処理・ログ設定・API キー管理を適切に行ってください。

1) ETL（日次パイプライン）を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのスコアリング（OpenAI を使う）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルへ書き込み可能
```

5) リサーチ用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

補足:
- OpenAI の呼び出し箇所は内部で retry/backoff を持ちますが、API キーは適切に管理してください。
- DuckDB 接続は共有して使用できます。ETL 系はトランザクション制御（BEGIN/COMMIT/ROLLBACK）を利用します。

---

## ディレクトリ構成

主要なファイル・モジュール構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                        - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     - ニュースの LLM スコアリング（score_news）
    - regime_detector.py              - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                      - ETL パイプライン（run_daily_etl 等）
    - etl.py                           - ETL の公開インターフェース（ETLResult）
    - jquants_client.py                - J‑Quants API クライアント（取得/保存）
    - news_collector.py                - RSS 収集と前処理
    - calendar_management.py           - マーケットカレンダー管理（営業日判定等）
    - quality.py                       - データ品質チェック
    - stats.py                         - 統計ユーティリティ（zscore_normalize）
    - audit.py                         - 監査ログ（スキーマ初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py               - Momentum / Value / Volatility 等
    - feature_exploration.py           - 将来リターン / IC / 統計サマリー 等

リポジトリルート（想定）
- pyproject.toml / setup.cfg / requirements.txt （存在する場合）
- .env.example（プロジェクトに合わせて作成しておくことを推奨）
- src/kabusys/...

---

## 運用上の注意点

- セキュリティ:
  - RSS 取得は SSRF 対策・プライベートアドレスブロック・レスポンスサイズ上限を組み込んでいますが、運用環境ではさらにネットワーク制御を行ってください。
  - API キーは適切に管理（シークレット管理・権限分離）してください。
- データ一貫性:
  - ETL は差分更新・バックフィルを行います。バックフィル日数や lookahead の設定は環境に応じて調整してください。
- テスト:
  - 自動 .env ロードはテスト時に不要な環境依存を招くため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用して無効化できます。
  - OpenAI / ネットワーク呼び出しはモック可能な設計（内部の _call_openai_api 等を patch）です。

---

この README は主要な使い方と設計上のポイントを簡潔にまとめたものです。各モジュールの docstring により詳細な振る舞いと設計意図が記載されていますので、実装や拡張を行う場合は該当ファイルの docstring を参照してください。