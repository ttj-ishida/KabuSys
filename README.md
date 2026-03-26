# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼研究・自動売買支援ライブラリです。J-Quants / kabuステーション / OpenAI 等と連携して、データ取得（ETL）、データ品質チェック、ニュース NLP による銘柄スコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）などを提供します。  
このリポジトリはライブラリとして各種処理をモジュール化しており、本番運用・紙取引・研究用途いずれにも対応する設計になっています。

主な特徴
- J-Quants API からの差分 ETL（株価/財務/カレンダー）と DuckDB への冪等保存
- ニュース収集（RSS）と OpenAI を用いたセンチメント評価（銘柄単位）および市場レジーム判定
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化
- 環境設定は .env または環境変数で管理。配布後も安全に動作するよう設計

---

機能一覧
- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（API レート制御、リトライ、トークン自動更新）
  - カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - ニュース収集: RSS 取得、前処理、raw_news への冪等保存（SSRF 対策、サイズチェック）
  - データ品質チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄ごとのニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF 1321 の MA とマクロ記事の LLM センチメントを合成して market_regime に書き込む
- research
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - Settings: 環境変数から構成を読み込む（自動で .env/.env.local をプロジェクトルートから読み込み）

注意: 本ライブラリは「発注」「実際の口座操作」を自動で行うためのモジュール群を含む設計になっていますが、コードは発注実装を分離しており、誤って本番発注が走らないよう設計方針・フラグ（KABUSYS_ENV 等）を持っています。実際に発注を行う部分を組み合わせる場合は十分なレビューと安全対策を行ってください。

---

セットアップ手順（開発環境例）
1. リポジトリをクローンして仮想環境を用意
   - 例（venv を使う）
     ```
     python -m venv .venv
     source .venv/bin/activate   # Windows: .venv\Scripts\activate
     pip install --upgrade pip
     ```
2. 依存パッケージをインストール
   - 基本的に以下パッケージが必要です（プロジェクトによって追加が必要な場合あり）:
     - duckdb
     - openai
     - defusedxml
     - requests（必要に応じて）
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - パッケージ管理は requirements.txt / pyproject.toml を利用してください（本サンプルでは仮定）。

3. インストール（開発モード）
   ```
   pip install -e .
   ```
   （セットアップ用の pyproject.toml / setup.cfg がある場合。無ければ直接モジュールをインポートして使えます）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（代表例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...  # AI 機能を使う場合
   - データベースパス（デフォルト）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

5. ログ/環境
   - KABUSYS_ENV: development / paper_trading / live のいずれか
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

---

使い方（主要な例）

1) 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)            # Path オブジェクト
print(settings.is_live, settings.env)
```

2) DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース NLP によるスコア取得（OpenAI API キー必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は DuckDB 接続（raw_news / news_symbols / ai_scores テーブルが必要）
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print(f"scored {count} codes")
```

4) 市場レジーム評価（OpenAI 必須）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ作成されます
```

6) 研究用 API（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum, calc_value
from datetime import date

momentums = calc_momentum(conn, date(2026, 3, 20))
values = calc_value(conn, date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(momentums, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- 多くの関数は「ルックアヘッドバイアス防止」のため date.today() 等に依存しない設計です。バックテストで使う場合は target_date を明示してください。
- OpenAI 呼び出しには API レート制御やリトライが組み込まれていますが、API キーと使用ポリシーの管理はユーザ側で行ってください。
- J-Quants の API はレート制限（120 req/min）を厳守する実装です。認証トークンは自動更新されますが、環境変数でのトークン管理を適切に行ってください。

---

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須で ETL を走らせる際に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: ログレベル（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効化（テスト時に便利）

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP（銘柄スコアリング）
    - regime_detector.py              — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント & 保存
    - pipeline.py                     — ETL パイプライン（run_daily_etl など）
    - etl.py                          — ETL の公開型（ETLResult）
    - news_collector.py               — RSS ニュース収集・前処理
    - quality.py                      — 品質チェック
    - stats.py                        — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py          — マーケットカレンダー管理
    - audit.py                         — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py              — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py          — 将来リターン / IC / 統計サマリー 等
  - ai/__pycache__ etc.

（README はプロジェクトのトップレベルに置く想定です。実行に必要な DB スキーマや初期テーブル作成は別途 schema 初期化手順を提供してください。多くのモジュールは既存のテーブルを前提としています。）

---

運用上の注意
- is_live / is_paper / is_dev フラグ（settings.is_live など）で動作モードの切り替えを行ってください。本番での自動発注を行う場合は必ず多重防護（レビュー・手動確認・レート制限・冪等キー）を実装してください。
- ニュース収集や外部 API 呼び出しは信頼性・コストに関わるため、運用時はレート制御とエラーハンドリングを十分に監視してください。
- DuckDB の executemany はバージョン差異で空リストを受け付けない制約があるため、モジュール実装でも保護されている点に注意してください。

---

貢献・開発
- バグ修正や機能追加は Pull Request を歓迎します。API 変更時は互換性に注意し、テストケース（特に ETL と品質チェック）を追加してください。
- ログや警告は多用しているため、DEBUG レベルでの実行により内部挙動を追跡しやすくなります。

---

ライセンス / 著作権
- 本リポジトリのライセンス表記がプロジェクトに別途ある場合はそちらに従ってください（ここでは明示していません）。

---

問題報告・問い合わせ
- Issue に具体的な再現手順・ログ・環境情報を添えて報告してください。API キーや秘密情報は含めないでください。