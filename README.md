# KabuSys

日本株向けのデータプラットフォーム & 研究・AI支援モジュール群。  
株価・財務・ニュースの収集・ETL、データ品質チェック、ファクター計算、ニュースセンチメント評価（OpenAI 利用）、市場レジーム判定などを含むライブラリです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築のための基盤ライブラリ群です。主に以下を扱います。

- J-Quants API からのデータ取得（株価日足、財務、上場情報、JPX カレンダー）
- DuckDB を用いたデータ保存と ETL（差分更新・バックフィル・品質チェック）
- RSS からのニュース収集と前処理（SSRF 防御・トラッキング除去など）
- OpenAI（gpt-4o-mini）を使ったニュース NLP（銘柄別センチメント）とマクロセンチメントによる市場レジーム判定
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ・将来リターン・IC 等）
- 監査ログ（シグナル → 発注 → 約定）用スキーマの初期化ユーティリティ

本リポジトリはシステムのデータ基盤・研究ワークフロー・AI 評価ロジックを提供し、発注実行や監視周りを組み合わせて運用システムを構築するための基礎になります。

---

## 主な機能一覧

- data/
  - ETL（差分取得、backfill、カレンダー先読み）
  - J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - 市場カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS、URL 正規化、SSRF 対策、重複排除）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - 統計ユーティリティ（Zスコア正規化）
- ai/
  - news_nlp.score_news: 銘柄毎のニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定（bull/neutral/bear）
- research/
  - factor_research: モメンタム、バリュー、ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー

---

## 前提 / 必要環境

- Python 3.10+
- 必要な Python パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS ソース にアクセスする場合）

依存は pyproject.toml / requirements.txt を用意している場合はそちらからインストールしてください。最小例:

```bash
python -m pip install duckdb openai defusedxml
# or
pip install -e .
```

---

## 環境変数

設定は .env ファイルまたは環境変数から読み込まれます（packages/kabusys/config.py）。自動ロード動作はプロジェクトルート（.git または pyproject.toml）を探索して行います。自動ロードを無効にするには環境変数を設定してください:

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（必須は README 内にも明記）:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL : kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
- OPENAI_API_KEY : OpenAI API キー（ai モジュール使用時に必要）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : SQLite / 監視 DB パス（デフォルト data/monitoring.db）
- KABUSYS_ENV : 環境 ("development" | "paper_trading" | "live")（デフォルト development）
- LOG_LEVEL : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

.example の簡易記述例（.env.example）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=yourpassword
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージのインストール
   ```bash
   pip install -r requirements.txt   # もし用意されていれば
   # 最小
   pip install duckdb openai defusedxml
   ```

4. .env を作成（.env.example を参考に）
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

---

## 使い方（代表的なユースケース）

以下は主要 API の簡単な使用例（Python）です。実行前に環境変数を設定してください。

- DuckDB 接続を作る:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に書き込む:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {n} scores")
  ```

- マクロセンチメントと MA200 を合成して市場レジームを判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB を初期化（別 DB を使う場合）:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（例：モメンタム）:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]
  ```

注意点:
- AI 関連機能（news_nlp / regime_detector）は OPENAI_API_KEY を必要とします。
- ETL / API 呼び出しはネットワーク・認証（J-Quants）の実環境に依存します。テスト時はモックや KABUSYS_DISABLE_AUTO_ENV_LOAD を活用してください。
- DuckDB のバージョンや SQL の互換性に依存する箇所があります（コード内に互換性対策あり）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     -- 銘柄別ニュースセンチメント算出
    - regime_detector.py              -- マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - etl.py                          -- ETL 結果型のエクスポート
    - calendar_management.py          -- マーケットカレンダー管理（営業日判定等）
    - news_collector.py               -- RSS ニュース収集
    - quality.py                      -- データ品質チェック
    - stats.py                        -- 統計ユーティリティ（zscore 等）
    - audit.py                        -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py              -- モメンタム / バリュー / ボラティリティ
    - feature_exploration.py          -- 将来リターン / IC / 統計サマリー
  - （execution/monitoring 等の名前空間は __init__ で公開予定）

---

## 実運用上の注意点

- Look-ahead bias に対する配慮がコード内に多数あります（datetime.today() を直接参照しない、クエリは target_date 未満／以下の扱いの徹底など）。バックテストやリサーチで利用する場合はこの方針を尊重してください。
- J-Quants API はレート制限があります（120 req/min）。jquants_client でレート制御およびリトライを実装していますが、多数の並列処理は避けてください。
- OpenAI の呼び出しはエラー時にフォールバック（macro_sentiment=0.0 など）やリトライを行う実装です。コスト・レイテンシに注意してください。
- 監査ログは削除しない運用を前提としています。order_request_id を冪等キーとして二重発注防止を行う設計です。

---

## 貢献 / テスト

- ユニットテストやモックの利用が想定されています。特に OpenAI や外部 API 呼び出しはモック可能な設計（内部 _call_openai_api の差し替え等）になっています。
- 新しい機能追加や修正は PR でお願いします。CI で DuckDB や外部 API のモックを用いたテストを推奨します。

---

必要ならば README に含めるコマンド例（systemd タスク、cron、Dockerfile、より詳細な .env.example、CI 設定）の作成や、各モジュールの API リファレンス（関数ごとの引数・戻り値例）を追記します。どの情報を優先して追加しますか？