# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータ取得・品質管理・特徴量計算・ニュースセンチメント評価・市場レジーム判定・監査ログ管理までを含む日本株自動売買／リサーチ向けのライブラリ群です。DuckDB をデータストアとして利用し、J-Quants API や OpenAI（gpt-4o-mini）を外部 API として統合します。設計上、バックテストでのルックアヘッドバイアスを避けるために日付参照の扱いに注意が払われています。

---

## 主な機能一覧

- ETL（デイリー）パイプライン
  - J-Quants から株価（OHLCV）・財務データ・JPX カレンダーを差分取得して DuckDB に保存
  - 差分更新 / バックフィル / ページネーション対応 / 冪等保存（ON CONFLICT）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS）
  - URL 正規化・トラッキングパラメータ除去・SSRF 対策・gzip サイズ制限
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（ai_scores へ保存）
  - レート制限・リトライ・レスポンス検証を備えた実装
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して daily レジーム判定
- リサーチ用ファクター計算
  - Momentum / Volatility / Value / Liquidity 等の定量ファクターを DuckDB 上で計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z スコア正規化
- マーケットカレンダー管理
  - market_calendar の読み書き、営業日判定、次/前営業日検索、夜間バッチ更新ジョブ
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化（UTC、冪等）
  - order_request_id を冪等キーとして二重発注防止をサポート
- J-Quants API クライアント
  - レートリミッタ、401 自動リフレッシュ、リトライ（指数バックオフ）、ページネーション対応
- 汎用ユーティリティ
  - 設定管理（.env 自動ロード）、統計ユーティリティ、日付変換等

設計上の注意点（抜粋）
- datetime.today() / date.today() を直接参照しない処理設計（ルックアヘッドバイアス防止）
- DuckDB 接続を受け取る関数群で副作用を限定
- 外部 API 呼び出しはリトライ・フェイルセーフ設計（失敗時に処理継続する部分が多い）

---

## セットアップ手順

前提
- Python 3.10+（typing union 等を利用）
- ネットワーク接続（J-Quants / OpenAI）

1. リポジトリをクローン（またはプロジェクト配布物を取得）
   ```
   git clone <repo_url>
   cd <repo_dir>
   ```

2. 仮想環境作成・有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. パッケージをインストール
   - setup.py / pyproject.toml があれば editable install
   ```
   pip install -e .
   ```
   - 本リポジトリで明示的に使われている外部依存（例）
   ```
   pip install duckdb openai defusedxml
   ```
   （実際の依存は pyproject.toml / requirements.txt を参照してください）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込みは .git または pyproject.toml を基準にルート探索）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（代表例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
     - SLACK_BOT_TOKEN:（Slack 通知がある場合）
     - SLACK_CHANNEL_ID:（Slack 通知先）
     - KABU_API_PASSWORD: kabuステーション API パスワード（利用する場合）
     - OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime 等）
   - 任意（デフォルトがある）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
     - DUCKDB_PATH: データベースファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡易ガイド）

以下は Python REPL / スクリプトからの基本的な利用例です。各関数は DuckDB 接続オブジェクト（duckdb.connect）を受け取ります。

1. 設定参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 必須項目（未設定時は ValueError）
```

2. DuckDB 接続
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

3. ETL（日次パイプライン）を実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026,3,25))
print(result.to_dict())
```

4. 単体 ETL ジョブ（株価 / 財務 / カレンダー）
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
from datetime import date

run_prices_etl(conn, target_date=date(2026,3,25))
run_financials_etl(conn, target_date=date(2026,3,25))
run_calendar_etl(conn, target_date=date(2026,3,25))
```

5. ニュースのセンチメントスコア（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_keyを明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください
count = score_news(conn, target_date=date(2026,3,25), api_key="sk-xxxxx")
print(f"scored {count} symbols")
```

6. 市場レジーム判定（OpenAI 必須）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,25), api_key="sk-xxxxx")
```

7. 監査ログ DB 初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
```

8. リサーチ関数の呼び出し例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

