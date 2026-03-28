# KabuSys — 日本株自動売買プラットフォーム（README）

簡潔説明:
KabuSys は日本株向けのデータパイプライン、リサーチ・ファクター計算、ニュース NLP（LLM を用いたセンチメント評価）、市場レジーム判定、監査ログ機能などを備えた自動売買/リサーチ基盤のライブラリ群です。内部的には DuckDB をデータストアに使用し、J-Quants API / RSS / OpenAI（gpt-4o-mini 等）など外部サービスと連携します。

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）と設定
- 使い方（主要 API の例）
- ディレクトリ構成
- 注意事項 / 補足

---

## プロジェクト概要
KabuSys は以下の目的を想定して設計されています。
- J-Quants から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS を取得して raw_news に格納するニュース収集（SSRF / Gzip / トラッキング削除などの安全対策あり）
- OpenAI を使ったニュースセンチメント（銘柄別 ai_score）およびマクロセンチメントの評価 → 市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）とリサーチ用ユーティリティ
- データ品質チェック（欠損 / 重複 / スパイク / 日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を管理するスキーマ提供

設計上の特徴:
- ルックアヘッドバイアスを防ぐため、内部処理で現在時刻を安易に参照しない（ターゲット日ベースで処理）
- DuckDB を中心に SQL + Python で効率的にデータ処理
- 冪等性（ON CONFLICT 等）・リトライ・レート制御・セキュリティ対策（SSRF / XML / サイズチェック）を重視

---

## 機能一覧
- ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル対応）
- J-Quants クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info, get_id_token
- ニュース収集: RSS 取得・前処理・raw_news 保存（_make_article_id、preprocess_text 等）
- ニュース NLP: score_news（銘柄別センチメントを ai_scores に保存）
- 市場レジーム判定: score_regime（ETF 1321 の MA とマクロセンチメントを合成）
- リサーチ: calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- データ品質: check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- 監査ログ: init_audit_schema / init_audit_db（監査用テーブル群の初期化）
- 設定管理: .env 自動ロード（プロジェクトルート検出）、Settings クラス経由でアクセス

---

## セットアップ手順

前提
- Python 3.10 以上（ソースで | 型注釈や typing の機能を使用）
- ネットワーク経由で J-Quants / OpenAI API にアクセス可能

基本手順
1. リポジトリをクローン
   - git clone ... (省略)

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主要依存例:
     - duckdb
     - openai
     - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに pyproject.toml がある場合は `pip install -e .` や `pip install -r requirements.txt` を使用）

4. 環境変数を設定
   - プロジェクトルートに `.env` を配置すると自動的に読み込まれます（.git と pyproject.toml を探してプロジェクトルートを特定）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。

---

## 環境変数（主なもの）
以下はコード内で参照される主要な環境変数です。必須・任意を分けて記載します。

必須（本番的な運用で必要）
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（発注等で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャネル ID

AI / LLM 関連
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で参照）

オプション（デフォルト値あり）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — 有効値: development, paper_trading, live （デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL （デフォルト INFO）

.env 例（プロジェクトルートに .env を置く）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な API／実行例）

以下は最小限の Python スニペット例です。実運用ではロギングや例外処理、接続管理を追加してください。

1) DuckDB 接続を作って日次 ETL を回す
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # または settings.duckdb_path
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを実行（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
print("書き込み件数:", n_written)
```

3) 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を参照
```

4) 監査 DB の初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_duckdb.db")
# これで監査用テーブル(signal_events, order_requests, executions) が作成されます
```

5) カレンダー関連ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## ディレクトリ構成（主要ファイル）
※ src 配下にパッケージが配置されています（src layout）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理（.env 自動ロード / Settings）
  - ai/
    - __init__.py
    - news_nlp.py         — 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py  — マクロ + ETF MA で市場レジームを判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch / save / auth）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - news_collector.py   — RSS 取得・前処理・保存
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py          — データ品質チェック
    - stats.py            — 共通統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化
    - etl.py              — ETL 結果型の再エクスポート
  - research/
    - __init__.py
    - factor_research.py  — モメンタム/バリュー/ボラティリティ等の計算
    - feature_exploration.py — forward returns / IC / summary
  - ai/ （上記）
  - research/
  - monitoring/ (README の先頭に示唆のあるモジュール群がある想定)

各モジュールは docstring に設計方針・処理フローが詳細に記載されているため、利用方法は docstring を参照してください。

---

## 注意事項 / 補足
- 自動環境変数読み込み:
  - config._find_project_root() は .git または pyproject.toml を起点にプロジェクトルートを特定し、.env/.env.local を読み込みます。テスト時や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを停止できます。
- OpenAI 呼び出し:
  - news_nlp / regime_detector は OpenAI の JSON mode を想定して厳密な JSON をパースします。API の応答が期待通りでない場合はフォールバックしてスコア 0.0 を使用する設計です（フェイルセーフ）。
- J-Quants API:
  - レート制御（120 req/min）やトークン自動リフレッシュ、ページネーションを備えています。get_id_token の挙動や id_token キャッシュに注意してください。
- DB の互換性:
  - 一部の DuckDB バージョン差異（executemany の空リスト取り扱い等）を考慮した実装があります。DuckDB は定期的にバージョンアップしてください。
- セキュリティ:
  - RSS 取得における SSRF 防止、XML の defusedxml 利用、レスポンスサイズ制限などを実装していますが、運用環境に合わせた追加防御（プロキシ設定、TLS 証明書の検証等）を推奨します。

---

問題報告・寄稿
- バグ報告や改善提案があれば issue を立ててください。新しい機能追加は事前に設計案（簡潔な PR）を投げてもらえるとスムーズです。

以上が KabuSys の README です。必要であれば README にサンプル .env.example を追記したり、CLI 実行例 / systemd Cron ジョブ例などを追加できます。追加希望があれば教えてください。