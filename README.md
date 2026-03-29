# KabuSys

KabuSys は日本株向けのデータ基盤・機械学習・自動売買補助ライブラリです。J-Quants / RSS / OpenAI（LLM）を組み合わせて、データ取得（ETL）・データ品質チェック・ニュース NLP による銘柄スコアリング・市場レジーム判定・監査ログ（トレーサビリティ）を提供します。

---

## 主な特徴（機能一覧）

- データ取得（J-Quants API 経由）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー
  - ページネーション対応、トークン自動リフレッシュ、レート制御、リトライ
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL のエントリポイント（run_daily_etl）
- ニュース収集 & NLP
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、圧縮対応）
  - OpenAI（gpt-4o-mini）による銘柄別ニュースセンチメント（score_news）
  - LLM 呼び出しに対する堅牢なリトライ・レスポンス検証
- 市場レジーム判定
  - ETF（1321）200 日移動平均乖離とマクロニュースの LLM センチメントを合成（score_regime）
  - ルックアヘッドバイアス対策済みの設計
- 監査（Audit）テーブル
  - signal_events / order_requests / executions 等の監査スキーマを提供
  - 冪等で初期化、UTC タイムスタンプ管理
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計、Z スコア正規化

---

## 動作要件

- Python 3.10 以上（typing の |, from __future__ import annotations を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク経由で外部 API（J-Quants, OpenAI, RSS）へアクセスするため適切な API トークンが必要

（プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

---

## セットアップ手順

1. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

2. 依存パッケージのインストール（プロジェクトに依存ファイルがない場合は手動で）
   - pip install duckdb openai defusedxml

   またはプロジェクトルートに pyproject.toml / requirements.txt がある場合:
   - pip install -r requirements.txt
   - もしくは pip install -e .

3. 環境変数 / .env の準備
   - 以下の必須環境変数を設定してください（例は次節を参照）。
   - パッケージは起動時にプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

---

## 環境変数（.env 例）

必須:
- JQUANTS_REFRESH_TOKEN=あなたの_jquants_リフレッシュトークン
- SLACK_BOT_TOKEN=あなたのSlackBotトークン
- SLACK_CHANNEL_ID=通知先SlackチャンネルID
- KABU_API_PASSWORD=（kabuステーション API を使う場合のパスワード）

任意 / デフォルトあり:
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=INFO|DEBUG|WARNING|ERROR|CRITICAL  （デフォルト: INFO）
- OPENAI_API_KEY=あなたのOpenAI APIキー（score_news / score_regime 呼び出し時に渡すことも可）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動 .env 読み込みを無効化（テスト時など）

例（.env）:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

注意: Settings オブジェクトは必須変数未設定時に ValueError をスローします。

---

## 使い方（主要機能の呼び出し例）

以下は Python REPL / スクリプト内から直接呼び出す例です。DuckDB 接続には duckdb.connect を使用します。

1. DuckDB 接続例
   - import duckdb
   - from kabusys.config import settings
   - conn = duckdb.connect(str(settings.duckdb_path))

2. 日次 ETL 実行
   - from kabusys.data.pipeline import run_daily_etl
   - from datetime import date
   - conn = duckdb.connect(str(settings.duckdb_path))
   - result = run_daily_etl(conn, target_date=date(2026,3,20))
   - print(result.to_dict())

3. ニューススコアリング（OpenAI を使用）
   - from kabusys.ai.news_nlp import score_news
   - from datetime import date
   - conn = duckdb.connect(str(settings.duckdb_path))
   - count = score_news(conn, target_date=date(2026,3,20), api_key=settings.openai_api_key if hasattr(settings, "openai_api_key") else None)
   - print(f"scored {count} codes")

   注意: score_news は OPENAI_API_KEY を引数または環境変数で取得します。API 呼び出しに失敗した銘柄はスキップされる設計です。

4. 市場レジーム判定
   - from kabusys.ai.regime_detector import score_regime
   - from datetime import date
   - conn = duckdb.connect(str(settings.duckdb_path))
   - score_regime(conn, target_date=date(2026,3,20), api_key=os.environ.get("OPENAI_API_KEY"))

5. 監査テーブル初期化
   - from kabusys.data.audit import init_audit_db, init_audit_schema
   - conn = init_audit_db("data/audit.duckdb")  # ファイル作成してスキーマ適用
   - あるいは既存接続に対して init_audit_schema(conn, transactional=True)

6. 研究用ユーティリティ（ファクター計算等）
   - from kabusys.research import calc_momentum, calc_value, calc_volatility
   - from datetime import date
   - conn = duckdb.connect(str(settings.duckdb_path))
   - mom = calc_momentum(conn, date(2026,3,20))

---

## 重要な設計上の注意点（実運用・研究での留意点）

- ルックアヘッドバイアス（バックテストにおける未来情報使用）を避ける設計になっています。
  - 各モジュールは target_date 引数を用いて、内部で datetime.now() や date.today() に直接依存しない実装を心がけています。
- OpenAI など外部 API は失敗してもプロセスを停止させず、フェイルセーフ（デフォルトスコアやスキップ）を行います。
- ETL / DB 書き込みは多くの場合冪等（ON CONFLICT DO UPDATE）を意識しています。
- ニュース取得は SSRF / XML バグ対策（defusedxml、URL 検証、サイズ上限）を含みます。

---

## ディレクトリ構成

（src 配下を基準）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news, calc_news_window 等）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - etl.py                 — ETL ユーティリティ公開（ETLResult）
    - pipeline.py            — 日次 ETL 実装（run_daily_etl, run_prices_etl 等）
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py             — データ品質チェック（欠損・スパイク・重複等）
    - audit.py               — 監査ログ（テーブル定義・初期化）
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS 取得・前処理・raw_news 保存
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - (他モジュール: strategy / execution / monitoring 等を想定して __all__ にあり)

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が未設定
  - settings のプロパティが必須変数をチェックします。`.env` を作って必要なキーを設定してください。
- OpenAI や J-Quants の API 呼び出し失敗
  - ネットワークや API キーの有効期限、レート制限に注意。ログは再試行やフォールバックの理由を出力します。
- DuckDB に書き込みが行われない
  - 接続パス、パーミッション、テーブルが存在するか（初期スキーマが必要な場合は別途スキーマ初期化）を確認してください。
- RSS 取得が失敗する（SSRF / リダイレクトで除外される）
  - fetch_rss はプライベートアドレスや非 http(s) スキームを拒否します。外部向け RSS のみ使用してください。

---

## 開発・テスト

- 自動 .env 読み込みを無効化するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- テスト時は OpenAI / ネットワーク呼び出しをモックすることを推奨します（モジュール内の _call_openai_api や _urlopen を patch）。

---

README はプロジェクトの概要を中心にまとめています。詳細な API ドキュメントや開発者向け設計文書（StrategyModel.md, DataPlatform.md 等）があればそれらを併せて参照してください。必要であれば README にさらに「コマンドラインツール」「デプロイ手順」「CI 設定」などを追加できます。ご希望があれば追記します。