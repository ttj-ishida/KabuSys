# KabuSys — 日本株自動売買システム

軽量なデータプラットフォーム、リサーチ、AI 補助のニュースセンチメント評価、監査ログを備えた日本株向け自動売買用ライブラリです。  
この README はリポジトリ内のソースコードに基づいて作成されています。

主な設計方針：
- Look‑ahead bias を防ぐ（関数内で date.today()/datetime.today() を直接参照しない）
- DuckDB を用いたローカル DB 中心の ETL/解析
- J-Quants / OpenAI API との安全な連携（レート制御・リトライ・トークン自動更新等）
- 冪等性を考慮した DB 書き込み（ON CONFLICT / トランザクション制御）
- モジュール単位でテストしやすい設計（API 呼び出しは差し替え可能）

---

## 機能一覧

- データ取得・ETL（jquants_client, pipeline）
  - 株価（日足 OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存
  - 差分／バックフィル処理、品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF 対策、受信サイズ制限、トラッキングパラメータ除去
- AI ベースの NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコア算出
  - バッチ処理・JSON Mode 使用・堅牢なリトライとレスポンス検証
- 市場レジーム判定（ai.regime_detector）
  - ETF（1321）200日 MA 乖離とマクロニュースセンチメントの合成で日次レジーム判定
- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン / IC 計算、ファクター統計サマリー、Zスコア正規化
- マーケットカレンダー管理（data.calendar_management）
  - JPX カレンダーの更新、営業日判定、next/prev trading day 取得
- 監査ログ（data.audit）
  - signal → order_request → execution のトレーサビリティテーブルと初期化ユーティリティ
- 汎用統計ユーティリティ（data.stats）

---

## セットアップ手順

前提
- Python 3.10+（typing | union 型表記から推奨）
- システムに DuckDB がインストール済み（Python パッケージ duckdb を使用）
- OpenAI API キー、J-Quants リフレッシュトークン 等を取得済み

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   - 実プロジェクトでは requirements.txt / pyproject.toml を用意してください。
   - 本コードベースで使われている主な依存：
     - duckdb
     - openai
     - defusedxml
   ```bash
   pip install duckdb openai defusedxml
   # 開発用: pip install -e .
   ```

4. 環境変数の設定
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（設定は後述）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須の環境変数（主要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector の既定値）
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション（デフォルト有り）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_pwd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env の読み込みルール:
- OS 環境変数 > .env.local > .env の順で優先読み込み
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを抑止可

---

## 使い方（主要ユースケースの例）

以下は主要 API の簡単な使用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続と日次 ETL の実行例
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 今日（もしくは任意の日）の ETL を実行
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- OpenAI を使ったニューススコアリング（score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- J-Quants の ID トークン取得（内部で settings.jquants_refresh_token を使用）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を参照
print(token)
```

- 監査ログ DB 初期化（audit テーブルの作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ作成されます
```

- 研究用ファクター計算例
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "1234", "mom_1m": ..., ...}, ...]
```

ログレベルは環境変数 `LOG_LEVEL` で制御します。

---

## ディレクトリ構成（主要ファイル）

（この README は src/kabusys 以下のソースを元に作成しています）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数ローディング・Settings クラス（.env 自動読み込み、必須チェック）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント算出（OpenAI を用いるバッチ処理）
    - regime_detector.py — ETF MA200 とマクロニュースの合成で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得／保存処理・リトライ・レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集 / 前処理 / raw_news 保存（SSRF 対策あり）
    - calendar_management.py — JPX カレンダー管理・営業日判定・calendar_update_job
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログテーブル定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - (その他)
    - execution, monitoring, strategy パッケージは __all__ に含まれており、実運用の発注・監視ロジックを想定

---

## 注意事項 / 運用上のヒント

- Look-ahead を防ぐ設計のため、多くの関数は明示的に target_date を受け取ります。バックテストや再現性のために必ず日付を指定して利用してください。
- OpenAI 呼び出しはコストとレート制限がかかります。実行前に API キーと使用ポリシーを確認してください。
- jquants_client は API レート（120 req/min）を厳守する実装です。大量取得時はページネーションとレート制御を考慮してください。
- news_collector は外部 RSS を取得します。RSS ソースの信頼性確認と同時に、SSRF 対策やレスポンスサイズ制限の挙動を理解して利用してください。
- DuckDB スキーマ（テーブル名 raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar 等）に依存するため、既存 DB を流用する場合はスキーマ互換性を確認してください。
- テスト実行時は自動 .env 読み込みを無効化するか適切にモックしてください（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## 開発 / テスト

- モジュールごとに外部 API 呼び出しを差し替え可能（_call_openai_api や _urlopen 等をモックする設計）。
- ETL や AI 関連処理は副作用（DB 書き込み）を伴うため、テスト用インメモリ DuckDB（db_path=":memory:"）での実行が推奨されます。
- .env.example をプロジェクトルートに置き、開発環境でコピーして値を埋めると良いです。

---

この README はコードベースの主要な API と運用フローを簡潔にまとめたものです。詳細な実装や仕様は各モジュールの docstring（ソース内コメント）を参照してください。質問や追加で README に載せたい項目があれば教えてください。