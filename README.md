# KabuSys

KabuSys は日本株向けのデータプラットフォームおよび自動売買（リサーチ/戦略/実行）ユーティリティ群です。J-Quants や RSS、OpenAI を組み合わせてデータ取得・品質チェック・特徴量計算・ニュース NLP・市場レジーム判定・監査ログなどを提供します。

主な設計方針：
- Look‑ahead bias を避ける（関数内部で datetime.today() 等を不用意に参照しない）
- DuckDB を中心に冪等（idempotent）で ETL を実行
- 外部 API 呼び出しはリトライ／レートリミット制御を備える
- 品質チェック・監査ログによる安全性とトレーサビリティ確保

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - 必須環境変数の取得ユーティリティ

- データ収集・ETL（kabusys.data）
  - J-Quants API クライアント（株価、財務、マーケットカレンダー等）
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - マーケットカレンダー管理（営業日判定、next/prev trading day 等）
  - 監査ログスキーマ初期化・専用 DB 初期化

- AI / NLP（kabusys.ai）
  - ニュースの銘柄別センチメント分析（score_news）
  - マクロニュースと ETF の MA200 を用いた市場レジーム判定（score_regime）

- リサーチ（kabusys.research）
  - ファクター計算（Momentum / Value / Volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化ユーティリティ

- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize 等

---

## セットアップ手順

前提：
- Python 3.10 以上推奨（typing の新しい構文や型ヒントを利用）
- DuckDB（Python パッケージ）を利用
- 外部 API を使う場合はネットワーク接続と各種 API キーが必要

推奨インストール手順（プロジェクトルートで実行）:

1. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   （プロジェクトに requirements ファイルがある場合はそちらを利用。なければ最低限以下をインストールしてください）
   ```bash
   pip install duckdb openai defusedxml
   ```

   - openai: OpenAI API を利用する場合
   - defusedxml: RSS パーサの安全対策
   - 追加: （必要に応じて）slack SDK など

3. 環境変数の設定
   プロジェクトルートに `.env`（または `.env.local`）を配置することで自動読み込みされます。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

必須（利用する機能に応じて）環境変数：
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 実行時）
- OPENAI_API_KEY : OpenAI（news_nlp / regime_detector を利用する場合）
- KABU_API_PASSWORD : kabuステーション API のパスワード（注文実行機能と連携する場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : 監視通知等で Slack を使う場合
- 省略可 / デフォルトあり:
  - KABUSYS_ENV : development | paper_trading | live（デフォルト development）
  - LOG_LEVEL : ログレベル（デフォルト INFO）
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 sqlite（デフォルト data/monitoring.db）
  - PID_FILE_PATH : 実行監視用 PID ファイルパス（デフォルト data/execution.pid）

例 .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（主要な関数・ワークフロー例）

以下は Python REPL もしくはスクリプトでの利用例です。DuckDB 接続を作り、ETL や AI スコアリング、リサーチ関数を呼びます。

- DuckDB 接続の作成例
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー、株価、財務、品質チェックを順に実行）
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しない場合は今日（注意: 実運用では明示的に指定すること推奨）
result = run_daily_etl(conn, target_date=None)
print(result.to_dict())
```

- ニュース NLP（銘柄別センチメント）を実行
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date を指定（例: 2026-03-20）
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written ai_scores count: {n_written}")
```

- 市場レジーム判定を実行
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 03, 20))
```

- ファクター計算例（Momentum / Volatility / Value）
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
# 取得したリストを分析・保存して利用
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path
from kabusys.config import settings

db_path = settings.duckdb_path  # あるいは別ファイルを指定
audit_conn = init_audit_db(db_path)
```

注意点：
- OpenAI を呼ぶ機能（score_news, score_regime）は OPENAI_API_KEY が必要です。
- J-Quants を呼ぶ ETL は JQUANTS_REFRESH_TOKEN を要求します。
- 関数群は Look‑ahead バイアスに配慮して実装されていますが、バックテスト等で使う場合は取得済みデータを適切に制御してください（外部 API 呼出しをテスト内で直接回すことは避ける）。

---

## ディレクトリ構成（主要ファイルと説明）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄別に集約して OpenAI へ問い合わせ、ai_scores テーブルに書き込む
    - regime_detector.py
      - ETF(1321) の MA200 とマクロニュースの LLM センチメントを合成して market_regime テーブルに保存
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save 系、rate limit / retry / token refresh）
    - pipeline.py
      - run_daily_etl など ETL パイプラインとヘルパー
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 収集、前処理、raw_news 保存
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付整合）
    - calendar_management.py
      - market_calendar の管理 / 営業日判定 / calendar_update_job
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログテーブル DDL と初期化関数
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / バリュー / ボラティリティ等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、rank、統計サマリー

---

## 開発・運用のヒント

- .env と .env.local の自動読み込み
  - 読み込み優先順: OS 環境変数 > .env.local > .env
  - テスト時に自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

- 安全性
  - news_collector は SSRF や XML インジェクションに対する複数の防御（スキーム検証、プライベートホスト検査、defusedxml、サイズ上限）を実装しています
  - OpenAI 呼び出しは JSON モードのレスポンスを期待しつつ不備へフォールバックする実装（失敗時は 0.0 などで継続）

- ログ
  - settings.log_level でログレベル制御可能
  - 各モジュールは logger を使用して進捗・エラーを出力

- テスト
  - 外部 API 呼び出し（OpenAI, J-Quants, HTTP）部分はモックで差し替えてユニットテストを実施してください（コード中に差し替え用の内部関数設計あり）

---

もし README に含めたい追加の情報（CI、ライセンス、具体的な設定例、運用手順、docker-compose 用構成など）があれば教えてください。必要に応じてサンプル .env.example や簡易運用手順（cron / systemd の例）も作成します。