# KabuSys

日本株向け自動売買・データ基盤ライブラリ（軽量プロトタイプ）

概要
- KabuSys は日本株のデータ取得（J-Quants）、ETL、ニュースセンシング（LLM 経由の NLP）、リサーチ用ファクター計算、監査（オーダー/約定トレーサビリティ）などを行うためのモジュール群です。
- DuckDB をデータ格納に使い、J-Quants API / OpenAI（gpt-4o-mini）を外部サービスとして利用します。
- バックテストや本番運用のためのデータ整備（差分 ETL、品質チェック）、ニューススコアリング、マーケットレジーム判定などのユーティリティを提供します。

主な機能
- データ取得 / ETL
  - J-Quants から株価日足、財務データ、マーケットカレンダーを差分取得して DuckDB に保存
  - run_daily_etl による日次 ETL パイプライン（カレンダー→株価→財務→品質チェック）
- データ品質チェック
  - 欠損データ、スパイク（急騰/急落）、重複、日付不整合の検出
- ニュース収集 / 前処理
  - RSS フィード取得、URL 正規化、記事 ID 生成（SHA-256 の先頭）および raw_news テーブルへの冪等保存
  - SSRF 対策・サイズ制限・XML パース安全化（defusedxml）
- ニュース NLP（LLM）
  - 銘柄ごとにニュースを統合して OpenAI に投げ、センチメント（ai_score）を ai_scores に記録（score_news）
  - API 呼び出しはバッチ化・リトライ・レスポンス検証あり
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュース LLM スコアを合成して market_regime を日次で判定（score_regime）
- リサーチ（因子計算・探索）
  - Momentum / Value / Volatility 等のファクター計算、将来リターン計算、IC（スピアマン）や統計サマリー
  - zscore_normalize 等のユーティリティ
- 監査ログ（オーダーから約定までのトレーサビリティ）
  - signal_events, order_requests, executions 等の監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）

前提要件（最低限）
- Python 3.10+
- 必要と思われるパッケージ（プロジェクトの pyproject/requirements に準拠してください）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI API、RSS フィード等）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)
3. 依存関係をインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用）
4. パッケージを開発モードでインストール（任意）
   - python -m pip install -e .
   - （src レイアウトを使用しているため -e . が推奨）
5. 環境変数 / .env を用意
   - プロジェクトルート（.git のあるディレクトリ）に .env または .env.local を置くと自動ロードされます（OS 環境変数が優先）。
   - 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

重要な環境変数
- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（ETL / API 呼び出しで使用）
- OPENAI_API_KEY (必須 for news / regime)
  - OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD
  - kabu ステーション API のパスワード（実行モジュールから参照）
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)
  - LINE 通知を使う場合
- DUCKDB_PATH (任意)
  - データベースファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)
  - 監視用 SQLite 等のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意)
  - 有効値: development, paper_trading, live
  - 本番判定は settings.is_live / is_paper / is_dev を使用
- LOG_LEVEL (任意): DEBUG|INFO|WARNING|ERROR|CRITICAL

簡易 .env 例
（プロジェクトルートに .env を置いてください）
ENV:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

自動 .env の読み込み順序
- OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化
- 読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます

使い方（代表的な API）
- DuckDB に接続して ETL を実行する例
  - Python REPL / スクリプト:
    - import duckdb
    - from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect(str(<your_duckdb_path>))  # settings.duckdb_path を使う場合は settings を参照
    - result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日の処理
    - print(result.to_dict())

- ニューススコアリング（score_news）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境で参照
  - print(f"書込件数: {written}")

- 市場レジーム判定（score_regime）
  - from datetime import date
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査 DB 初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")

注意点 / 実運用上のヒント
- Look-ahead バイアス防止
  - 各モジュールは内部で date や window を明示的に扱い、datetime.now()/today() の直接利用を避ける設計です。バックテスト時は target_date を明示的に渡してください。
- OpenAI 呼び出し部分
  - news_nlp と regime_detector は OpenAI を利用する箇所があり、API 呼び出しはリトライや JSON 検証の保護があります。ユニットテスト時は内部の _call_openai_api をモックすることが想定されています。
- J-Quants API
  - レートリミット（120 req/min）に合わせた RateLimiter とトークン自動リフレッシュを持ちます。get_id_token は settings.jquants_refresh_token を使用します。
- DuckDB バージョン差異
  - 一部実装は DuckDB の executemany / 型バインドの挙動に配慮しています（空の executemany を回避する等）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み / Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント解析 / score_news
    - regime_detector.py — 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py           — ETL 実行（run_daily_etl など）と ETLResult
    - etl.py                — ETLResult エイリアス
    - news_collector.py     — RSS 収集・前処理
    - calendar_management.py— カレンダーと営業日ロジック
    - quality.py            — データ品質チェック
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - audit.py              — 監査ログテーブル DDL と初期化
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Volatility / Value の計算
    - feature_exploration.py— 将来リターン・IC・統計サマリー・ランク化
  - ai の他、strategy / execution / monitoring 等のトップレベルエクスポートプレースホルダ（__all__ に記載）

開発・テスト
- ユニットテスト時は外部 API 呼び出し（OpenAI / J-Quants / ネットワーク）をモックしてください。
- news_nlp._call_openai_api や regime_detector._call_openai_api、jquants_client._request、news_collector._urlopen などは差し替え可能に設計されています。

貢献
- バグ報告、機能提案、テスト追加は歓迎します。CI / Lint / type checking の導入を推奨します。

以上。必要であれば README に含める具体的なサンプルスクリプト、依存関係の完全なリスト、または運用チェックリスト（cron / systemd ユニットの例など）を追加で作成します。どの情報を詳しく追記しますか？