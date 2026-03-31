# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買ユーティリティ群を集めたライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI を用いたセンチメント解析）、ファクター計算・特徴量探索、監査ログ（発注→約定トレーサビリティ）などを提供します。

---

## 主な機能（Feature一覧）

- データ取得・ETL
  - J-Quants API からの日次株価（OHLCV）、財務データ、JPX カレンダー取得（差分更新、ページネーション対応、リトライ／レート制御）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次パイプライン run_daily_etl（カレンダー→株価→財務→品質チェック）

- データ品質チェック
  - 欠損（OHLC）／重複／スパイク（前日比）／日付整合性チェック

- ニュース収集・NLP
  - RSS 取得（SSRF対策・トラッキングパラメータ除去・gzip対応）と raw_news テーブルへの保存
  - OpenAI（gpt-4o-mini）を使った銘柄単位ニュースセンチメント score_news（JSON Mode）、LLM 呼び出しのリトライとレスポンス検証

- 市場レジーム判定
  - ETF（1321）200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジーム判定（bull/neutral/bear）

- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査スキーマの初期化（冪等）
  - 監査用専用 DuckDB 初期化ユーティリティ

- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）・ランク化・統計サマリー
  - z-score 正規化ユーティリティ

- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日列挙、夜間バッチ更新ジョブ（J-Quants から取得）

---

## 動作環境・依存

- 推奨 Python バージョン: 3.10+
- 必要な主なパッケージ（少なくとも以下をインストールしてください）
  - duckdb
  - openai
  - defusedxml

（パッケージはプロジェクトの packaging / requirements に合わせてインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージを配置

2. 仮想環境を作成して依存をインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb openai defusedxml

   - パッケージとして開発インストールする場合:
     - pip install -e .

3. 環境変数 / .env の設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（OS 環境変数 > .env.local > .env の順）。
   - 自動ロードを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用）。

   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（get_id_token に使用）
     - KABU_API_PASSWORD : kabuステーション API パスワード（発注系を使う場合）
     - SLACK_BOT_TOKEN : Slack 通知を使う場合
     - SLACK_CHANNEL_ID : Slack 通知先チャンネルID
     - OPENAI_API_KEY : OpenAI API キー（AI モジュールを使う場合）
   - 任意 / デフォルト値あり
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト `INFO`
     - KABU_API_BASE_URL — デフォルト `http://localhost:18080/kabusapi`
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`

   - サンプル `.env`（例）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx...
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABU_API_PASSWORD=your_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB の接続先ディレクトリの作成（必要に応じて）
   - `mkdir -p data`

---

## 使い方（主要 API と実行例）

以下はライブラリ内の公開関数を直接呼ぶ簡単な例です。実運用ではログ設定・エラーハンドリング・ジョブスケジューラを組み合わせてください。

- DuckDB 接続の作成例:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（市場カレンダー→株価→財務→品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（OpenAI を使用）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数にセットしておくか、api_key 引数に渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数で提供
  ```

- 監査ログスキーマの初期化（監査用 DuckDB の作成）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
  # 以降 audit_conn を使って監査テーブルにアクセス
  ```

- マーケットカレンダー操作例
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  import datetime as dt
  d = dt.date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, date(2026, 3, 20))
  # records は各銘柄ごとの dict のリスト
  ```

注意:
- AI 系（score_news / score_regime）は OpenAI の API キーが必要です。引数で api_key を渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- ETL / API 呼び出しは外部サービスへの接続と課金リスクが伴うため、実行前に設定と権限を確認してください。

---

## テスト・開発向けのヒント

- 自動環境変数読み込みを無効化する:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env の自動読み込みをスキップします（ユニットテストなどで便利）。
- OpenAI 呼び出しや HTTP をモックすることを推奨（ユニットテストでネットワークに依存しないように）。
- DuckDB の in-memory を使うなら `duckdb.connect(":memory:")`。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下、主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NLP / score_news
    - regime_detector.py  — 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - calendar_management.py  — 市場カレンダー管理（判定、next/prev/get）
    - etl.py / pipeline.py     — ETL パイプライン（run_daily_etl 等）、ETLResult
    - stats.py                 — z-score 正規化等の統計ユーティリティ
    - quality.py               — データ品質チェック
    - audit.py                 — 監査ログスキーマ初期化 / init_audit_db
    - jquants_client.py        — J-Quants API クライアント（fetch_*/save_*）
    - news_collector.py        — RSS 取得・前処理・保存
    - pipeline.py              — ETLResult エクスポート
  - research/
    - __init__.py
    - factor_research.py       — Momentum/Value/Volatility 等
    - feature_exploration.py   — 将来リターン/IC/統計サマリー
  - ai、research、data の副モジュール群（内部実装が多岐に渡ります）

---

## ライセンス / 貢献

この README はコードベースの概要を示すものです。実際のライセンス・貢献ルールはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

README に記載されていない詳細な使い方や内部仕様については、各モジュールの docstring を参照してください。追加で README に載せたい実行例やワークフロー（例: CI のワークフロー、cron ジョブ例など）があれば教えてください。必要に応じて追記します。