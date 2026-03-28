# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants 連携）やマーケットカレンダー管理、ニュース収集・NLP（OpenAI）によるセンチメント評価、ファクター計算、監査ログ（発注／約定トレース）など、システム全体のバックエンドコンポーネントを提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（date/target_date を明示的に受け取る）
- DuckDB をデータレイクとして利用
- J-Quants API / OpenAI への堅牢な呼び出し（レートリミット・リトライ・トークン自動更新）
- 冪等性・監査性を重視（ON CONFLICT、UUID ベースの監査テーブル 等）

---

## 機能一覧

- データ取得・ETL
  - J-Quants からの株価（日次OHLCV）、財務データ、上場情報、JPXカレンダー取得
  - 差分取得・バックフィル・品質チェック（欠損、スパイク、重複、日付整合性）
  - ETL の結果を ETLResult に集約

- マーケットカレンダー管理
  - 営業日判定 / 前後営業日の計算 / 期間内営業日取得
  - JPX カレンダーを差分更新するバッチジョブ

- ニュース関連
  - RSS 収集（SSRF 対策・トラッキング除去・gzip 上限）
  - news_symbols と raw_news の紐付け
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュース + ETF（1321）200日MA乖離の合成による市場レジーム判定（score_regime）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化
  - 監査用の DuckDB 初期化ユーティリティ

- その他
  - 設定管理（環境変数および .env 自動ロード）
  - J-Quants クライアント（トークン管理・レート制御・リトライ）
  - 汎用統計ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以降（コード内で `|` 型注釈 等を使用）
- ネットワークアクセス（J-Quants/API、OpenAI、RSS）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   依存は主に以下を使用します（プロジェクトの pyproject / requirements に合わせてください）:

   pip install duckdb openai defusedxml

   - duckdb: データベース
   - openai: OpenAI API クライアント
   - defusedxml: 安全な XML パーサ（RSS）

   ※ その他標準ライブラリのみで実装されている部分が多いですが、実際の運用ではログ周りや Slack 連携等の追加パッケージが必要になる場合があります。

3. パッケージを開発モードでインストール（任意）
   - プロジェクトルートに pyproject.toml / setup.cfg 等があれば:
     pip install -e .

4. 環境変数の設定
   プロジェクトは起動時にプロジェクトルート（.git または pyproject.toml を探索）を検出し、`.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

   任意／推奨:
   - OPENAI_API_KEY        : OpenAI 呼び出し用（score_news, score_regime に渡すことも可能）
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 sqlite パス（デフォルト data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単なコード例）

基本的な使い方は Python からモジュールをインポートして関数を呼び出します。以下は代表的な操作例です。

1) DuckDB 接続と ETL 実行（日次ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# デフォルトの DuckDB パスを settings.duckdb_path で取得
conn = duckdb.connect(str(settings.duckdb_path))

# ETL を実行（target_date を省略すると today）
result = run_daily_etl(conn)

print(result.to_dict())
```

2) ニュースセンチメント計算（OpenAI API キーは環境変数 or 引数で指定）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム（マクロ + ETF）判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

5) 監査DB（audit）初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

conn = init_audit_db(Path("data/audit.duckdb"))
# これで signal_events / order_requests / executions テーブルが作成されます
```

注意点：
- OpenAI 呼び出しは外部 API コールのためネットワーク・料金に注意してください。テストでは api_key を None にするか、モックして実行することを推奨します。
- J-Quants に接続するには JQUANTS_REFRESH_TOKEN が必要です。jquants_client はトークンの自動リフレッシュとレート制御を行います。

---

## 主要 API（概観）

- kabusys.config.settings — 環境設定アクセス（settings.jquants_refresh_token 等）
- kabusys.data.jquants_client — J-Quants API の fetch/save メソッド
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - get_id_token
- kabusys.data.pipeline — run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl / ETLResult
- kabusys.data.quality — run_all_checks 他の品質チェック関数
- kabusys.data.calendar_management — is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- kabusys.data.news_collector — fetch_rss / preprocess_text 等（RSS 収集）
- kabusys.ai.news_nlp — score_news（銘柄別ニューススコア）
- kabusys.ai.regime_detector — score_regime（市場レジーム判定）
- kabusys.research.* — ファクター計算・統計ユーティリティ
- kabusys.data.audit — init_audit_schema / init_audit_db

---

## ディレクトリ構成

（主要ファイル抜粋）
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ etl.py
│  ├─ quality.py
│  ├─ stats.py
│  ├─ news_collector.py
│  ├─ calendar_management.py
│  └─ audit.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ ai/ (上記)
└─ research/ (上記)
```

各モジュールは責務ごとに分割されています（data: ETLやAPIクライアント、ai: NLP/レジーム判定、research: ファクター解析、audit: 監査ログ）。

---

## 運用上の注意・トラブルシューティング

- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml）を基準に .env と .env.local を読み込みます。
  - 優先順位: OS 環境変数 > .env.local > .env
  - テスト時などで自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI 呼び出し
  - gpt-4o-mini（JSON Mode）を標準で使用します。API レート・コストに注意してください。
  - API エラーやパース失敗は一部フェイルセーフ（スコア 0.0 やスキップ）として扱います。

- J-Quants クライアント
  - レート制限（120 req/min）を守るため内部でスロットリングしています。
  - 401 が返ると refresh token によるトークン再発行を自動で試みます。

- DuckDB
  - DuckDB のバージョン差異（executemany の空リスト不可など）に配慮した実装になっていますが、実行時のエラーが出た場合は DuckDB バージョンを確認してください。

---

## 最後に

このリポジトリはライブラリ的なコンポーネント群を提供する形で設計されています。CLI やサービス化（エージェント、ジョブスケジューラ、監視）などは別途ラッパーを用意して運用してください。

ご不明点や README に追加したい使用例があれば教えてください。補足のサンプルスクリプトや CI 用の手順も作成します。