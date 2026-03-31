# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、リサーチ用ファクター計算、ニュースNLP（OpenAI）、市場レジーム判定、監査ログ（発注→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の定量投資・自動売買に必要なデータ基盤とアルゴリズム部品を集めた Python モジュール群です。主な目的は次のとおりです。

- J-Quants API を使った株価・財務・カレンダーの差分取得（ETL）
- RSS ベースのニュース収集・前処理と銘柄紐付け
- OpenAI を利用したニュースセンチメント（銘柄別 / マクロ）評価
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と研究ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を DuckDB にセットアップ
- 市場カレンダー管理（営業日判定、next/prev trading day など）

設計上の特徴:
- ルックアヘッドバイアス防止（内部で date.today() や datetime.today() を直接参照しない設計の関数が多数）
- 冪等性（DB 保存は ON CONFLICT / UPSERT を利用）
- API 呼び出しにはリトライやレート制御を組み込み
- 外部依存を最小化しつつ、OpenAI / duckdb / defusedxml など必要箇所のみ利用

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl を含む）
  - J-Quants クライアント（fetch / save / 認証）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days）
  - ニュース収集（RSS → raw_news、SSRF 対策やトラッキングパラメータ除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（監査テーブル・インデックスの作成）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で算出し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースセンチメントを合成して市場レジーム判定
- research/
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

（strategy, execution, monitoring 等の高レベルモジュールは __init__ にて公開候補が示されています）

---

## 前提条件（環境）

- Python 3.9+
- 必須ライブラリ（代表例）:
  - duckdb
  - openai
  - defusedxml

実際に使う機能に応じて追加パッケージが必要になる場合があります。requirements.txt をプロジェクトに用意している場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローンし作業ディレクトリへ移動:

   git clone <repo-url>
   cd <repo>

2. 仮想環境の作成（推奨）:

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール（例）:

   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt や pyproject.toml があればそれを利用してください）
   pip install -e . などの開発インストールも可能です。

4. 環境変数の設定:
   - 推奨: プロジェクトルートに `.env` を作成すると自動で読み込まれます（.env.local は .env をオーバーライド）。
   - 自動ロードはデフォルトで有効。無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   必要な環境変数（機能に応じて）:
   - JQUANTS_REFRESH_TOKEN （必須: J-Quants 認証）
   - KABU_API_PASSWORD （kabuステーション API を使う場合）
   - KABU_API_BASE_URL （任意、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID （Slack 通知を使う場合）
   - OPENAI_API_KEY （AI 機能を使う場合）
   - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH （監視用 SQLite デフォルト: data/monitoring.db）
   - KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL （DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

   簡単な .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（簡単な例）

以下は代表的な使い方のサンプルコードです。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN や OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続 & ETL 実行:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は pathlib.Path
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 監査ログ用 DB 初期化:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成されます
```

- ニュースセンチメント評価（ai.news_nlp）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（ai.regime_detector）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # 例: api_key を直接渡す
```

- リサーチ関数（factor 計算）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors は各銘柄の dict のリスト
```

テスト時のヒント:
- ai モジュールの OpenAI 呼び出しは内部関数 _call_openai_api を patch して差し替えられるよう設計されています（unittest.mock.patch を利用）。

---

## 重要な挙動・注意点

- .env 自動読み込み:
  - パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動で読み込みます。
  - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- ルックアヘッドバイアス対策:
  - 多くの分析・AI 関数は内部で date.today() を直接参照しないように実装されています。バックテスト等では target_date を明示的に渡してください。

- DB 保存の冪等性:
  - save_* 系の関数（J-Quants クライアント）は ON CONFLICT DO UPDATE を利用して冪等に保存します。

- OpenAI 呼び出し:
  - news_nlp / regime_detector は gpt-4o-mini を想定した JSON mode を使用します。API 失敗時はフォールバック（スコア 0.0 等）が組み込まれています。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要なファイルとモジュール構成です（抜粋）。

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
    - etl.py
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
  - research/ ... (その他リサーチ用モジュール)
  - (strategy/, execution/, monitoring/ などは __all__ に含まれるが本リストに無い場合は別途実装されます)

---

## 開発・貢献

- コード品質: ロギング、例外ハンドリング、リトライ、テストの容易性を重視して実装しています。
- テスト: 外部 API 呼び出しはモック可能な設計です。OpenAI / J-Quants 呼び出しのスタブ化を推奨します。
- 貢献: Issue / PR を歓迎します。機能追加・バグ修正・ドキュメント改善などお気軽に対応ください。

---

この README はコードベース（src/kabusys）からの主要機能・使い方の抜粋となります。より詳細な設計方針やデータスキーマ、外部連携仕様（J-Quants API フィールドマッピング等）は該当モジュールの docstring を参照してください。