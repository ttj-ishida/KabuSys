# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
J‑Quants から市場データを取得して DuckDB に格納し、NLP / LLM を使ったニュース評価や市場レジーム判定、研究用のファクター計算、ETL パイプラインやデータ品質チェック、監査ログなどを提供します。

主な用途
- 日次の市場データ ETL（株価・財務・市場カレンダー）
- ニュースの収集と LLM による銘柄センチメント算出
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- 監査ログスキーマの初期化（発注 → 約定のトレーサビリティ）
- 研究（ファクター計算・将来リターン・IC 等）
- データ品質チェック

---

## 機能一覧（抜粋）

- 環境変数 / .env 読み込み（settings）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）基準で自動ロード
  - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J‑Quants API クライアント（rate limit・リトライ・トークン自動リフレッシュ）
  - fetch/save の idempotent 実装（DuckDB へ ON CONFLICT DO UPDATE）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース収集（RSS）と前処理、raw_news / news_symbols への保存
  - SSRF 対策、トラッキングパラメータ除去、サイズ制限などの防御ロジック
- ニュース NLP（OpenAI）による銘柄別センチメント算出（score_news）
  - バッチ送信、レスポンス検証、スコアクリップ、フェイルセーフ動作
- 市場レジーム判定（score_regime）
  - ETF (1321) の 200日 MA 乖離 + マクロニュース LLM スコアを合成して 'bull'/'neutral'/'bear' 判定
- 研究モジュール
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリー
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions）の初期化関数

---

## 要件

- Python 3.10+
- 主要依存ライブラリ（最小限）:
  - duckdb
  - openai
  - defusedxml
- その他（ネットワーク / システム機能）: 標準ライブラリのみで多くを実装していますが、実行用途に応じて追加パッケージが必要になる場合があります。

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# パッケージを editable インストールする場合（プロジェクトルートに pyproject.toml または setup.py があること）
pip install -e .
```

---

## 環境変数（主要なキー）

プロジェクトは環境変数 / .env に依存します。主に次のキーを設定してください（必須は明示）:

必須:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知を使用する場合
- SLACK_CHANNEL_ID — Slack チャンネル ID

必須（kabu ステーション使用時）:
- KABU_API_PASSWORD

OpenAI 関連:
- OPENAI_API_KEY — news_nlp / regime_detector のデフォルト API キー（関数呼び出し時に api_key を渡すことも可能）

データベース / パス（省略時デフォルトあり）:
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH など（監視用）

その他:
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動 .env ロードを無効化

プロジェクトは起動時にプロジェクトルート（.git または pyproject.toml）を探索し .env/.env.local を自動で読み込みます（OS 環境変数を上書きしない設計、.env.local は上書き）。テスト等で自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env):
```env
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-xxxx...
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（手順化）

1. Python 仮想環境作成・有効化
2. 必要パッケージをインストール（上記参照）
3. .env/.env.local をプロジェクトルートに作成（または環境変数を設定）
4. DuckDB ファイルを置くディレクトリ（例: data/）を作成
5. 監査ログ DB を初期化する（必要に応じて、デフォルトでは ETL 実行時にテーブル作成が行われる関数を呼ぶ）

例: 依存インストール
```bash
pip install duckdb openai defusedxml
```

---

## 使い方（サンプルコード）

ここでは代表的な操作例を示します。すべて Python スクリプトから呼び出す形になります。

- 設定と DuckDB 接続を使った ETL 実行（日次 ETL）:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP スコア算出（OpenAI API キーは環境変数 OPENAI_API_KEY を使用）:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化（独立した audit DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続オブジェクト
```

- J‑Quants の id_token を直接取得（テストや手動実行用）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token が必要
print(token)
```

注意:
- news_nlp.score_news / regime_detector.score_regime は OpenAI の API 呼び出しを行います。API キーの設定と料金・レート管理には十分ご注意ください。
- 各関数はルックアヘッドバイアス対策として内部で date.today() を必ず参照しない実装方針があります（target_date を必ず渡すことで再現性ある処理が可能です）。

---

## よくある操作フロー（例）

1. 定期ジョブで daily ETL を実行（run_daily_etl） → DuckDB にデータ蓄積
2. 夜間バッチでニュース収集（news_collector.fetch_rss → save）→ raw_news を更新
3. 朝方、score_news（ニュース NLP）を実行して ai_scores を更新
4. score_regime を実行して market_regime を更新
5. 監視・実行（execution / monitoring モジュール）により発注・約定を記録（監査ログ）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主な構成（コードベースからの抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                         -- 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                      -- ニュース NLP / OpenAI バッチ処理
    - regime_detector.py               -- 市場レジーム判定（ETF MA + マクロ LLM）
  - data/
    - __init__.py
    - jquants_client.py                -- J‑Quants API クライアント + save_* 関数
    - pipeline.py                      -- ETL パイプライン / run_daily_etl
    - etl.py                           -- ETLResult 再エクスポート
    - calendar_management.py           -- 市場カレンダー管理・判定
    - stats.py                         -- z-score 正規化ユーティリティ
    - quality.py                       -- データ品質チェック
    - audit.py                         -- 監査ログスキーマ初期化（signal/order/execution）
    - news_collector.py                -- RSS 取得・前処理・保存
  - research/
    - __init__.py
    - factor_research.py               -- モメンタム / ボラ / バリュー等
    - feature_exploration.py           -- 将来リターン / IC / 統計サマリー

（注）README に含めたファイル一覧はリポジトリ内の一部を抜粋しています。実際のツリーはリポジトリの内容に依存します。

---

## 注意事項 / 運用上のポイント

- OpenAI や J‑Quants は API 利用料・レート制限があります。適切な API キー管理・リトライ・バックオフ制御がライブラリ内に実装されていますが、運用側でも監視してください。
- DuckDB に対する executemany やトランザクションの振る舞いはバージョン依存の挙動があるため、重大なバルク処理を行う際は環境での動作確認を行ってください（コード内にも注意コメントあり）。
- ニュース収集時は外部 URL を開くため SSRF 防御等に注意していますが、運用環境でのアクセス制御は別途考慮してください。
- 本ライブラリは「データ取得・評価・監査ログ」までを担う基盤であり、実際の売買執行（証券会社 API に接続しての発注）層は execution / broker 絡みで別実装または拡張が必要です。

---

もし README に追加したい内容（例: CI / テスト手順、具体的な .env.example、CLI の使い方など）があれば伝えてください。必要に応じてサンプルスクリプトや運用チェックリストも作成します。