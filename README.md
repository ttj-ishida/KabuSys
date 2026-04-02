# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。J-Quants / JPX / RSS / OpenAI 等を統合し、データ収集（ETL）・品質チェック・特徴量計算・ニュースセンチメント（LLM）・市場レジーム判定・監査ログ（発注履歴トレース）等の機能を提供します。

主な設計方針:
- Look‑ahead bias を防止する（内部で date.today() を参照しない設計や、取得日時を記録）
- DuckDB を中心としたローカルデータベース管理
- 冪等性（ETL 保存は ON CONFLICT / upsert）と堅牢なリトライ・バックオフ
- 外部 API 呼び出しの失敗に対するフェイルセーフ（部分失敗を許容して継続）

---

## 機能一覧

- data
  - ETL パイプライン（prices / financials / market_calendar）の差分取得・保存（J-Quants）
  - 市場カレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - ニュース収集（RSS → raw_news、SSRF 防御、ID 正規化）
  - J-Quants クライアント（レートリミット、トークン自動リフレッシュ、ページング）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - 統計ユーティリティ（zscore_normalize 等）
- ai
  - news_nlp.score_news: ニュース記事を LLM でセンチメント評価し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA とニュースセンチメントを組合せて市場レジームを判定し market_regime に書き込み
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns / IC / summary / rank）
- 設定管理
  - 環境変数の自動ロード（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を尊重）
  - Settings クラス経由で型付きアクセス

各モジュールは README 内の API 例と組み合わせて利用できます。

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（少なくとも下記をインストールしてください）
  - duckdb
  - openai（OpenAI Python SDK）
  - defusedxml
  - （その他 urllib, typing などは標準ライブラリ）

pip 例:
pip install duckdb openai defusedxml

※ 実運用では kabu ステーション API 連携、Slack 通知、J-Quants の API トークン等が必要です。

---

## インストール

ソースをクローンしてパッケージとしてインストールする例:

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate

3. 依存インストール
   pip install -e .      # setup.py/pyproject がある場合
   # もしくは:
   pip install duckdb openai defusedxml

---

## 環境変数 / .env

パッケージは起動時にプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し、`.env` と `.env.local` を自動的に読み込みます（OS 環境変数優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（必須/任意）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY (LLM 機能で必要) — OpenAI API キー（ai.score_news / regime_detector など）
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL など（監視・ロギング関連）

.example の簡易雛形（`.env` に保存）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（初期 DB 等）

1. DuckDB ファイルの準備
   - default のパスは settings.duckdb_path（デフォルト data/kabusys.duckdb）
   - DuckDB にスキーマを作成するスクリプトがある場合はそれに従ってください（本リポジトリでは audit.init_audit_db などで監査DBを初期化可能）

2. 監査ログ DB の初期化（例）
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # :memory: も可能

3. ETL 実行用の DB 接続（例）
   import duckdb
   from kabusys.config import settings
   conn = duckdb.connect(str(settings.duckdb_path))

---

## 使い方（主要 API 例）

以下は最小の利用例です。各関数は duckdb の接続と日付を受け取ります。

- 日次 ETL 実行
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント評価（LLM）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API key は環境か引数で

- 研究系ファクター計算
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

- 品質チェック
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)

- 監査スキーマ初期化
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

注意:
- LLM を使う機能（score_news, score_regime）は OPENAI_API_KEY が必要です。
- 外部 API 呼び出し（J-Quants, OpenAI）は失敗する可能性があるため、リトライやフォールバックが組み込まれています。ログを確認してください。

---

## 自動環境ロードの挙動

- パッケージ読み込み時にプロジェクトルートの `.env` と `.env.local` を自動読み込みします。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- テスト時などに自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント（OpenAI）
  - regime_detector.py  — 市場レジーム判定（MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント & DB 保存
  - pipeline.py            — ETL パイプライン / run_daily_etl
  - etl.py                 — ETLResult 再エクスポート
  - news_collector.py      — RSS 取得・前処理・保存
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - quality.py             — データ品質チェック
  - stats.py               — 統計ユーティリティ (zscore_normalize)
  - audit.py               — 監査ログスキーマ定義 / 初期化
- research/
  - __init__.py
  - factor_research.py     — momentum/value/volatility
  - feature_exploration.py — forward returns, IC, summary, rank

---

## 実運用上の注意 / 補足

- Look‑ahead バイアス防止: 多くの処理は target_date を明示し、内部で date.today() に依存しないよう実装されています。バックテストやレトロスペクティブ分析の際は ETL を対象期間まで遡って準備してください。
- 冪等性: ETL の保存処理は ON CONFLICT / upsert を使い、再実行で上書き可能です。
- セキュリティ: news_collector は SSRF 対策（リダイレクト検査 / プライベートアドレス拒否）と XML パーサ保護（defusedxml）を実施しています。
- ロギング・監視: settings.log_level 等でログレベルを制御できます。監視閾値（CPU/MEM/DISK）は環境変数で調整できます。
- 外部依存 API レート・エラー: J-Quants, OpenAI などはレート制限や 5xx をリトライ・バックオフで扱う設計ですが、使用時は利用規約・レートを確認してください。

---

不明点や README に追加したい具体的なサンプル（eg. ETL スケジューリング、Kabu ステーションとの発注フロー例、CI 用のテスト手順など）があれば教えてください。必要に応じてセクションを拡張します。