moms = calc_momentum(conn, target_date=date(2026,3,25))
forward = calc_forward_returns(conn, target_date=date(2026,3,25), horizons=[1,5,21])
ic = calc_ic(moms, forward, factor_col="mom_1m", return_col="fwd_1d")
```

注意点
- OpenAI API 呼び出しはレート・エラーに対してリトライ・フェイルセーフ設計ですが、API キーが未設定の場合は ValueError が発生します。
- ETL は差分取得を基本とします。初回は過去の十分な期間を取得する設計です。

---

## 推奨環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。get_id_token() で ID トークンを取得します。
- OPENAI_API_KEY (score_news / score_regime 等で使用)  
- KABU_API_PASSWORD (必須にしている箇所あり)  
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)  
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知用)  
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)  
- SQLITE_PATH (任意, default: data/monitoring.db)  
- KABUSYS_ENV (development | paper_trading | live)  
- LOG_LEVEL (DEBUG/INFO/...)  

.env ファイルの書式は shell の `KEY=VALUE` に準拠し、コメント・クォートをサポートします。.env と .env.local がプロジェクトルートにあれば自動で読み込まれます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュール（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（銘柄別センチメント）
    - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult 再エクスポート
    - news_collector.py             — RSS ニュース収集
    - calendar_management.py        — マーケットカレンダー管理・判定
    - stats.py                      — 統計ユーティリティ（Zスコア等）
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログ（テーブル作成 / 初期化）
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Value / Volatility ファクター
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー
  - ai/、research/、data/... の他に strategy / execution / monitoring 等の名前は
    __init__ の __all__ に含まれていますが、各モジュールは必要に応じて実装・拡張してください。

（上記はコードベースから抽出した主要モジュール構成です）

---

## 開発者向けメモ・設計上の重要点

- ルックアヘッドバイアス防止
  - 多くの処理（news window、regime 判定、ETL の target_date 指定）は現在日時を内部で参照せず、明示的に target_date を与える設計です。バックテストや再現性のために重要です。
- トランザクション
  - 重要な書き込み（市場レジーム、ai_scores への一括置換、audit 初期化など）は BEGIN/DELETE/INSERT/COMMIT で冪等性・整合性を保つ実装がされています。DuckDB の executemany に関する互換性考慮も含まれます。
- 外部 API の取り扱い
  - J-Quants: レート制限（120 req/min）、401 のトークン自動リフレッシュ、リトライ（指数バックオフ）を実装
  - OpenAI: JSON mode を使った厳密なレスポンス検証・リトライ（429/タイムアウト/5xx）を備え、失敗時はフェイルセーフで 0 相当の中立値にフォールバックすることがある
- セキュリティ / 安全対策
  - RSS の取得には SSRF 対策（プライベート IP 判定、リダイレクト検査）、defusedxml による XML パース安全化、大きすぎるレスポンスの検査（最大バイト数）を実装
- ロギング
  - 各モジュールは logger を利用して処理の進捗や警告・エラーを出力します。環境変数 LOG_LEVEL により制御できます。

---

## よくある質問（FAQ）

Q: 初回セットアップで何日分のデータを取り込めば良いですか？  
A: J-Quants の提供期間に依存します。pipeline モジュールは初回に _MIN_DATA_DATE（実装例では 2017-01-01）から取り込み可能な設計になっています。初回は時間がかかります。

Q: OpenAI を使わずにローカルだけで試したいです。  
A: score_news / score_regime の呼び出しは api_key を必須としていますが、テスト時は内部の _call_openai_api をモック（unittest.mock.patch）して差し替えることが可能です。settings で OPENAI_API_KEY を設定しない場合、関数は ValueError を投げます。

Q: データベースのスキーマ（テーブル定義）はどこに？  
A: audit.py に監査ログ用の DDL が定義されています。raw_prices / raw_financials / market_calendar 等のテーブル定義はデータスキーマ初期化モジュール（ここに含まれていない場合は別モジュール）で定義される想定です。必要に応じてスキーマ初期化コードを実装してください。

---

必要であれば、README にさらに以下を追加できます：
- 例: .env.example のテンプレート
- 詳細な API 使用例や CLI スクリプト（もし提供されている場合）
- テストの実行方法（pytest など）
- 開発・デプロイ手順（systemd / cron / Airflow での運用例）

ご希望があれば、.env.example のテンプレート作成や、CI / 実運用（cron / Airflow）用の起動スクリプト例も作成します。