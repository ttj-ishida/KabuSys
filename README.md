# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリ。J-Quants / RSS / OpenAI 等の外部データソースと連携し、ETL、ニュースセンチメント、ファクタ計算、監査ログなどの機能を提供します。

---

## プロジェクト概要

KabuSys は下記コンポーネントを備えたモジュール群です。

- データ収集・ETL（J-Quants API から株価・財務・マーケットカレンダーを取得）
- ニュース収集（RSS）と NLP による銘柄別センチメント算出（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースの融合）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ 等）
- データ品質チェック
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用のスキーマ管理
- ユーティリティ（マーケットカレンダー管理、統計関数等）

設計上の主な方針：
- ルックアヘッドバイアスを防ぐために内部で `date.today()` 等を不用意に参照しない
- DuckDB を主な内部 DB に利用し、ETL は冪等に実行される
- 外部 API 呼び出しはリトライやレートリミット制御あり
- OpenAI 呼び出しは JSON mode を想定し、失敗時はフェイルセーフで継続

---

## 機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得、バックフィル、品質チェック）
  - J-Quants クライアント（認証・ページネーション・保存）
- ニュース
  - RSS 取得（SSRF対策、追跡パラメータ除去）
  - news_nlp.score_news: 銘柄ごとに OpenAI でセンチメント評価して ai_scores に保存
- AI
  - ai.regime_detector.score_regime: ETF（1321）200日MA乖離とマクロニュースで市場レジーム判定
- Research
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- Data utilities
  - calendar_management: 営業日判定・次/前営業日検索・カレンダー更新ジョブ
  - quality: 欠損・スパイク・重複・日付不整合チェック
- Audit
  - init_audit_schema / init_audit_db：監査ログ用スキーマ初期化
- 設定管理
  - kabusys.config.Settings：.env または OS 環境変数から設定を読み込む（自動ロードあり。無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

---

## セットアップ手順

前提
- Python 3.10+（型ヒントや | Union 構文を使用）
- DuckDB、OpenAI SDK、defusedxml 等を利用します

1. リポジトリをチェックアウト（省略）

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに setup.cfg / pyproject.toml があれば pip install -e . を利用してください）

4. 環境変数 (.env) の準備
   プロジェクトルートに `.env` または `.env.local` を置くと自動でロードされます（自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（実行・発注連携用）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack のチャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector で使用）

   オプション / 設定
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: モニタリング用 SQLite（デフォルト data/monitoring.db）
   - PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL またはスクリプトから呼び出す際の例です。

共通: DuckDB 接続を作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行（例: 今日分を取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュースセンチメントを算出して ai_scores に保存
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI APIキーは環境変数 OPENAI_API_KEY、または api_key 引数で指定可能
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {written} codes")
```

3) 市場レジームをスコアリングして market_regime に書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB を初期化（監査専用 DB を別ファイルで作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以後 audit_conn を使って監査テーブルへ書き込み/参照が可能
```

5) 研究用ファクター計算の実行例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの dict のリスト
```

注意点:
- OpenAI 呼び出しや外部 API はネットワーク接続を要します。テスト時は該当内部関数を mock できます（コード中にパッチしやすい箇所が設計されています）。
- run_daily_etl は内部で market_calendar を先に更新して営業日に調整します。

---

## ディレクトリ構成（主なファイル・モジュール）

src/kabusys/
- __init__.py: パッケージメタ情報
- config.py: 環境変数・設定読み込みロジック（.env 自動読み込み、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py: ニュースのセンチメント解析（OpenAI 経由、ai_scores 書き込み）
  - regime_detector.py: 市場レジーム判定（ETF MA とマクロニュースの融合）
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（認証・取得・保存）
  - pipeline.py: ETL パイプラインの実装（run_daily_etl 等）
  - etl.py: ETL の公開インターフェース（ETLResult 再エクスポート）
  - calendar_management.py: マーケットカレンダー管理（営業日判定、更新ジョブ）
  - news_collector.py: RSS 取得と raw_news への保存ロジック（SSRF対策等）
  - stats.py: 統計ユーティリティ（zscore_normalize 等）
  - quality.py: データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - audit.py: 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー、rank 等
- monitoring, strategy, execution など（パッケージ __all__ に含まれるがコードベースでは補助モジュールがあり得ます）

各モジュールはドキュメント文字列で設計意図・処理フロー・フェイルセーフの振る舞いが詳細に記述されています。

---

## 開発・テスト上の留意点

- OpenAI の呼び出しは内部でリトライ／フェイルセーフが実装されていますが、ユニットテストでは HTTP 呼び出しをモックしてください（コード内にパッチしやすい関数が分離されています）。
- DuckDB の executemany に関する互換性（空リスト不可等）への対策が実装されていますが、テスト環境のバージョン差分に注意してください。
- 設定は .env と OS 環境変数の優先順位（OS > .env.local > .env）で読み込まれます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし README に追加したい具体的なコマンド（systemd サービス定義、cron ジョブ例、CI 設定、.env.example の完全なテンプレート等）があれば教えてください。必要に応じて追記します。