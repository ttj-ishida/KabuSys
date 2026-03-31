# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants） → データ品質チェック → ニュースNLP / 市場レジーム判定 → 研究用ファクター計算 → 監査ログ（発注トレーサビリティ）といった機能群を提供します。

---

## 主要な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）、財務情報、JPXマーケットカレンダーを差分取得して DuckDB に保存（冪等）
  - ページネーション / レート制限 / トークン自動リフレッシュ / 再試行の実装
- データ品質チェック
  - 欠損（OHLC）、スパイク（前日比）、重複（主キー）、日付整合性（未来日付・非営業日）を検出
- ニュース収集・NLP
  - RSS からニュースを収集し前処理して raw_news に保存（SSRF対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメント評価（ai_scores テーブルへ）
- 市場レジーム判定
  - ETF(1321)の200日移動平均乖離 + マクロニュースセンチメントを合成して日次の市場レジームを判定（bull/neutral/bear）
- 研究用ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算、将来リターンやIC、統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブルとインデックスを初期化するユーティリティ
  - 発注フローのトレースをUUIDチェーンで担保
- 設定管理
  - .env（.env.local）または環境変数から設定を自動読み込み
  - テスト用途に自動読み込みを無効化するフラグ

---

## 必要な環境変数（主要）

少なくとも以下は実運用で必須です（README上のサンプル .env を参照してください）。

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（注文実行等）
- SLACK_BOT_TOKEN — Slack 通知（監視など）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector）に使用（関数引数でも指定可）
- （任意）LOG_LEVEL, KABUSYS_ENV（development / paper_trading / live）

デフォルトの DB パスなど（設定クラスから）:
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PID_FILE_PATH: data/execution.pid

自動 .env ロードはデフォルトで有効。無効化するには環境変数を設定:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 依存パッケージ（例）

主に次を想定しています。プロジェクトの pyproject.toml / requirements に合わせてください。

- duckdb
- openai
- defusedxml
- その他: 標準ライブラリのみで多くを実装していますが、実行環境に合わせて logger 等を設定してください。

インストール例:
```bash
pip install duckdb openai defusedxml
# またはプロジェクトの依存ファイルに従って pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージとして導入）
2. Python 仮想環境を作成・有効化
3. 依存ライブラリをインストール
4. プロジェクトルートに .env を作成（.env.example を参考に）

サンプル .env（例）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxx

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-xxxxxxxx
SLACK_CHANNEL_ID=C01234567

# DB 等
DUCKDB_PATH=data/kabusys.duckdb
```

注意: パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml がある場所）を探索して .env を自動ロードします。テスト等で自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 基本的な使い方（コード例）

以下は簡単な Python スニペット例です。DuckDB の接続を作成して各処理を呼び出します。

- 日次 ETL を実行する例
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースのセンチメントスコアを作成する例
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# 引数 api_key を与えなければ環境変数 OPENAI_API_KEY を使用
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定を実行する例
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する例
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duck.db")
# 以降 conn を使って audit テーブルへアクセスできます
```

注記:
- OpenAI 呼び出しを行う関数（news_nlp.score_news, regime_detector.score_regime）は api_key 引数を受け取り、None の場合は環境変数 OPENAI_API_KEY を参照します。未設定の場合は ValueError が発生します。
- 各関数はルックアヘッドバイアスを避ける設計（target_date 未満のみ参照など）になっています。

---

## よく使う API（主要関数）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult データクラス（結果確認）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.quality
  - run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
- kabusys.data.news_collector
  - fetch_rss（RSS 取得とパース）
- kabusys.ai.news_nlp
  - score_news（銘柄別ニュースセンチメントを ai_scores に書き込み）
- kabusys.ai.regime_detector
  - score_regime（市場レジームを market_regime に書き込み）
- kabusys.data.audit
  - init_audit_db, init_audit_schema（監査テーブル初期化）
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize

---

## 設計上の重要なポイント / 注意事項

- ルックアヘッドバイアス防止
  - AIや研究用関数は datetime.today() や date.today() を直接参照せず、常に引数で与えた target_date を起点に処理します。
- 冪等性
  - ETL の保存処理は基本的に ON CONFLICT（Upsert）で実装しており、再実行してもデータが重複しないよう配慮されています。
- OpenAI / J-Quants API 呼び出し
  - 失敗時は再試行・フォールバックの実装あり（429/タイムアウト/5xx 等）。ただし API キーは運用で必ず管理してください。
- RSS / ネットワーク安全
  - ニュース収集は SSRF 対策や受信サイズ制限（10MB）を備えています。
- DuckDB バージョン差分
  - 一部の実装は DuckDB のバージョン差異（executemany の空リスト扱い等）に配慮した実装になっています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理、自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py  — ニュース NLP スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント、保存関数
    - pipeline.py  — ETL パイプラインと run_daily_etl
    - etl.py — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py — RSS 取得と前処理
    - quality.py  — データ品質チェック（QualityIssue 等）
    - calendar_management.py — 取引日ロジック、カレンダー更新ジョブ
    - audit.py  — 監査ログテーブル初期化・インデックス
    - stats.py  — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - monitoring/ (監視系モジュールは __all__ に含まれる想定)
  - execution/ (注文実行などのモジュールは __all__ に含まれる想定)
  - data/（その他テーブル定義モジュール等）

---

## 開発・テストのヒント

- 自動 .env ロードが邪魔なテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからモジュールをインポートしてください。
- OpenAI の呼び出し部分（_call_openai_api など）はテストでモック可能になっています（モジュール内関数を patch して差し替え）。
- DuckDB のインメモリ接続は `duckdb.connect(":memory:")` で可能。テスト用の軽量 DB として便利です。
- ロガーは各モジュールに分かれているので、テスト時は logging.basicConfig や個別 logger のレベル設定で出力を制御してください。

---

もし README に含めたい具体的なコマンド（CI/CD、起動スクリプト、systemd unit、Dockerfile 等）があれば、それに合わせた例を追加します。どの部分をより詳細に書くか（例: ETL の運用手順、Slack 通知の設定、kabuステーションとの接続方法）も指示ください。