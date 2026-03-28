# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータプラットフォームおよび自動売買支援ライブラリです。J-Quants API と連携した ETL、ニュース収集・NLP、AI を用いたセンチメント判定、ファクター計算、品質チェック、および発注監査ログの基盤機能を提供します。

---

## 主な機能

- データ収集・ETL
  - J-Quants から株価（OHLCV）/財務データ/上場銘柄情報/市場カレンダーを差分で取得・保存
  - DuckDB への冪等的保存（ON CONFLICT / UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）

- データ品質管理
  - 欠損検出、重複検出、スパイク（急変動）検出、日付整合性チェック（run_all_checks）

- カレンダー管理
  - JPX カレンダーの取得・管理、営業日判定（is_trading_day 等）
  - 翌営業日/前営業日の取得、期間内営業日一覧取得

- ニュース収集（RSS）
  - RSS フィードの取得・正規化、SSRF 対策、トラッキングパラメータ除去、raw_news への冪等保存

- ニュース NLP / AI
  - ニュースをまとめて LLM（gpt-4o-mini）で銘柄別センチメントをスコア化し ai_scores に保存（score_news）
  - マクロニュース + ETF（1321）200日移動平均乖離を組み合わせて市場レジーム（bull/neutral/bear）判定（score_regime）

- 研究用ユーティリティ
  - ファクター計算（モメンタム/ボラティリティ/バリュー）
  - 将来リターン計算、IC（Information Coefficient）等の統計処理、Zスコア正規化

- 監査ログ（オーダー／約定トレーサビリティ）
  - signal_events / order_requests / executions テーブルによる監査スキーマの初期化・管理（init_audit_schema / init_audit_db）

- その他
  - 環境変数読み込み (.env / .env.local 自動ロード、プロジェクトルート検出)
  - レートリミッタ、リトライロジック、Fail-safe 設計（API エラー時は安全にフォールバック）

---

## セットアップ

前提
- Python 3.10+ を推奨（型注釈で `X | None` を使用）
- J-Quants API アクセス、OpenAI API、（任意で）Slack トークン等の外部クレデンシャル

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境を作成して有効化（任意）
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 依存パッケージをインストール
（実プロジェクトの requirements.txt / pyproject.toml を利用してください。ここは主要依存の例です。）
```bash
pip install duckdb openai defusedxml
```

4. パッケージをインストール（開発用）
```bash
pip install -e .
```

5. 環境変数の設定
プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。`.env.example` を参考に必要な変数を設定してください。主要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に必要）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須にするかは利用機能による）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB などの SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development | paper_trading | live）デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

auto .env ロードの仕様:
- プロジェクトルートは this file の親ディレクトリから上方向に `.git` または `pyproject.toml` を探し特定します。
- 読み込み順序: OS 環境 > .env.local > .env
- テスト時など自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（基本例）

以下は主要な操作の最小例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作成して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを取得して ai_scores に保存
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # returns number of codes written
print("wrote", written)
```

- 市場レジームスコア（1321 MA200 + マクロニュース）を算出
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は duckdb connection
```

- 研究用：ファクター計算・IC 計算など
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
forw = calc_forward_returns(conn, date(2026,3,20), horizons=[1,5,21])
ic = calc_ic(momentum, forw, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

注意点
- AI（OpenAI）を使う機能は OPENAI_API_KEY を必要とします。API 呼び出しにはリトライやフォールバックが組み込まれていますが、トークン割当・コスト管理は各自で行ってください。
- ETL / データ保存や品質チェックは DuckDB のスキーマを前提としています。初期スキーマの準備はプロジェクト側のスクリプトで行ってください（スキーマ定義は data パッケージ内を参照）。

---

## ディレクトリ構成

主要ファイル/モジュールの概観（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py               -- 環境変数・設定管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py           -- ニュース NLP（score_news）
    - regime_detector.py    -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py-- カレンダー管理（営業日判定など）
    - etl.py                 -- ETL インターフェース再エクスポート
    - pipeline.py            -- ETL パイプライン実装（run_daily_etl 等）
    - stats.py               -- 統計ユーティリティ（zscore_normalize 等）
    - quality.py             -- データ品質チェック
    - audit.py               -- 監査ログスキーマと init 関数
    - jquants_client.py      -- J-Quants API クライアント（取得・保存）
    - news_collector.py      -- RSS ニュース収集（SSRF 対策等）
  - research/
    - __init__.py
    - factor_research.py     -- ファクター計算（Momentum/Value/Volatility）
    - feature_exploration.py -- 将来リターン・IC・統計サマリー等
  - (その他)                 -- strategy / execution / monitoring 等のサブパッケージが存在する想定

各モジュールは単一責務を保ち、外部 API 呼び出しや DB 書き込み時に冪等・リトライ・ログを考慮した実装になっています。詳細は該当ファイル内の docstring を参照してください。

---

## 注意事項 / 実運用上のヒント

- 環境分離: KABUSYS_ENV を `development` / `paper_trading` / `live` に設定し、本番運用時には `live` に切り替えてください。設定値や挙動を環境ごとに分けることで誤発注リスクを低減します。
- .env の取り扱い: 機密情報は `.env.local` 等で管理し、リポジトリに含めないでください。
- OpenAI 呼び出し: レート制限・コストが発生します。バッチサイズや最大記事数のパラメータ（news_nlp の _BATCH_SIZE など）を必要に応じて調整してください。
- DuckDB スキーマ: 初期スキーマや監査スキーマの作成はプロジェクトの初期化スクリプトで確実に行ってください（data.audit.init_audit_schema / init_audit_db を利用）。
- テスト: 多くの内部 API 呼び出しはモック可能な設計になっています（例: news_nlp / regime_detector 内の _call_openai_api を patch してテスト）。

---

README に含めてほしい追加情報（例: インストール用の pyproject.toml / requirements.txt、初期スキーマ SQL、CI 手順など）があれば教えてください。必要に応じてサンプル .env のテンプレートも作成します。