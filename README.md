# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査（トレーサビリティ）などを含むモジュール群を提供します。

## 目次
- プロジェクト概要
- 主な機能
- 必須要件・依存関係
- セットアップ手順
- 環境変数（.env）例
- 使い方（簡易コード例）
- ディレクトリ構成（主要ファイルと説明）
- 注意事項 / 設計方針メモ

---

## プロジェクト概要
KabuSys は日本株のデータ基盤と自動売買ワークフローを構成するためのライブラリセットです。  
主な目的は以下です。
- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ニュース収集と OpenAI による銘柄別センチメントスコア付与
- 市場レジーム判定（テクニカル + マクロニュース）
- 研究用ファクター計算 / 特徴量探索ユーティリティ
- 監査ログ用 DuckDB スキーマ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、ルックアヘッドバイアスを避けるために datetime.today()/date.today() を内部処理で不用意に参照しない等の配慮があります。

---

## 主な機能（抜粋）
- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・保存・品質チェック）
  - J-Quants クライアント（認証、ページネーション、レートリミッティング、リトライ）
- ニュース NLP:
  - RSS 取得、前処理、OpenAI によるセンチメント評価（バッチ処理、リトライ、レスポンス検証）
  - ai_scores テーブルへの書き込み処理
- 市場レジーム判定:
  - ETF (1321) の 200 日 MA 乖離 + マクロニュースセンチメント の合成による日次レジーム判定
- 研究用:
  - momentum / value / volatility などのファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Z スコア正規化
- データ品質:
  - 欠損、重複、スパイク（前日比）や日付整合性のチェック
- 監査（Audit）:
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - init_audit_db で監査用 DuckDB を作成・初期化

---

## 必須要件・依存関係
- Python 3.10+
- 必要なパッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで多くを実装しているため最小限の外部依存）
- ネットワーク接続（J-Quants API、RSS フィード、OpenAI）

（実プロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

2. パッケージのインストール
   - pip install duckdb openai defusedxml
   - 開発・配布形式に合わせて pip install -e . 等を行ってください（本リポジトリがパッケージ化されている前提）。

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（ただし CWD に依存せず、パッケージ内ファイル位置からプロジェクトルートを探索します）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB（データベース）ディレクトリの準備
   - デフォルトの DuckDB ファイルは `data/kabusys.duckdb`（settings.duckdb_path）です。必要に応じてディレクトリを作成してください（init 関数が親ディレクトリを自動作成する場合もあります）。

5. 監査 DB 初期化（任意）
   - 監査用 DB を作成・スキーマ初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 環境変数（.env）例
最低限必要なもの（用途別）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン

- kabuステーション API（約定等）
  - KABU_API_PASSWORD=...
  - KABU_API_BASE_URL=http://localhost:18080/kabusapi  （デフォルト）

- OpenAI / ニュース NLP
  - OPENAI_API_KEY=sk-...

- Slack（通知用）
  - SLACK_BOT_TOKEN=...
  - SLACK_CHANNEL_ID=...

- DB パス（省略可）
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db

- 実行環境モード
  - KABUSYS_ENV=development|paper_trading|live
  - LOG_LEVEL=INFO

注意: Settings クラスは未設定の必須キーで ValueError を投げます。

---

## 使い方（簡易コード例）

以下はそれぞれの主要ユースケースの最小例です。詳細は各モジュール関数の docstring を参照してください。

- DuckDB 接続を開く:
  from pathlib import Path
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する:
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 戻り値は ETLResult
  print(result.to_dict())

- ニュースのスコアリング（OpenAI 必須）:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026, 3, 19))
  print(f"scored {n} codes")

- 市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 19))

- ファクター計算（研究用）:
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  recs = calc_momentum(conn, target_date=date(2026,3,19))
  # z-score 正規化
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m"])

- 監査 DB 初期化（既述）:
  from kabusys.data.audit import init_audit_db
  aconn = init_audit_db("data/audit.duckdb")

- カレンダー操作ユーティリティ例:
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_open = is_trading_day(conn, date(2026,3,20))
  nxt = next_trading_day(conn, date(2026,3,20))

---

## ディレクトリ構成（主要ファイルと説明）
（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（.env 自動読み込みロジック、Settings）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約・OpenAI でのセンチメント評価・ai_scores への書き込み
    - regime_detector.py
      - ETF MA200 乖離 + マクロニュースセンチメントの合成で市場レジームを算出
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、レート制御、保存ロジック）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - etl.py
      - ETLResult のエクスポート
    - news_collector.py
      - RSS 取得・前処理・raw_news への格納ロジック
    - calendar_management.py
      - 市場カレンダー管理と営業日判定ユーティリティ
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal/order/execution）スキーマ定義と初期化
  - research/
    - __init__.py
    - factor_research.py
      - momentum/value/volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー
  - その他: strategy, execution, monitoring パッケージがエクスポート対象に含まれます（実装はこのスナップショットにより部分的に存在する可能性があります）。

---

## 注意事項 / 設計方針メモ
- Look-ahead バイアス回避:
  - 多くのモジュールで target_date 未満や window を明示的に扱い、内部で現在時刻を安易に参照しない設計。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants）の失敗時には可能な限りフォールバック（ゼロスコア等）して処理継続する実装が多い。重大な永続化エラーは例外として伝播。
- 冪等性:
  - ETL / 保存処理は ON CONFLICT（アップサート）や挿入前の PK チェックで再実行可能性を確保。
- セキュリティ:
  - news_collector では SSRF 対策、受信サイズ制限、defusedxml の使用など安全性を意識した実装。
- テスト性:
  - OpenAI / ネットワーク呼び出し箇所は外部関数（_call_openai_api など）をモックしやすい構造。

---

詳細な API 仕様や運用手順、CI/CD、デプロイ手順は別ドキュメント（StrategyModel.md / DataPlatform.md 等）に準拠してください。  
追加の README 内容や実運用向けの具体例（Docker Compose、systemd ジョブ、監視設定など）を作成したい場合は用途を教えてください。