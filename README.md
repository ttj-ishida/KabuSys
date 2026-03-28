# KabuSys

日本株向け自動売買基盤（データパイプライン / 研究 / AI スコアリング / 監査ログ）  
このリポジトリは、J-Quants や RSS、OpenAI（gpt-4o-mini）等を利用してデータ収集・品質管理・ファクター計算・ニュースセンチメント判定・市場レジーム判定・監査ログ管理までを提供するモジュール群です。

主な設計方針（抜粋）
- ルックアヘッドバイアス対策：内部で date.today()/datetime.today() を直接参照しない設計が多い
- DuckDB を主要な OLAP ストアとして採用
- API 呼び出しはリトライ/バックオフ/レート制御を実装
- ETL / 品質チェックはフェイルセーフで一部失敗しても他処理を継続

---

## 機能一覧

- 設定管理
  - .env / .env.local を自動ロード（CWD に依存せずプロジェクトルートを探索）
  - settings オブジェクトから各種設定を取得

- データ収集・ETL（kabusys.data）
  - J-Quants から株価（daily_quotes）、財務データ、上場情報、マーケットカレンダーを取得
  - 差分取得・ページネーション・レート制御・トークン自動リフレッシュに対応
  - DuckDB へ冪等保存（ON CONFLICT / UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）

- データ品質チェック
  - 欠損、重複、スパイク、日付不整合等の検出（QualityIssue のリストを返す）

- ニュース取り込み（RSS）と前処理
  - RSS 取得（SSRF 対策、受信サイズ制限、トラッキングパラメータ削除）
  - raw_news / news_symbols との連携

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（JSON mode）で銘柄ごとのセンチメントをスコア化し ai_scores に保存
  - バッチ処理・チャンク・再試行ロジック・レスポンスバリデーション実装

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で bull/neutral/bear を判断し market_regime に保存

- 研究用ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Z-score 正規化ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルを定義・初期化する関数を提供
  - 監査トレーサビリティのためのスキーマ初期化・専用 DB 初期化関数を提供

---

## 必要条件 / 依存パッケージ（代表例）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK v1 系想定)
- defusedxml
- その他標準ライブラリ（urllib 等）

例（pip）:
```
pip install duckdb openai defusedxml
```

プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境作成（任意）
```
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows
```

3. 依存パッケージをインストール
```
pip install -r requirements.txt   # または必要なパッケージを個別にインストール
```

4. 環境変数設定
- プロジェクトルートに `.env`（と任意で `.env.local`）を置くと自動で読み込まれます（config.py の自動ロード）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

主に必要な環境変数（例）
- JQUANTS_REFRESH_TOKEN  : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime などで使用）
- KABU_API_PASSWORD      : kabuステーション API パスワード（実行・発注連携時）
- SLACK_BOT_TOKEN        : Slack 通知用トークン
- SLACK_CHANNEL_ID       : Slack 通知先チャネルID
- KABUSYS_ENV            : development / paper_trading / live（デフォルト development）
- LOG_LEVEL              : DEBUG/INFO/…（デフォルト INFO）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト data/monitoring.db）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本的な例）

以下は Python インタプリタ／スクリプトから呼び出す最小例です。実運用ではロギングやエラーハンドリング、スケジューラ（cron / Airflow 等）を組み合わせて下さい。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に保存（OpenAI API キーは環境変数 OPENAI_API_KEY）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定を実行（1321 の MA200 とマクロセンチメントを合成）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作られる
```

- 設定を参照する
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)
```

- 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026,3,20))
# records は各銘柄ごとの dict のリスト
```

---

## 開発／テストに役立つ設定

- 自動 .env ロードを無効化する（ユニットテスト等）:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

- OpenAI 呼び出し箇所はモジュール内部の _call_openai_api をモックして置き換えることを想定しているため、ユニットテストが書きやすい構造になっています。

---

## 主要モジュール・ディレクトリ構成

（ソースは src/kabusys 以下に配置）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py         : ニュース → 銘柄センチメントスコア（OpenAI）
    - regime_detector.py  : 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py   : J-Quants API クライアント / 保存ロジック
    - pipeline.py         : 日次 ETL 実行 / run_daily_etl / run_prices_etl 等
    - etl.py              : ETLResult 再エクスポート
    - calendar_management.py : マーケットカレンダー管理（営業日判定等）
    - news_collector.py   : RSS 取得・前処理・保存
    - quality.py          : データ品質チェック
    - stats.py            : z-score 等の汎用統計ユーティリティ
    - audit.py            : 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py  : Momentum / Volatility / Value 等のファクター
    - feature_exploration.py : forward returns / IC / rank / summary 等

---

## 注意事項 / 運用上の留意点

- OpenAI／J-Quants の API キーやトークンは機密情報です。リポジトリにハードコーディングしないでください。
- 実口座での自動売買（kabu API 等）を使う場合は、必ず paper_trading 環境で十分な検証を行ってください（settings.is_live / is_paper を利用）。
- DuckDB のスキーマやテーブルは ETL と連携して作成・更新する前提です。既存 DB と併用する際はバックアップを必ず取ってください。
- news_collector は外部 RSS を取得します。SSRF 対策やサイズ制限を組み込んでいますが、運用でアクセス先リストを管理してください。

---

この README はコードベースの概要と開発者向けの最初のハンドブックを目的としています。詳細な API、スキーマ定義、運用手順（cron/airflow、SLACK 通知、kabu 発注フロー等）は別途ドキュメント（Design/Operation.md 等）を参照してください。必要であれば README に追加したい項目（CI、テスト実行方法、具体的な SQL スキーマなど）を教えてください。