# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、監査ログ（約定トレース）などを備えており、バッチ ETL や研究解析、戦略基盤の構築を目的としています。

バージョン: 0.1.0

---

## 主要機能

- データ取得 / ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分取得・バックフィル、ページネーション、トークン自動リフレッシュ、レートリミット管理
- データ品質管理
  - 欠損、スパイク（急変）、重複、日付整合性（未来日付・非営業日）チェック
- ニュース収集 / 前処理
  - RSS 収集、URL 正規化、SSRF 対策、トラッキングパラメータ除去、前処理、冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを集約して LLM（gpt-4o-mini）でセンチメント評価し ai_scores に保存
  - API リトライ、レスポンスバリデーション、スコアクリップなどの堅牢な実装
- 市場レジーム判定
  - ETF（1321）の 200 日移動平均乖離とマクロニュースセンチメントを合成し日次で bull/neutral/bear を判定
  - Look-ahead バイアス対策（対象日以前のデータのみ使用）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions など監査テーブルを初期化するユーティリティ（DuckDB）
  - order_request_id を冪等キーとして二重発注を防止
- 研究ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）、将来リターン、IC、Zスコア正規化 等

---

## セットアップ

前提:
- Python 3.10+（typing の union 表記や型ヒントを使用）
- システムに DuckDB が入ること（pip 経由で duckdb パッケージを導入）

推奨パッケージ（最低限、実行に必要なもの）:
- duckdb
- openai
- defusedxml

例（仮の requirements、実際の要件はプロジェクトの requirements.txt を参照してください）:
```
pip install duckdb openai defusedxml
```

パッケージとしてインストール（開発時）:
```
pip install -e .
```

環境変数:
- 自動でプロジェクトルートの `.env` / `.env.local` が読み込まれます（ただしテスト等で無効化可能）。
  - 自動読み込み無効化:
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主要な環境変数:
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
  - OPENAI_API_KEY (LLM を使う機能で必要)
  - KABU_API_PASSWORD (kabu ステーション連携用)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知用)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用 DB、デフォルト: data/monitoring.db)
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（監視 / 実行管理用）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

.env の自動読み込み順序:
- OS 環境変数 > .env.local > .env

設定の取得は `kabusys.config.settings` を使用してください。

---

## 使い方（例）

以下は代表的な操作の例です（スクリプト内で実行する想定）。

1) 設定・DB 接続の準備:
```python
from kabusys.config import settings
import duckdb

# settings.duckdb_path は Path を返す（展開済み）
conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（J-Quants から株価 / 財務 / カレンダーを差分取得）:
```python
from kabusys.data.pipeline import run_daily_etl

# 実行日を指定するか None で今日
result = run_daily_etl(conn, target_date=None)
print(result.to_dict())
```

3) ニュースセンチメントをスコアリング（target_date のニュースウィンドウを対象）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定
written_count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written_count}")
```

4) 市場レジーム判定（例: target_date 日付のレジームを計算して保存）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env で参照
```

5) 監査ログスキーマを初期化／専用 DB を作る:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions 等のテーブルが作られる
```

6) 研究向けユーティリティの利用例（モメンタム計算）:
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list[dict] — date, code, mom_1m, mom_3m, mom_6m, ma200_dev
```

---

## 設計上の注意点 / 特記事項

- Look-ahead bias 対策:
  - AI スコアリングやレジーム判定は target_date の「当日データ」やそれ以降のデータを参照しないよう設計されています（バックテストでの公正性確保）。
- 冪等性:
  - ETL の保存関数（save_*）は ON CONFLICT DO UPDATE を用い冪等性を担保しています。
- リトライ / フォールトトレランス:
  - J-Quants クライアントや OpenAI 呼び出しではリトライ・指数バックオフやフェイルセーフ（API失敗時はスコアを 0 とする等）を備えています。
- レート制限:
  - J-Quants は 120 req/min を想定したレートリミッタを実装しています。
- セキュリティ / ネットワーク:
  - news_collector は SSRF 対策、XML パースの堅牢化（defusedxml）、レスポンスサイズ上限などを実装しています。
- テスト向け:
  - 自動 .env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - OpenAI の呼び出し部分は内部ラッパー関数をモックして差し替え可能です（ユニットテスト用フックあり）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを集約して OpenAI でセンチメントを計算、ai_scores に書き込む
    - regime_detector.py — ETF MA とニュースセンチメントを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB への保存）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETL 関連の公開インターフェース（ETLResult の再エクスポート）
    - calendar_management.py — 市場カレンダー管理、営業日判定、夜間バッチ更新ジョブ
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログスキーマ定義・初期化（signal/order/execution）
    - news_collector.py — RSS 収集・前処理・保存
    - (その他) pipeline / ETLResult 等
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラ / バリュー等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等

（上記は提供された主要モジュールの抜粋です）

---

## 貢献 / テスト

- 自動ロードされる環境変数の影響を避けたいテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI / 外部 API を使う部分はモック可能に設計されています（モジュール内の _call_openai_api 等を patch）。
- DuckDB を用いるため、単体テストでは ":memory:" を使ったインメモリ DB を活用できます（例: init_audit_db(":memory:")）。

---

問題や追加で README に含めたい内容（依存関係の正確な一覧、例のスクリプト、CLI の有無など）があれば教えてください。必要に応じて README を拡張します。