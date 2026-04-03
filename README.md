# KabuSys

KabuSys は日本株向けのデータプラットフォーム & 自動売買支援ライブラリです。J-Quants API / RSS / OpenAI（LLM）を利用してデータ取得・品質チェック・特徴量計算・ニュースセンチメント評価・市場レジーム判定・監査ログの初期化などを行うユーティリティ群を提供します。

主に DuckDB をデータ層に用い、ETL パイプラインや研究用途（factor/research）と自動売買実行フロー（監査／発注管理）で使えるモジュールを含みます。

---

## 主な機能

- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存（ページネーション・レート制御・自動リフレッシュ）
- ETL パイプライン
  - run_daily_etl による日次 ETL（カレンダー→株価→財務→品質チェック）
- データ品質チェック
  - 欠損、スパイク（前日比）、重複、日付不整合を検出（QualityIssue を返す）
- ニュース収集 / 前処理
  - RSS 取得、URL 正規化、SSRF 対策、記事テキストの前処理、raw_news 保存補助
- LLM を用いた NLP
  - ニュースごとの銘柄センチメント（score_news）
  - マクロセンチメント + ETF MA200 による市場レジーム判定（score_regime）
  - OpenAI リトライ/バックオフ制御を備えた実装
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化（DuckDB）
  - 監査DB初期化ユーティリティ（init_audit_db）

---

## 要件（推奨）

- Python 3.10 以上（typing の表記に依存）
- DuckDB
- OpenAI Python SDK
- defusedxml
- （ネットワーク呼び出しを行うため）インターネット接続
- J-Quants API リフレッシュトークン、OpenAI API キー 等

依存パッケージの例（requirements.txt の参考）:
- duckdb
- openai
- defusedxml

（実プロジェクトでは pip のインストール要件を requirements.txt / pyproject.toml にまとめてください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt
4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
   - 必須の主要環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector で使用）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（発注周りで使用）
   - その他オプション:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB）など
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

例 (.env):
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=your_kabu_password
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

5. DuckDB ファイルの親ディレクトリが存在しない場合は作成されます。監査DB初期化関数が必要なディレクトリを自動作成します。

---

## 使い方（主要なユースケース）

以下は最小限の利用例です（import 例・関数呼び出し）。

共通: 設定読み取り・DuckDB 接続
```python
import duckdb
from kabusys.config import settings

# settings は環境変数から各種パス・トークンを取得します
db_path = settings.duckdb_path
conn = duckdb.connect(str(db_path))
```

日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメント（LLM）を計算して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定します
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written}")
```

市場レジーム判定（ETF 1321 MA200 + マクロセンチメント）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

監査ログ用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

カレンダー更新ジョブ（J-Quants から calendar を取得して保存）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

使用上の注意（ポイント）
- OpenAI 呼び出しはネットワーク不安定時やレート制限時にリトライ処理を実装していますが、APIキーは安全に管理してください。
- ETL / 解析関数はルックアヘッドバイアスを避ける設計になっています（内部で date.today() を用いない箇所が多い）。
- 自動で .env をプロジェクトルートから読み込む仕組みがあるため、テスト時などに自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なモジュール一覧（本コードベースの主要ファイル）です。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースセンチメント（LLM 呼び出し）
    - regime_detector.py               — 市場レジーム判定（ETF + LLM）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（取得 + 保存）
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETL 結果型再エクスポート（ETLResult）
    - quality.py                       — データ品質チェック
    - stats.py                         — 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py           — JPX カレンダー管理
    - news_collector.py                — RSS ニュース収集
    - audit.py                         — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py               — momentum/value/volatility 等
    - feature_exploration.py           — 将来リターン / IC / 統計サマリ
  - research/__init__.py
  - その他（strategy / execution / monitoring 等は __all__ に含まれるが本抜粋により省略）

（この README は提示されたコードベースの抜粋に基づいています。実際のリポジトリではさらにユーティリティ・CLI・テスト等のファイルが存在する場合があります。）

---

## 設計上の重要なポイント

- Look-ahead Bias 防止: 多くの関数は target_date に厳密に依存し、実行時点の現在時刻を無条件に参照しない設計です。バックテスト／研究用途での安全性を重視しています。
- 冪等性: J-Quants からの保存処理は ON CONFLICT DO UPDATE を使い冪等に実装されています。
- フェイルセーフ: LLM/API 呼び出しで失敗した場合は部分的にフォールバック（例: macro_sentiment=0.0）して処理を継続する設計が多く見られます。
- セキュリティ: RSS 収集で SSRF 対策、defusedxml を利用した XML パース、URL スキームチェックなどが実装されています。

---

## よくある質問 / トラブルシューティング

- .env が自動で読み込まれない
  - プロジェクトルートの判定は config._find_project_root() により __file__ の親階層で .git または pyproject.toml を探索します。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化し、os.environ を手動で設定してください。

- OpenAI / J-Quants の認証エラー
  - 環境変数名を確認（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY）。J-Quants はリフレッシュトークンから ID トークンを自動で取得します。

- DuckDB のファイルパス
  - settings.duckdb_path によりデフォルトは data/kabusys.duckdb。パスは expanduser を使って展開されます。

---

必要に応じて README を拡張して、サンプル .env.example、requirements.txt、利用ワークフロー（ETL を Cron で回す例、監視の起動方法、戦略シグナル→発注フローなど）を追記できます。追加したい内容があれば指示してください。