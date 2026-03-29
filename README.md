# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ KabuSys の README です。  
このリポジトリはデータ取得（ETL）、品質チェック、ニュースNLP、レジーム判定、リサーチ（ファクター計算）、監査ログ（オーダー／約定トレース）などのコンポーネントを備えたモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・カレンダーデータの差分取得・保存（DuckDB ベース）
- RSS ニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini を想定）を用いたニュースセンチメント（銘柄別）およびマクロセンチメントの評価
- ETF（1321）200日移動平均乖離とマクロセンチメントを統合した市場レジーム判定
- ファクター計算（Momentum / Volatility / Value 等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査用スキーマ（signal → order_request → executions）の初期化／管理

設計上の特徴：
- ルックアヘッドバイアス対策（関数内で date.today()/datetime.today() を不用意に参照しない）
- DuckDB を中心としたローカル DB 保持、冪等（ON CONFLICT）での保存
- API 呼び出しはリトライ・バックオフ・レート制御を実装
- フェイルセーフ：外部 API 失敗時は可能な範囲で継続（例：LLM が使えない場合は 0 スコアにフォールバック）

---

## 主な機能一覧

- data.jquants_client: J-Quants からのデータ取得／保存（daily_quotes, financial_statements, market_calendar, listed_info）
- data.pipeline: 日次 ETL パイプライン（run_daily_etl）と個別 ETL ジョブ
- data.quality: データ品質チェック（欠損/スパイク/重複/日付不整合）
- data.calendar_management: 市場カレンダー操作（営業日判定、next/prev_trading_day 等）
- data.news_collector: RSS フィード収集と前処理、raw_news への保存
- data.audit: 監査ログ用テーブルの初期化（signal_events / order_requests / executions）
- ai.news_nlp: ニュースを銘柄別に統合して LLM に投げ、ai_scores を更新する（score_news）
- ai.regime_detector: ETF 1321 の MA200 乖離とマクロセンチメントを合成し market_regime に書き込む（score_regime）
- research: ファクター計算（momentum / volatility / value）や将来リターン、IC 計算、統計サマリー
- data.stats: Zスコア正規化などの統計ユーティリティ

---

## セットアップ手順（ローカル開発向け）

前提：
- Python 3.9+（型ヒントでは 3.10 様式の Union | を使用していますが、3.9 でも typing の backport があれば可）
- ネットワーク接続（J-Quants / OpenAI / RSS）

1. リポジトリをクローン
   - git clone ... 

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（最低限）
   - pip install duckdb openai defusedxml

   注: プロジェクトに requirements.txt がある場合はそちらを使用してください。

4. 環境変数（または .env ファイル）を用意
   KabuSys は起動時にプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（CWD に依存しません）。
   自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト等で使用）。

   主な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai.* の機能で必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（売買連携時）
   - KABU_API_BASE_URL: kabu API ベース URL（既定: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（通知等で使用）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（既定: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（既定: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）

   例（.env の一部）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB の初期化（監査ログ用 DB の例）
   - Python から初期化:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   または、既存 conn を作ってスキーマだけ適用:
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)

---

## 使い方（簡易サンプル）

以下は Python スクリプトや REPL から呼ぶ基本例です。

1) ETL（日次パイプライン）を実行する
```
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

2) ニューススコアリングを実行（OpenAI API キーが必要）
```
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20))
print("書込件数:", n_written)
```

3) 市場レジーム判定を実行
```
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

4) 監査スキーマを初期化（既存のデータベースに監査テーブルを追加）
```
import duckdb
from kabusys.data.audit import init_audit_schema

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

5) 研究用ユーティリティ（ファクター計算）
```
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# z-score 正規化など
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m","mom_3m","mom_6m","ma200_dev"])
```

---

## よくある設定・運用注意

- OpenAI 呼び出しはレートや費用がかかるため、API キーとコール頻度を運用で管理してください。AI 関連処理はフェイルセーフ設計（API失敗時は 0 スコアへフォールバック）です。
- J-Quants API はレート制限があるためモジュール内で固定間隔のレートリミッティングをしてあります。大量の連続要求は避けてください。
- データベースファイル（DuckDB）は単一ファイルでローカル運用が可能ですが、バックアップやローテーションを計画してください。
- テスト実行時に自動 env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                           -- 環境変数 / 設定の読み込みと検証
- ai/
  - __init__.py
  - news_nlp.py                        -- ニュースの LLM スコアリング（score_news）
  - regime_detector.py                 -- マクロ + MA200 でレジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                  -- J-Quants API クライアント（fetch/save）
  - pipeline.py                        -- ETL パイプライン（run_daily_etl 他）
  - etl.py                             -- ETLResult の再エクスポート
  - news_collector.py                  -- RSS ニュース収集・前処理
  - quality.py                         -- データ品質チェック
  - calendar_management.py             -- 市場カレンダー管理（営業日判定 等）
  - stats.py                           -- zscore_normalize 等統計ユーティリティ
  - audit.py                           -- 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py                 -- Momentum/Volatility/Value の計算
  - feature_exploration.py             -- 将来リターン / IC / rank / summary
- monitoring/ (未表示ファイルがある可能性あり)
- strategy/ (戦略層のコード（ここでは省略））
- execution/ (発注実装（ここでは省略））

（上記は主要モジュールと担当機能の一覧です。実際のファイル一覧はリポジトリのルートを参照してください。）

---

## 開発・拡張のヒント

- テスト時に OpenAI の呼び出しをモックするために、ai 内部の _call_openai_api をパッチする想定で設計されています（unittest.mock.patch 等）。
- DuckDB による SQL 実行はパラメータバインド（?）を基本にしているため、SQL インジェクション面で安全です。
- 新しい ETL ステップや保存テーブルを追加する場合は、既存の ON CONFLICT 戦略に倣って冪等性を確保してください。
- ローカルの kabuステーション（kabu API）へ接続する際は KABU_API_BASE_URL / KABU_API_PASSWORD を設定してください。

---

## サポート / 問い合わせ

不具合や改善提案があれば issue を作成してください。ドキュメント不足や API 仕様に関する質問は README を更新の上で対応します。

---

README の内容はリポジトリ内コードの説明に基づいてまとめています。より詳細な API や運用手順は各モジュールの docstring を参照してください。