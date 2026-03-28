# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）、さらには市場レジーム判定など、トレーディング戦略の研究・運用に必要な機能群を提供します。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- データ取得 / ETL
  - J-Quants API からの株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーの差分取得と DuckDB への冪等保存（ON CONFLICT）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- データ品質チェック
  - 欠損値、重複、スパイク（急変）、日付不整合（未来日付・非営業日データ）チェック
- ニュース収集 / NLP
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメントスコアリング（ai_scores）
  - マクロニュースを使った市場レジーム判定（ETF 1321 の MA200 と LLM を組み合わせ）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを DuckDB に初期化
  - order_request_id を冪等キーとして発注の二重化を防止
- カレンダー管理
  - market_calendar の取得・保持・営業日判定・次・前営業日探索・期間内営業日取得

---

## 必要条件

- Python 3.10 以上（型注釈や union 型演算子 `|` を使用）
- 推奨ライブラリ（pip でインストール）
  - duckdb
  - openai
  - defusedxml

（その他、標準ライブラリと urllib 等を使用します）

requirements.txt を用意している場合はそれを参照してください（本リポジトリには簡易に必要ライブラリを記載してください）。

---

## 環境変数 / 設定

KabuSys は環境変数から設定を読み込みます。プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（ただしテスト時などに自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な必須環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（発注・実行用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

任意（デフォルトあり）:

- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
- LOG_LEVEL — ログレベル: `DEBUG`|`INFO`|`WARNING`|`ERROR`|`CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）

.env の例（.env.example を参照のこと）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 例（最低限）:
     ```
     pip install duckdb openai defusedxml
     ```
   - またはプロジェクトに requirements.txt があれば:
     ```
     pip install -r requirements.txt
     ```

4. 環境変数 (.env) を作成
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成して上記の必須変数を設定してください。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（Python API 例）

以下は主要ユースケースの簡単な利用例です。実行には DuckDB 接続（duckdb.connect）と必要な環境変数が必要です。

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # -> 書き込み銘柄数
print(f"written: {written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
ret = score_regime(conn, target_date=date(2026, 3, 20))
print("regime score updated")
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # parent ディレクトリは自動作成されます
```

- 研究用：ファクター計算・IC 計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026,3,20))
fwd = calc_forward_returns(conn, target_date=date(2026,3,20))
ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

---

## 自動 .env 読み込みの挙動

- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` → `.env.local` の順で読み込みます。
- 読み込みは OS 環境変数より優先されません（OS 環境変数があるキーは上書きされません）。`.env.local` は上書き用として扱われ、`.env` の値を上書きできます。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール構成は以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py  — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL Result 再エクスポート
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - news_collector.py      — RSS ニュース収集
    - quality.py             — データ品質チェック
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - audit.py               — 監査ログ（監査スキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - (その他: strategy / execution / monitoring 等のエントリポイントが想定される)

---

## 注意事項 / 設計上のポイント

- Look-ahead bias を防ぐため、モジュールの多くは内部で datetime.today() / date.today() を直接参照せず、呼び出し側から target_date を渡す設計です。バックテスト等での使用時は target_date を明示してください。
- OpenAI 呼び出しにはリトライ・フォールバック機構があり、API 失敗時はゼロスコアでフォールバックする等のフェイルセーフが入っています（ただし API キーは必須）。
- DuckDB への書き込みはできる限り冪等（ON CONFLICT）で実装されています。
- RSS 取得には SSRF 対策や Gzip サイズチェック、XML パースのセーフ実装（defusedxml）を行っています。

---

## テスト・開発

- 自動 .env 読み込みを無効にしてユニットテストを実行する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  pytest
  ```
- OpenAI 呼び出しや外部 HTTP 呼び出しはモックして単体テストを作成することを推奨します（コード内に unittest.mock.patch で差し替えることを想定したフックが存在します）。

---

## 貢献・ライセンス

- 貢献はプルリクエストで歓迎します。コードスタイル・型チェック・ユニットテストをできるだけ含めてください。
- ライセンス表記はリポジトリルートの LICENSE を参照してください（本 README では明示していません）。

---

README の内容で不明点や、特定の利用例（例: ETL の定期ジョブ化、kabuステーションへの発注ワークフロー）を追加で希望する場合は、用途に応じてサンプルコードや詳細手順を作成します。必要なセクションを教えてください。