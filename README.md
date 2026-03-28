# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
J-Quants からの市場データ取得（ETL）、ニュース収集・NLP、ファクター計算、監査ログ（トレーサビリティ）など、アルゴリズム取引・リサーチに必要なユーティリティ群を提供します。

主な設計方針：
- Look-ahead バイアスに配慮した日付扱い（内部で date.today() を不用意に参照しない実装）
- DuckDB をデータ層に採用し、SQL と Python を組み合わせた処理
- 外部 API 呼び出しはリトライ / フェイルセーフを備え、部分失敗時も処理継続
- 冪等（idempotent）設計（DB 保存は ON CONFLICT で上書き等）

---

## 機能一覧

- データ取得・ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダー等を差分取得・保存（pagination・リトライ・レート制御対応）
  - 日次 ETL パイプライン（run_daily_etl）を提供
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合を検出するチェック群
- ニュース収集
  - RSS フィードから記事を収集して正規化・保存（SSRF 対策・トラッキングパラメータ除去等）
- ニュース NLP（OpenAI）
  - 銘柄ごと・時間ウィンドウ単位でニュースをまとめ、LLM（gpt-4o-mini）でセンチメントスコアを生成（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
- リサーチ / ファクター処理
  - モメンタム、バリュー、ボラティリティ等のファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等
- 監査ログ（Audit）
  - シグナル → 発注 → 約定までを UUID で追跡する監査用スキーマの初期化・管理（init_audit_schema / init_audit_db）
- 設定管理
  - .env/.env.local または環境変数から設定を自動読み込み（パッケージ起動時にプロジェクトルートを探索して読み込み）

---

## 必要条件（推奨）

- Python 3.10+
- DuckDB
- OpenAI Python SDK
- defusedxml
- （ネットワーク接続、J-Quants API アクセス、OpenAI API アクセス）

例: 必要パッケージ（実際の requirements.txt を参照してください）
- duckdb
- openai
- defusedxml

---

## インストール

ローカル開発でセットアップする最小例：

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

3. パッケージを開発モードでインストール（ルートに setup.cfg / pyproject.toml がある想定）
   - pip install -e .

※ 実プロジェクトでは requirements.txt / pyproject.toml を用意して依存解決してください。

---

## 設定（環境変数 / .env）

パッケージは起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、以下の優先順位で環境変数を読み込みます：
1. OS 環境変数
2. .env.local（存在すれば上書き）
3. .env

自動読み込みを無効化する場合：
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション等のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector の呼び出しで利用）

.env の例（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（クイックスタート）

以下は Python REPL / スクリプト内で利用する例です。DuckDB 接続は kabusys が想定する DuckDB 接続オブジェクト（duckdb.connect(...））を渡します。

1) 日次 ETL を実行する
```py
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントスコアを作成（OpenAI API キーは環境変数か引数で指定）
```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（ETF 1321 の MA とマクロニュースを組み合わせる）
```py
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
status = score_regime(conn, target_date=date(2026, 3, 20))
print("OK" if status == 1 else "Failed")
```

4) 監査ログ DB を初期化する
```py
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使用して order_requests / executions 等の監査テーブルが作成されます
```

注意点 / 備考:
- OpenAI 呼び出しは外部 API を使用するため API キーと通信環境が必要です。API 呼び出しはリトライ・フェイルセーフを実装していますが、コストやレート制限には注意してください。
- ETL / ニュース収集はネットワークアクセス・認証を伴います。運用環境ではシークレット管理・監査ログ保存方針に従ってください。

---

## ディレクトリ構成（主要ファイル）

以下はこのコードベースで提供されている主要モジュールの概要です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news: ニュースを LLM でスコア化して ai_scores に書き込み
    - regime_detector.py
      - score_regime: MA とマクロセンチメントを合成して market_regime に書き込み
  - data/
    - __init__.py
    - calendar_management.py
      - 市場カレンダーの判定・更新ロジック（is_trading_day, next_trading_day, ...）
    - etl.py
      - ETLResult の公開（再エクスポート）
    - pipeline.py
      - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログスキーマ定義・初期化（signal_events / order_requests / executions）
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
    - news_collector.py
      - RSS 取得・前処理・保存（SSRF 対策・トラッキング除去）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - research/ 他の補助モジュール...
  - その他（strategy / execution / monitoring などのパッケージ名が __all__ に含まれています）

---

## 開発・テストに関するメモ

- 自動環境変数読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテストで .env の自動ロードを避ける際に有用）。
- OpenAI / J-Quants 呼び出し部は内部で独自の _call_openai_api / _request を持ち、テスト時はモック差し替えが想定されています（unittest.mock.patch を使用）。

---

## ライセンス・貢献

本 README ではライセンスや貢献フローの記載はしていません。実運用での利用や公開を行う場合は適切な LICENSE ファイルと貢献ガイドラインを追加してください。

---

必要なら、この README をベースに「環境変数の完全な .env.example」や「デプロイ／cron ジョブの例」「監視・アラート設定例」などの追加ドキュメントも作成します。どの章を詳細化したいか教えてください。