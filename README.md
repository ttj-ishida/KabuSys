# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
ETL、ニュース収集・NLP、ファクター研究、監査ログ、マーケットカレンダー管理などを含み、バックテストや実運用の基盤として利用できます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 要件 / 依存関係
- セットアップ手順
- 環境変数（.env）例
- 使い方（主要ユースケースとサンプル）
- ディレクトリ構成（主要ファイル説明）
- 注意点 / 設計方針のハイライト

---

プロジェクト概要
- KabuSys は J-Quants や各種 RSS / OpenAI を用いて日本株のデータ収集、品質検査、ニュースによる AI スコアリング、ファクター計算、監査ログ管理までをカバーするモジュール群です。
- バックテストや運用システムのデータ基盤（DuckDB を主データストアに想定）および監査・トレーサビリティ機能を提供します。
- Look-ahead バイアス回避やフェイルセーフ設計（API失敗時のフォールバック）などを念頭に実装されています。

主な機能
- ETL（J-Quants）:
  - 株価日足、財務データ、JPXカレンダーの差分取得・保存（ページネーション対応・冪等保存）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック:
  - 欠損、スパイク、重複、日付整合性チェック（quality.run_all_checks）
- ニュース収集:
  - RSS 取得、安全対策（SSRF対策・受信サイズ制限）・前処理・raw_news テーブルへの冪等保存
- ニュース NLP（OpenAI）:
  - 銘柄単位のニュースセンチメントスコアリング（ai.score_news）
  - マクロニュースを元にした市場レジーム判定（ai.score_regime）
  - JSON Mode / リトライ・バックオフ実装
- 研究（research）:
  - Momentum / Value / Volatility 等のファクター計算（DuckDB 上で SQL/Python）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- 監査ログ（audit）:
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - init_audit_schema / init_audit_db による冪等初期化
- ユーティリティ:
  - 統計ユーティリティ（zscore_normalize）、カレンダー管理（営業日判定）など

要件 / 依存関係
- Python 3.10+（typing の | 型合併などを使用）
- 主な依存パッケージ:
  - duckdb
  - openai (OpenAI Python SDK、Chat/Completions API を利用する想定)
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging など）

セットアップ手順（開発環境想定）
1. リポジトリをクローン
   - git clone <リポジトリ URL>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)
3. 必要パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - またはプロジェクトが pip 用ファイルを持つ場合: pip install -e .
4. .env を用意（下記参照）
5. DuckDB データベース用ディレクトリを用意（設定例では data/）

環境変数（.env）例
- プロジェクトは .env または OS 環境変数から設定を読み込みます。プロジェクトルートに .env を置くか、環境変数を設定してください。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 代表的な変数:

  - JQUANTS_REFRESH_TOKEN=あなたの_jquants_リフレッシュトークン  (必須)
  - OPENAI_API_KEY=あなたのOpenAI APIキー  (ai.score_news / score_regime 実行時に使用)
  - KABU_API_PASSWORD=kabuステーションAPIパスワード（発注等で必要）
  - SLACK_BOT_TOKEN=Slack 通知用 Bot Token（任意だが設定されている箇所あり）
  - SLACK_CHANNEL_ID=Slack チャンネルID
  - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
  - SQLITE_PATH=data/monitoring.db
  - KABUSYS_ENV=development|paper_trading|live  (デフォルト development)
  - LOG_LEVEL=INFO (DEBUG/INFO/WARNING/ERROR/CRITICAL)

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

主な使い方（コード例）
- DuckDB 接続の作成、日次 ETL 実行
```
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（score_news）
```
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を使用
print(f"written: {written}")
```

- 市場レジーム判定（score_regime）
```
from kabusys.ai.regime_detector import score_regime
# conn は DuckDB 接続、target_date は判定日
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB の初期化
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# または既存 conn に対して init_audit_schema(conn)
```

- ファクター計算（研究用途）
```
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
res = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(res, columns=["mom_1m","mom_3m","ma200_dev"])
```

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — 環境変数 / 設定管理（.env 自動読込・settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し、チャンク処理、DB への書込）
    - regime_detector.py — 市場レジーム判定（ETF 1321 の MA とマクロセンチメントを合成）
  - data/
    - __init__.py
    - pipeline.py — ETL のメイン機能（run_daily_etl など）
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py — RSS 収集・前処理・保存
    - quality.py — データ品質チェック
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - calendar_management.py — JPX カレンダー管理 / 営業日判定 / calendar_update_job
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
    - etl.py — ETLResult の公開
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai and research モジュールは OpenAI や DuckDB を前提に設計されています。

注意点 / 設計方針のハイライト
- Look-ahead バイアス回避:
  - 内部実装は target_date より未来のデータ参照を避ける設計（例: date < target_date 等）
  - datetime.today() / date.today() 参照を回避する場所が多い（ユニットテストと再現性に配慮）
- フェイルセーフ:
  - OpenAI / API 呼び出し失敗時はスコアを 0.0 にフォールバックしたり、処理を部分的にスキップして継続する実装
- 冪等性:
  - J-Quants の保存系は ON CONFLICT DO UPDATE を使用して冪等にデータを更新
  - news_collector は正規化 URL のハッシュで記事 ID を生成し冪等性を確保
- セキュリティ:
  - RSS 取得で SSRF 対策（リダイレクト検査、プライベートアドレス排除）
  - defusedxml による XML パース防御
- リトライ / バックオフ:
  - API 呼び出し（OpenAI, J-Quants）に対してリトライ、指数バックオフ、429/5xx の取り扱いあり

運用・デプロイ上の備考
- 運用（paper_trading / live）で実際に発注するモジュールは別にあり、KabuSys の一部は研究/データ側に重点を置いています。KABUSYS_ENV を設定し、is_live/is_paper 判定をコードから利用できます。
- ログレベルは LOG_LEVEL で制御します。運用時は INFO か WARNING、開発時は DEBUG を推奨します。
- OpenAI の利用は課金対象です。バッチサイズやモデル（gpt-4o-mini）を設定で注意してください。

---

質問・追加ドキュメントの希望
- 使い方のサンプル（ETL スケジュール、Docker 化、CI テスト例）、または各テーブルのスキーマ一覧が必要なら作成します。どの項目を優先して欲しいか教えてください。