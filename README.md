# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
本リポジトリはデータのETL、ニュースの収集・NLPスコアリング、リサーチ（ファクター計算）、
市場レジーム判定、監査ログ（発注/約定のトレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要なAPI例）
- 環境変数
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けのデータプラットフォームおよび自動売買支援ライブラリ群です。
- J-Quants API を用いた株価・財務・市場カレンダーの差分ETL、RSSベースのニュース収集、
  OpenAI（gpt-4o-mini）を利用したニュースセンチメント/市場レジーム判定、
  DuckDB を利用したデータ保存・監査ログ等の機能を持ちます。
- バックテストや運用で生じやすい「ルックアヘッドバイアス」を避ける設計が各モジュールに組み込まれています。

主な機能一覧
- 環境変数管理
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可）
  - settings オブジェクトから型付きプロパティで取得
- データ取得・ETL
  - J-Quants API クライアント（認証、自動リフレッシュ、レート制御、リトライ）
  - 日次ETL run_daily_etl（市場カレンダー・株価・財務の差分取得／保存）
  - 個別ETL: run_prices_etl, run_financials_etl, run_calendar_etl
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集
  - RSS 取得（SSRF対策、gzip対応、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存の想定
- ニュースNLP / レジーム判定（OpenAI）
  - 銘柄毎のニュースをまとめて gpt-4o-mini に投げ、ai_scores を生成する score_news
  - マクロニュース + ETF(1321) の200日MA乖離を合成して市場レジーム（bull/neutral/bear）を判定する score_regime
  - API呼び出しのリトライ・フェイルセーフ設計（失敗時は中立スコアにフォールバック）
- リサーチ（ファクター計算）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDBベース）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ機能
- 監査ログ（Audit）
  - signal_events, order_requests, executions 等の監査テーブル定義と初期化（冪等）
  - init_audit_db で監査用 DuckDB を初期化
- ユーティリティ
  - 統計ユーティリティ（zscore 正規化等）
  - 市場カレンダーの一貫した営業日判定ロジック

---

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. Python 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要な依存をインストール  
   （プロジェクトに requirements.txt がない場合は下記を参考にインストールしてください）
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 主要依存: duckdb, openai, defusedxml
   - 標準ライブラリに存在する urllib 等は追加不要

4. 環境変数（.env）を用意  
   プロジェクトルートに .env（または .env.local）を配置すると自動読み込みされます。
   自動ロードを無効化したいときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot Token（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネルID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出し時に必要）
- 任意・デフォルトあり:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

使い方（主要API例）
- 共通: DuckDB 接続を作成して関数に渡すスタイルを採用しています。

1) ETL 実行（日次）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのスコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定済みの場合は api_key=None でOK
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", count)
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査DB初期化（発注/約定ログ用）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセスできます
```

5) リサーチ: モメンタム計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の dict のリスト
```

注意点
- OpenAI API を利用する関数は api_key 引数で明示的にキー注入可能（テスト容易化）。
- ルックアヘッドバイアス防止のため、各関数は内部で date.today() 等を乱用しない設計です。必ず target_date を明示するか、意図を理解して使用してください。
- J-Quants へのリクエストはレート制御やリトライロジックを備えています。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / settings
  - ai/
    - __init__.py
    - news_nlp.py                -- ニュースセンチメント取得（score_news）
    - regime_detector.py         -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py                -- ETL パイプライン（run_daily_etl など）
    - etl.py                     -- ETL インターフェース（ETLResult）
    - news_collector.py          -- RSS 収集・前処理
    - calendar_management.py     -- 市場カレンダー操作・更新ジョブ
    - quality.py                 -- データ品質チェック
    - stats.py                   -- 汎用統計ユーティリティ（zscore）
    - audit.py                   -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         -- ファクター計算（momentum, value, volatility）
    - feature_exploration.py     -- 将来リターン / IC / 統計サマリ
  - monitoring/ (想定)           -- 監視用モジュール（PID/リソース閾値等） ※コードベースに準拠
  - execution/ (想定)            -- 発注・ブローカー連携モジュール（将来実装想定）
  - strategy/ (想定)             -- 戦略定義・シグナル生成モジュール（将来実装想定）

（注）実際のリポジトリに含まれるファイルは上記の一覧と一致します。部分的に未実装/想定のディレクトリもあります。

---

運用上の補足
- 自動環境変数読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動ロードします。
  - テスト時や明示的に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギング / 環境
  - settings.log_level でログレベルを制御します。KABUSYS_ENV により挙動（paper_trading / live）を分けられます。
- 安全対策
  - news_collector は SSRF/プライベートホスト接続防止、XML/大容量応答対策などを実装しています。
  - API呼び出しはレート制御・リトライ・トークン自動更新等の堅牢化を行っています。

---

問題点・注意（開発者向け）
- ドキュメント内で参照されているテーブル（raw_prices, raw_news, ai_scores, market_calendar, raw_financials, etc.）はスキーマ定義が別途必要です。ETL/監査初期化関数を使って適切にテーブルを作成してください。
- OpenAI SDK のバージョンにより例外クラス名やレスポンス形状が異なる可能性があります。テストにて動作を確認してください。

---

貢献
- バグ報告・機能要望は Issue を作成してください。プルリクは歓迎します。
- コードスタイルやテストを整備のうえで PR を送ってください。

---

ライセンス
- 本プロジェクトのライセンス情報はリポジトリルートの LICENSE を参照してください（未設定の場合は管理者へ問い合わせてください）。

---

README は以上です。必要であれば、各モジュールごとの詳細な使用例やテーブルスキーマ（DDL）、requirements.txt のテンプレート、または運用手順（cron / systemd の例）を追記します。どのトピックを詳しく追加しますか？