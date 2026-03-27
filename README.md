# KabuSys

日本株のデータパイプライン・リサーチ・自動売買を想定したユーティリティ群とアルゴリズム群のライブラリです。  
DuckDB をストレージに用いた ETL、J-Quants クライアント、ニュース収集・NLP（OpenAI）によるセンチメント評価、リサーチ用のファクター計算、監査ログ/トレーサビリティ（発注/約定ログ）の初期化・管理などを提供します。

## 特徴（機能一覧）
- 環境設定管理
  - .env / .env.local から自動で環境変数を読み込む仕組み（必要に応じて無効化可能）
- データ取得・ETL
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー、上場銘柄情報）
  - 差分更新・ページネーション対応・レート制限と再試行
  - ETL パイプライン（run_daily_etl）と個別 ETL 関数（prices / financials / calendar）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS 収集（SSRF 対策・トラッキング除去・前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄単位のニュースセンチメント付与（score_news）
  - マクロニュースと ETF 200 日 MA を組み合わせた市場レジーム判定（score_regime）
- リサーチ
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Spearman）算出、統計サマリー、Z スコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査スキーマ作成（冪等、UTC タイムスタンプ）
  - 監査専用 DuckDB 初期化ユーティリティ（init_audit_db / init_audit_schema）

---

## セットアップ手順

前提
- Python 3.9+（typing の union 表記等を利用）
- システムに DuckDB が導入される（pip パッケージで依存解決可）

推奨依存パッケージ（少なくとも以下が必要です）
- duckdb
- openai
- defusedxml

インストール例（プロジェクトルートで）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# パッケージとして使う場合（開発インストール）
pip install -e .
```

環境変数
- 必須（ライブラリの一部機能で必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
  - SLACK_BOT_TOKEN — Slack 通知を使う場合
  - SLACK_CHANNEL_ID — Slack チャネル
- 任意 / デフォルトあり
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
  - LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")（デフォルト: INFO）
  - OPENAI_API_KEY — OpenAI を使う機能で必要

.env の自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env → .env.local を自動読み込みします。
- 自動読み込みを無効にする場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

サンプル .env（README 用例）
- .env.example（作成して .env にコピーして編集）
  - JQUANTS_REFRESH_TOKEN=...
  - OPENAI_API_KEY=...
  - KABU_API_PASSWORD=...
  - SLACK_BOT_TOKEN=...
  - SLACK_CHANNEL_ID=...
  - DUCKDB_PATH=data/kabusys.duckdb
  - KABUSYS_ENV=development
  - LOG_LEVEL=INFO

---

## 使い方（代表的な API と実行例）

基本的な呼び出しは Python スクリプトや CLI バッチから行います。ここでは主なユーティリティの使用例を示します。

- 設定参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

- DuckDB 接続と ETL の実行（日次 ETL）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_dateを指定しない場合は今日が対象
print(result.to_dict())
```

- ニュースセンチメント付与（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境で供給
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境で供給
```

- 監査ログ DB の初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
```

- リサーチ用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore_normalize 等を組み合わせて利用
```

ログ設定
- settings.log_level を参照してログレベルを決める設計になっています。アプリ側で logging.basicConfig(level=...) 等で有効化してください。

エラーハンドリング
- 多くの外部 API 呼び出しは内部でリトライやフェイルセーフ（API 失敗時はスキップしてゼロや中立値）を行います。ETL やスコアリング関数は失敗時に例外を投げる場合がありますので呼び出し元で適切に try/except を行ってください。

---

## ディレクトリ構成（主要ファイル）
プロジェクトのルートが src/kabusys としてインストールされる想定です。主要ファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント（OpenAI）
    - regime_detector.py — マクロ+MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult 再エクスポート
    - calendar_management.py— 市場カレンダー管理・営業日関数
    - news_collector.py     — RSS ニュース収集（SSRF 対策）
    - quality.py            — データ品質チェック
    - stats.py              — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログ（スキーマ作成・init）
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Volatility/Value 計算
    - feature_exploration.py— 将来リターン / IC / サマリー 等
  - ai/__init__.py
  - research/__init__.py

---

## 注意点 / 補足
- Look-ahead バイアス対策:
  - 多くの処理（ETL, ニュース窓, レジーム判定等）は date 引数を明示的に受け取り、内部で date.today() を不用意に参照しない設計になっています。バックテスト等で過去日を与えることを想定しています。
- 環境変数の優先度:
  - OS 環境変数 > .env.local > .env の順で上書きされます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 利用:
  - score_news / score_regime は OpenAI API（gpt-4o-mini）を使います。環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key 引数で渡してください。
  - API 呼び出しは JSON mode を前提とした厳密なパース・バリデーションを行います。API エラー時はフェイルセーフ動作でスコアを 0.0 にフォールバックする実装が多く含まれます。
- J-Quants 認証:
  - get_id_token は settings.jquants_refresh_token を参照します。refresh token を .env に設定しておくことで自動的にトークンを取得・キャッシュします。

---

もし README に追加したいサンプル CLI、CI 設定、あるいは実際のテーブルスキーマ（raw_prices / raw_financials など）の DDL を含めたい場合は、その内容を教えてください。README をプロジェクトの配布用途に合わせて拡張します。