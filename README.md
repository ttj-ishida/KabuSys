# KabuSys

日本株のデータプラットフォーム兼自動売買補助ライブラリ。  
DuckDB をデータレイヤに用い、J-Quants / RSS / OpenAI など外部ソースを統合して以下を提供します：

- データ ETL（株価・財務・市場カレンダー）
- ニュース収集・NLP（OpenAI を用いた銘柄センチメント）
- 市場レジーム判定（ETF + マクロニュースの合成）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- データ品質チェック、監査（監査ログ用スキーマ初期化）
- J-Quants クライアント（取得・保存・レート制御・リトライ）

バージョン: 0.1.0

---

## 主な機能

- ETL（data.pipeline）
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェックを順次実行
  - 差分更新・バックフィル対応、DuckDB への冪等保存
- ニュース & NLP（ai.news_nlp）
  - RSS 収集・前処理（news_collector）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメントスコア化（score_news）
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離 + マクロニュースセンチメントの合成 → bull/neutral/bear 判定（score_regime）
- 研究用（research）
  - モメンタム / ボラティリティ / バリュー計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- データ品質（data.quality）
  - 欠損・重複・スパイク・日付不整合の検出（QualityIssue）
- 監査（data.audit）
  - signal → order_request → executions のトレーサビリティ用スキーマ初期化（init_audit_schema / init_audit_db）
- J-Quants クライアント（data.jquants_client）
  - API レート制御、リトライ、token リフレッシュ、DuckDB へ冪等保存

---

## 要件（推奨）

- Python 3.10+
- 必須パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の依存はプロジェクトの運用方針に合わせて追加してください）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install -e .               # パッケージとしてインストールする場合
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそれを使ってください）

4. 環境変数を設定
   プロジェクトルート（.git または pyproject.toml を含む場所）に `.env` / `.env.local` を置くと自動的に読み込まれます（読み込みは config モジュールが行います）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
   - KABU_API_BASE_URL — kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知に使用（任意）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE — paper_trading のモード（instant|partial|never|reject）
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB パス（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 実行監視用
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
   - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 `.env`（抜粋）:
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

5. DuckDB スキーマ初期化など（必要に応じて）
   - 監査ログ用 DB を初期化する例（Python REPL 等で実行）:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - その他スキーマ初期化は運用スクリプト側で実施してください。

---

## 使い方（代表例）

以下サンプルは Python REPL / スクリプトで実行する想定です。

- 日次 ETL 実行（DuckDB 接続を渡す）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path は .env またはデフォルトから取得
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを生成（score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数か api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定（score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルへ書き込み等を行えます
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

注意:
- ai モジュールは OpenAI API 呼び出しを行います。API キーと料金体系に注意してください。
- 各関数は「ルックアヘッドバイアス」を避ける設計（内部で date.today() を参照しない）になっています。バックテストや再現性を意識した運用が可能です。

---

## よくある運用上の注意

- .env 自動読み込み:
  - config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` を自動で読み込みます。
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用途など）。
- DuckDB バージョン依存:
  - 一部の executemany / 型バインドの挙動は DuckDB バージョンに依存する可能性があるため、運用時は安定バージョンを利用してください。
- エラー時のフェイルセーフ:
  - AI API の失敗は多くの箇所でフォールバック（0.0 等）して継続する設計です。監査やログで異常を確認してください。
- トークン管理:
  - J-Quants の id_token は自動リフレッシュされます（refresh token を設定してください）。
  - OpenAI のキー漏洩に注意してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ初期化（version）
- config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（score_news）と関連処理
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save 等）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py — ETLResult 再エクスポート
  - calendar_management.py — 市場カレンダー関連（is_trading_day 等）
  - news_collector.py — RSS 収集・前処理
  - quality.py — データ品質チェック（QualityIssue 等）
  - stats.py — zscore_normalize 等統計ユーティリティ
  - audit.py — 監査ログ用スキーマ定義 / 初期化
- research/
  - __init__.py — 研究用 API 再エクスポート
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — forward returns / IC / factor_summary / rank
- ai モジュールと research モジュールの間に明確な責務分離があります（AI 呼び出しの内部関数共有を避ける等）。

---

## 貢献・開発メモ

- 単体テストや統合テストは外部 API をモックして実装してください（既にモジュール内にモック差替え用の設計が見られます）。
- コードは「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」を方針に作られています。設計方針を崩さない変更を心がけてください。
- 依存する外部サービス（J-Quants / OpenAI / RSS ソース）に対する rate-limit や課金には注意してください。

---

もし README に追加したい内容（例: サンプルワークフロー、CI 設定、requirements.txt の候補、実運用向けの起動スクリプト例など）があれば教えてください。必要に応じて追記・整形します。