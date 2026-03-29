# KabuSys

日本株向け自動売買・データ基盤ライブラリ (KabuSys)

このリポジトリは、日本株のデータ収集（J-Quants / RSS）、データ品質チェック、ファクター計算、LLM を用いたニュースセンチメント評価、監査ログ（オーダー・約定トレース）などを含む自動売買 / リサーチ基盤のコア実装群です。

主な設計方針
- ルックアヘッドバイアス防止（内部で datetime.today()/date.today() を安易に参照しない）
- DuckDB をデータ格納に利用（軽量で SQL が使える組み込み DB）
- API 呼び出しはリトライ／バックオフ／レート制御等の堅牢な実装
- LLM（OpenAI）呼び出しは JSON Mode を使った厳密な入出力検証
- ETL / 品質チェックは部分失敗を許容して他処理を継続（フェイルセーフ）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - 必須環境変数の明示的チェック
- データ収集（J-Quants）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得 / 保存（差分ETL）
  - レート制限 / リトライ / トークン自動リフレッシュ対応
- ニュース収集
  - RSS フィードからの記事取得、URL 正規化、SSRF 保護、gzip/RSS パース、安全対策
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを統合して LLM に投げ、センチメント（ai_scores）を保存
  - チャンク/バッチ処理、再試行、レスポンス検証
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して日次レジーム判定
- 監査ログ（Audit）
  - signal_events / order_requests / executions のスキーマ定義・初期化（冪等）
  - トレーサビリティ向け設計（UUID、created_at/updated_at、UTC）
- ETL パイプライン
  - run_daily_etl によるカレンダー・株価・財務の差分取得と品質チェックの統合
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック。QualityIssue オブジェクトで集約
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility 等）、forward returns、IC 計算、zscore 正規化

---

## 必要な環境変数

主に以下を設定してください（.env をプロジェクトルートに置くことを推奨）。

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注を使う場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャネル ID（通知先）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）

任意 / デフォルトあり
- KABUSYS_ENV: development | paper_trading | live （デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
- KABUSYS_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

.env 自動読み込みについて
- パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、その下の `.env` と `.env.local` をロードします。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- テストなどで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（代表的なパッケージ）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使う）
   - pip install -r requirements.txt

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. .env を作成して必須環境変数を設定
   - プロジェクトルートに .env を置くと自動で読み込まれます。
   - 例（最小）:
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...

5. DuckDB データベースの用意（デフォルトは data/kabusys.duckdb）
   - フォルダが無ければ自動作成されます。コード内で Path(settings.duckdb_path) を使って接続してください。

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトから呼び出す例です。

- DuckDB 接続の作成
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースのセンチメントスコアを作成（ai_scores へ書き込み）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"wrote {written} scores")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))

- マーケットカレンダー更新ジョブ（J-Quants から差分取得）
  from kabusys.data.calendar_management import calendar_update_job
  calendar_update_job(conn)

- 監査ログ DB 初期化（別 DB に分けたい場合）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

- 研究用ユーティリティ（例: モメンタム）
  from kabusys.research import calc_momentum
  calc_momentum(conn, target_date=date(2026,3,20))

注意点
- OpenAI / J-Quants API 呼び出しはネットワーク・課金対象です。キーは適切に管理してください。
- LLM 呼び出しは JSON レスポンスを厳密に検証しますが、API の挙動変化に備えてログを確認してください。
- DuckDB の executemany に関するバージョン差異（空リスト渡せない等）に留意しています。

---

## ディレクトリ構成（重要ファイル概観）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み・Settings 定義（jquants トークン、OpenAI など）
- ai/
  - __init__.py
  - news_nlp.py       — ニュースをまとめて LLM でスコアリングし ai_scores に保存
  - regime_detector.py— ETF MA とマクロニュースを合成して market_regime を作成
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得／保存ロジック）
  - pipeline.py       — run_daily_etl など ETL パイプライン
  - etl.py            — ETL の公開型再エクスポート（ETLResult）
  - news_collector.py — RSS 取得・正規化・保存
  - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
  - quality.py        — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py          — zscore_normalize 等の統計ユーティリティ
  - audit.py          — 監査ログ（signal/order/execution）スキーマ初期化
  - pipeline.py       — ETL の中心処理（差分取得・保存・品質チェック）
  - etl.py            — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py    — momentum/value/volatility の計算
  - feature_exploration.py— forward returns, IC, rank, factor_summary
- monitoring/ (パッケージがある場合に監視関連を配置)
- strategy/, execution/, monitoring/ （__all__ に含まれるがここでは主要実装を抜粋）

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、DB 上の既存テーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）を参照/更新する設計です。

---

## 実運用時の注意点

- KABUSYS_ENV を production や live にした場合は外部発注ロジックに十分注意してください（paper_trading を活用）。
- OpenAI 呼び出しはリクエスト料金とレイテンシのコストがあるため、バッチ頻度とモデル選択を慎重に決めてください。
- J-Quants のレート制限（デフォルト 120 req/min）に合わせた実装になっていますが、大量ページネーション時は運用監視を推奨します。
- DuckDB のファイルは適切にバックアップしてください。監査ログは削除しない前提の設計です。

---

## よくある操作（コマンド例）

- 日次 ETL（スクリプトから）
  python -c "from kabusys.data.pipeline import run_daily_etl; import duckdb, os; from kabusys.config import settings; conn=duckdb.connect(str(settings.duckdb_path)); print(run_daily_etl(conn).to_dict())"

- ニューススコアリング（特定日）
  python -c "from kabusys.ai.news_nlp import score_news; import duckdb; from kabusys.config import settings; conn=duckdb.connect(str(settings.duckdb_path)); print(score_news(conn, __import__('datetime').date(2026,3,20)))"

---

## サポート / 拡張案

- 発注層（kabu ステーション）との統合（execution モジュール）を使って実運用する場合は、必ず paper_trading フラグや sandbox 環境で十分テストを行ってください。
- ニュースソース追加、モデル切替、バッチサイズ調整、品質チェックルールのチューニングが可能です。
- モニタリング（Prometheus / Sentry 等）を組み込むと運用性が向上します。

---

作成・メンテナンス: KabuSys 開発チーム  
ライセンス・貢献方法等はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。