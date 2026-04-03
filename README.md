# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（発注→約定トレース）、市場レジーム判定などを含むモジュール群を提供します。

---

## 概要

KabuSys は日本株の自動売買システム／データ基盤を構築するための内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と LLM を用いた銘柄別センチメント（ai_scores）算出
- 市場レジーム（bull / neutral / bear）を ETF+マクロニュースで判定
- ファクター計算・特徴量探索（研究用）
- 発注・約定の監査ログ（監査テーブルの初期化・管理）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

パッケージはモジュール単位で利用でき、バックテストや本番運用、研究用途いずれにも対応するよう設計されています。

---

## 主な機能一覧

- データ取得・保存
  - J-Quants クライアント（fetch / save: daily quotes、financials、market calendar、listed info）
  - ETL パイプライン（差分取得・バックフィル・品質チェックを含む run_daily_etl）

- ニュース関連（NLP）
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメント算出（score_news）
  - マクロニュース＋ETF MA200 乖離による市場レジーム判定（score_regime）

- 研究（Research）
  - Momentum / Value / Volatility 等のファクター計算（calc_momentum 等）
  - 将来リターン計算、IC（Information Coefficient）、rank / zscore 正規化など

- 監査（Audit）
  - signal_events / order_requests / executions を含む監査スキーマの初期化（init_audit_db / init_audit_schema）

- データ品質チェック
  - 欠損（OHLC）、スパイク、重複、日付不整合の検出（run_all_checks）

- 設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）、環境変数経由で設定を参照（kabusys.config.settings）

---

## セットアップ

前提
- Python 3.10 以上（型ヒントに `|` を使用しているため）
- 必要な外部サービス: J-Quants API、OpenAI（LLM 呼び出しに使用）

インストール（最小例）:

```bash
# 仮想環境推奨
python -m venv .venv
source .venv/bin/activate

# 必要なパッケージを個別にインストール
pip install duckdb openai defusedxml
# またはプロジェクトで配布する requirements.txt があればそれを使う
# pip install -r requirements.txt

# パッケージを編集可能モードでインストール（プロジェクト直下で）
pip install -e .
```

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知に使用する場合
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（監視関連）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）

自動 .env 読み込み
- プロジェクトルート（.git または pyproject.toml の親ディレクトリ）から `.env` と `.env.local` を自動読み込みします。
- 自動ロードを無効化するには環境変数を設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: .env の最小例

```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（基本例）

以下はライブラリ機能を直接呼び出す最小例です。DuckDB の接続は `duckdb.connect(path)` を使います。

- ETL（デイリー実行）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントスコア算出

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数で設定するか、第三引数に文字列で渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
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

- 監査 DB 初期化（監査専用 DB を作る）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
# 以降 conn を使って監査テーブルにアクセス
```

- 研究用ファクター計算の例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点
- LLM 呼び出し（score_news, score_regime）は実際に OpenAI API を呼ぶため API キーが必要です。テスト時は各モジュール内の _call_openai_api をモックできるよう設計されています。
- 関数群はルックアヘッドバイアス防止のため、内部で date.today() を安易に参照しないよう配慮されています。target_date を明示的に渡して使ってください。
- DuckDB の一部操作（executemany 等）でバージョン差の影響を受ける箇所があるため、DuckDB のバージョンに依存する運用注意があります。

---

## ディレクトリ構成（主なファイル）

パッケージは `src/kabusys/` 以下に配置されています。主要なモジュールと役割を示します。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py        — ニュースの LLM によるセンチメントスコア算出
    - regime_detector.py — ETF MA200 とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch/save）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETLResult 再エクスポート
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - news_collector.py  — RSS 収集・前処理
    - quality.py         — データ品質チェック（欠損・スパイク等）
    - stats.py           — 共通統計関数（zscore_normalize）
    - audit.py           — 監査ログ（監査スキーマ初期化・init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー など

各モジュールには docstring と設計方針・注意事項が含まれており、関数の引数・戻り値・副作用が明記されています。

---

## 補足・運用上の注意

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト時に自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しはリトライとフォールバックを実装していますが、API 失敗時は安全にフォールバック（macro_sentiment=0 など）する設計です。重要な運用時は呼び出し回数・コスト管理に注意してください。
- J-Quants API リクエストはレート制御（120 req/min）とリトライ実装があります。認証トークンの自動リフレッシュも行われます。
- DuckDB に対する変更（スキーマ初期化や DDL）は冪等性を意識して設計されていますが、運用時はバックアップを取ることを推奨します。

---

この README はコードベースの主要機能・利用方法・セットアップ方法のサマリです。詳細な API ドキュメントや運用手順（デプロイ、監視、バックテストとの連携等）は別途ドキュメント化してください。必要であれば README に追記する具体例（CI/CD、cron スケジュール、systemd サービス、LINE 通知設定など）も作成します。