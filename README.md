# KabuSys

日本株向けのデータプラットフォーム兼自動売買（リサーチ・ETL・AI 評価・監査）ライブラリです。  
本リポジトリは、J-Quants・RSS 等からのデータ取得、DuckDB ベースの永続化、AI（OpenAI）を用いたニュースセンチメント評価、ファクター計算・特徴量探索、監査ログスキーマなどを提供します。

主な設計方針
- ルックアヘッドバイアスの排除（内部で datetime.today()/date.today() を直接参照しない設計）
- DuckDB を中心としたローカルデータプラットフォーム（冪等保存）
- 外部 API 呼び出しはリトライやレート制御を備える（J-Quants / OpenAI）
- ETL と品質チェックを分離し、部分失敗に耐える構成

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易例）
- 環境変数
- ディレクトリ構成

---

プロジェクト概要
- データ収集（J-Quants、RSS）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース NLP（OpenAI を用いた銘柄別センチメント）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）

---

機能一覧（主要モジュール）
- kabusys.config
  - .env 自動読み込み（プロジェクトルートの .env / .env.local。無効化可）
  - settings による環境変数アクセス（必須キーを検証）
- kabusys.data.jquants_client
  - J-Quants API 呼び出し（トークンリフレッシュ、ページネーション、レート制御、保存処理）
  - save_* 系で DuckDB に冪等保存
- kabusys.data.pipeline
  - run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl：差分 ETL と品質チェック
  - ETLResult：実行結果の構造化
- kabusys.data.news_collector
  - RSS フィード取得・前処理・raw_news への保存（SSRF 対策、トラッキング除去）
- kabusys.data.quality
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返す）
- kabusys.data.audit
  - 監査ログテーブルの初期化（init_audit_schema / init_audit_db）
- kabusys.ai.news_nlp
  - 銘柄別ニュースを集約して OpenAI に送信し ai_scores に書き込む（score_news）
- kabusys.ai.regime_detector
  - ETF 1321 の MA200 とマクロニュースの LLM スコアを組合せて market_regime を判定（score_regime）
- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）

---

セットアップ手順（開発環境向け）
1. リポジトリを取得
   - git clone <repo_url>
   - プロジェクトルートに移動（pyproject.toml か .git が存在する場所）

2. Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - 必要最低限:
     pip install duckdb openai defusedxml
   - 実運用では追加の依存（slack_sdk など）やバージョン管理を行ってください。

4. パッケージを編集可能インストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数等については下の「環境変数」セクション参照。

6. DuckDB / 監査 DB 初期化（例）
   - Python スクリプト内で:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

注意: 実行環境によってはネットワーク接続や API キー（J-Quants / OpenAI）が必要です。

---

環境変数（主要項目）
- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD (必須)  
  kabu ステーション API のパスワード
- KABU_API_BASE_URL (任意)  
  デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須)  
  Slack 通知用
- OPENAI_API_KEY (必須 for AI 機能)  
  news_nlp / regime_detector が OpenAI にアクセスする際に参照
- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)  
  デフォルト: data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT  
  監視関連の設定
- KABUSYS_ENV (任意)  
  値: development | paper_trading | live（デフォルト development）
- LOG_LEVEL (任意)  
  DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

.env 自動ロードの挙動:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env を読み込み、続いて .env.local を上書き読み込みします。
- OS 環境変数は上書きされません（.env.local の override は OS 環境変数を保護）。
- テスト等で自動読み込みを抑止する場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 (.env.example)
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

機密情報（API トークン等）はバージョン管理に含めないでください。

---

使い方（簡単なコード例）

準備: DuckDB 接続を取得（settings で DUCKDB_PATH を参照）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

ETL を日次で実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースの AI スコア付け（score_news）
- OPENAI_API_KEY が環境変数にセットされていることを確認してください
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written_scores={written}")
```

市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

監査 DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または既存コネクションにテーブル追加:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

J-Quants から株価を取得して保存する（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
saved = save_daily_quotes(conn, records)
```

ログ出力の設定や追加のエラーハンドリングはアプリ側で設定してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py (再エクスポート等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (パッケージプレースホルダ)
  - execution/ (パッケージプレースホルダ)
  - strategy/ (パッケージプレースホルダ)

各ファイルは上部にモジュール概要・設計方針が記載されており、関数単位での使い方や例外ポリシーも注釈されています。

---

運用上の注意事項
- OpenAI / J-Quants の API キーを適切に管理してください（.env ファイルは .gitignore に追加）。
- ETL は外部 API 呼び出しを含むためネットワークや API レート制限に注意してください（jquants_client に RateLimiter を実装済み）。
- DuckDB のバージョン互換性や executemany の空リスト制約等に注意（コード内に対応箇所あり）。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化し、環境を明示的に制御すると良いです。

---

ライセンス / 貢献
- 本リポジトリのライセンス表記が無い場合は、利用前にライセンス方針を確認してください。
- バグ報告・機能提案は Issues を立ててください。

---

この README はコードベースの主要機能と使い方の概要を示すことを目的としています。詳細な API リファレンスや運用手順は各モジュールの docstring を参照してください。