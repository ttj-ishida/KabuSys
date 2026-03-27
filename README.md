# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（注文→約定トレーサビリティ）などのユーティリティ群を提供します。

---

## 主な機能

- ETL（J-Quants API 経由）
  - 日次株価（OHLCV）取得・保存（ページネーション / 冪等）
  - 財務諸表取得・保存
  - JPX マーケットカレンダー取得・保存
  - run_daily_etl による一括パイプライン実行（品質チェック含む）
- データ品質チェック
  - 欠損値、スパイク（急騰/急落）、重複、日付不整合の検出
- ニュース収集 / NLP
  - RSS 取得（SSRF 対策・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアの生成（score_news）
  - マクロニュース + ETF（1321）200日MA乖離を用いた市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions を備えた監査DB初期化ユーティリティ
- J-Quants クライアント
  - レート制御、リトライ、トークン自動リフレッシュ、DuckDB 保存ユーティリティ

---

## 必要環境と依存パッケージ

- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

推奨: 仮想環境を作成して以下をインストールしてください（requirements.txt がある場合はそれを利用）。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## 環境変数（.env）

主要な環境変数（プロジェクトでは .env / .env.local を自動ロードします）:

- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY - OpenAI API キー（score_news / score_regime などで使用）
- KABU_API_PASSWORD - kabuステーション API パスワード（必要時）
- KABU_API_BASE_URL - kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN - Slack 通知用トークン（必要時）
- SLACK_CHANNEL_ID - Slack 通知先チャンネル ID（必要時）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV - 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL - ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）

自動ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

config.Settings API でアプリケーションから取得できます:
```py
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 依存パッケージをインストール
4. プロジェクトルートに `.env` を作成して必要な値を設定
5. デフォルト DuckDB ファイルパス（data/kabusys.duckdb）にアクセスできることを確認

例 `.env`（最低限のキーの例）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要 API の例）

以下は Python REPL あるいはスクリプトでの利用例です。関数は duckdb.DuckDBPyConnection を受け取るので、duckdb.connect() で接続を渡します。

- DuckDB 接続準備（ファイルは自動作成されます）
```py
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（run_daily_etl）
```py
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を指定しなければ今日
print(result.to_dict())
```

- ニュースセンチメント（AI）
```py
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date はスコア対象日（ニュースウィンドウ: 前日15:00 JST ～ 当日08:30 JST）
n_written = score_news(conn, target_date=date(2026,3,20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定
```py
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査DB 初期化（監査ログ専用ファイルを作る例）
```py
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions が作成されます
```

- RSS 取得（ニュースコレクタ）
```py
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用: モメンタム / ボラティリティ / バリュー
```py
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date

moms = calc_momentum(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
```

注意:
- OpenAI 呼び出しは外部 API に依存するため、テストでは _call_openai_api をモックして差し替えることができます。
- J-Quants API 呼び出し時は settings.jquants_refresh_token を利用して自動で id_token を得ます。`get_id_token` を直接呼ぶことも可能です。

---

## ログ / 実行環境

- KABUSYS_ENV（development, paper_trading, live）により振る舞いを切り替えられる箇所があります（settings.is_live 等）。
- LOG_LEVEL でログの詳細度を調整してください。
- config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動ロードします。テスト時などに自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要ファイル / モジュールの一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py    # マクロ + ETF MA200 で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py  # 市場カレンダー管理（is_trading_day 等）
    - etl.py                  # etl 再エクスポート
    - pipeline.py             # run_daily_etl 等の ETL パイプライン
    - stats.py                # zscore_normalize 等の統計ユーティリティ
    - quality.py              # データ品質チェック
    - audit.py                # 監査ログ（テーブル定義・初期化）
    - jquants_client.py       # J-Quants API クライアント（fetch/save）
    - news_collector.py       # RSS 収集 / 前処理
  - research/
    - __init__.py
    - factor_research.py      # calc_momentum / calc_volatility / calc_value
    - feature_exploration.py  # calc_forward_returns / calc_ic / factor_summary / rank
  - monitoring/ (エントリポイント等がある想定)
  - strategy/ (戦略レイヤ、別途実装想定)
  - execution/ (注文実行関連、別途実装想定)

各モジュールは docstring に処理フロー・設計方針・フェイルセーフ方針が詳述されているので実装参照に便利です。

---

## 補足 / 注意点

- Look-ahead バイアス対策:
  - 多くの処理（ETL / news window / regime / factor 計算）は datetime.today() を直接参照せず、明示的な target_date を受け取るか、DB 内の最新取得日を基準にする設計です。バックテスト用途での誤用に注意してください。
- 冪等性:
  - DuckDB への保存は基本的に ON CONFLICT DO UPDATE を利用して冪等性を保証しています。
- エラー処理:
  - 外部 API 呼び出しはリトライやフォールバック（例: macro_sentiment=0.0）を行うよう実装されています。重大な DB 書き込み失敗は上位に例外を投げます。
- セキュリティ:
  - RSS 取得では SSRF 対策（リダイレクト検査 / プライベート IP 拒否）や XML の安全なパース（defusedxml）を実装しています。

---

この README はライブラリのハイレベルな利用方法と構成をまとめたものです。具体的な API の挙動やパラメータについては、各モジュールの docstring を参照してください。必要であれば、サンプルスクリプトや CLI の利用方法を別途追記します。