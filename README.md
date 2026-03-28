# KabuSys — 日本株自動売買プラットフォーム（README）

日本語ドキュメントです。KabuSys は日本株向けのデータ基盤・リサーチ・AI 評価・監査ログを備えた自動売買システムのコアライブラリ群です。本リポジトリにはデータ取得（J‑Quants）、ETL、ニュース収集・NLP（OpenAI）、ファクター計算、バックテスト用の研究ユーティリティ、監査ログ初期化などのモジュールが含まれます。

---

目次
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 環境変数（.env）例
- 使い方（主要操作の例）
  - DuckDB 接続
  - 日次 ETL 実行
  - ニュース NLP スコア生成
  - 市場レジーム判定
  - 監査ログ DB 初期化
- 自動 .env ロードについての注意
- ディレクトリ構成（主要ファイル一覧）
- テスト / 開発メモ

---

プロジェクト概要
- 日本国内株式データを J‑Quants API から取得し、DuckDB に格納・品質チェックを行う ETL パイプラインを提供します。
- RSS ベースのニュース収集と OpenAI（gpt-4o-mini）を用いた銘柄別 / マクロのセンチメント評価を行い、ai_scores や market_regime といったテーブルに保存します。
- 研究用のファクター計算（モメンタム・バリュー・ボラティリティ等）や統計ユーティリティを備えています。
- 監査ログ（signal_events / order_requests / executions）を保持する監査用 DuckDB 初期化ユーティリティを提供します。
- J‑Quants のレート制限・認証更新、OpenAI 呼び出しのリトライやフェイルセーフ設計が組み込まれています。

主な機能（抜粋）
- ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- J‑Quants クライアント: fetch_* / save_*（raw_prices, raw_financials, market_calendar など）
- ニュース収集: RSS を安全に取得して raw_news に保存（SSRF / Gzip bomb 等に対策済み）
- ニュース NLP: score_news（銘柄ごとの AI スコアを ai_scores テーブルに保存）
- レジーム判定: score_regime（ETF 1321 の MA とマクロニュースを合成）
- 研究: calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- 品質チェック: missing_data, spike, duplicates, date_consistency, run_all_checks
- 監査ログ初期化: init_audit_schema / init_audit_db

必要条件
- Python 3.10+
- 推奨ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の依存は setup で管理してください）

セットアップ手順（例）
1. リポジトリをクローン（省略）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージをインストール（例）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - またはローカルパッケージとしてインストール: pip install -e .

4. プロジェクトルートに .env を準備（下記参照）
5. DuckDB 用ディレクトリを作成（デフォルトは data/）
   - mkdir -p data

環境変数（.env）例
- 自動ロード: kabusys.config はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を自動でロードします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

最低限設定が必要な環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN=（必須）J‑Quants リフレッシュトークン
- KABU_API_PASSWORD=（必須）kabu ステーション API パスワード
- SLACK_BOT_TOKEN=（必須）Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID=（必須）通知先チャンネル ID
- OPENAI_API_KEY=（OpenAI を使う機能を利用する場合は必須）
オプション:
- KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
- LOG_LEVEL=INFO|DEBUG|...
- KABUS_API_BASE_URL=（kabu API の base URL。デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

簡易 .env.example:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

使い方（主要操作の例）

1) DuckDB 接続を取得する
```python
import duckdb
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))
```

2) 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース NLP（銘柄ごとの AI スコア）を実行する
- score_news は OpenAI API キーを引数で受け取れます（未指定なら環境変数 OPENAI_API_KEY を参照）。
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数のキーを使う場合 api_key=None
print(f"written scores: {n_written}")
```

4) 市場レジーム判定（ETF 1321 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```
- OpenAI 呼び出しに失敗してもフェイルセーフで macro_sentiment=0.0 を使う設計です。
- API キーは api_key 引数または OPENAI_API_KEY 環境変数で供給します。

5) 監査ログ DB を初期化する（監査専用 DB を別に作成する場合）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```
- init_audit_db は指定パスの親ディレクトリを自動作成します。":memory:" でインメモリ DB も可。

6) JPX カレンダー更新ジョブを直接実行する
```python
from kabusys.data.calendar_management import calendar_update_job
calendar_update_job(conn)
```

自動 .env ロードについての注意
- kabusys.config はプロジェクトルート（.git または pyproject.toml が見つかる場所）をベースに .env と .env.local を自動読み込みします。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - テストや特別な用途で自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py       — 銘柄別ニュースセンチメント（score_news）
    - regime_detector.py — マクロ + MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J‑Quants API クライアント（fetch_* / save_*）
    - pipeline.py       — ETL パイプライン（run_daily_etl 他）
    - etl.py            — ETL の公開インターフェース（ETLResult）
    - calendar_management.py — 市場カレンダーの判定・更新ロジック
    - news_collector.py — RSS ニュース収集（SSRF 対策等含む）
    - quality.py        — データ品質チェック（run_all_checks 等）
    - stats.py          — zscore_normalize 等統計ユーティリティ
    - audit.py          — 監査ログテーブルの初期化・DB 作成
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - ai/、data/、research/ はそれぞれの責務に沿って機能が分離されています。

テスト / 開発メモ
- OpenAI 呼び出しはモックしやすいように内部の _call_openai_api を patch してテストできます（news_nlp._call_openai_api / regime_detector._call_openai_api をモック）。
- J‑Quants クライアントは get_id_token の自動リフレッシュや rate limiter を備えています。API を模擬する際は jquants_client._request をモックすると良いです。
- ETL 実行は部分失敗（1 ステップの例外）でも他ステップを継続する設計です。ETLResult にエラー・品質問題が蓄積されます。

ライセンス・貢献
- 本 README はコードベースの説明を目的としたもので、実際の運用環境では API キーやパスワードを厳重に管理し、実資金での稼働時は十分なリスク管理を行ってください。
- コントリビューションやバグ報告はリポジトリの issue を利用してください。

---

補足・注意点
- 多くの処理は「ルックアヘッドバイアス（未来データ参照）」を避ける設計になっています（date.today()/datetime.today() を直接参照しない等）。
- OpenAI / J‑Quants の API 呼び出しはリトライ・バックオフ・フェイルセーフを実装していますが、利用量に応じたコスト・レート制限に注意してください。
- 実際の発注（execution / order_requests）と接続するブローカー API の実装はこのコードベースでは限定的です。production（live）モードでの使用は慎重に行ってください（KABUSYS_ENV 設定を必ず確認）。

必要であれば README にコマンド別のさらに詳しい実行例（systemd ジョブ、cron、Dockerfile、CI 設定等）や SQL スキーマ定義（テーブル DDL）の抜粋を追加できます。どの項目を詳しく載せたいか教えてください。