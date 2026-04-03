# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォームとリサーチ／自動売買基盤のプロトタイプです。J-Quants や RSS、OpenAI（LLM）などを組み合わせ、データ収集（ETL）、品質チェック、ファクター計算、ニュースセンチメント評価、マーケットレジーム判定、監査ログ（トレーサビリティ）を提供します。

## 主な特徴
- J-Quants API 経由の差分 ETL（株価・財務・市場カレンダー）
- DuckDB ベースのローカルデータストア保存（冪等保存）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュースの収集と LLM による銘柄別センチメント算出（gpt-4o-mini を使用想定）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログテーブル一式の初期化・運用（シグナル→発注→約定のトレーサビリティ）
- 安全性設計（Look-ahead バイアス回避、SSRF 対策、API レート・リトライ制御）

## 機能一覧（モジュール単位）
- kabusys.config
  - 環境変数の読み込み（.env、.env.local、OS 環境変数）と Settings クラス
  - 自動ロードの抑止: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- kabusys.data
  - etl / pipeline: run_daily_etl や個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート管理）
  - news_collector: RSS からの記事取得・前処理・raw_news 保存（SSRF・XML 安全対策）
  - calendar_management: JPX カレンダー管理と営業日ユーティリティ
  - quality: データ品質チェック（QualityIssue を返す）
  - audit: 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp: ニュースを LLM に投げて銘柄別センチメント（ai_scores）を作成
  - regime_detector: ETF 1321 の MA とマクロニュースで市場レジーム判定（market_regime）
- kabusys.research
  - factor_research: momentum, value, volatility 等の定量ファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリ等

## 必要条件
- Python 3.10+
- 必要ライブラリ（代表例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード、OpenAI API）

依存はプロジェクトの setup/pyproject に合わせてインストールしてください。ローカルでの最小実行例:
pip install duckdb openai defusedxml

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時）
- KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
- KABU_API_BASE_URL: kabu API のベース URL（既定: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（既定: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH 等：監視設定
- KABUSYS_ENV: environment ("development" / "paper_trading" / "live")
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml がある場所）を基準に .env → .env.local の順で読み込みます。
- OS 環境変数が優先され、.env.local は上書きされます。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## セットアップ手順（ローカル開発）
1. レポジトリをクローン
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install -r requirements.txt
   - または最低限: pip install duckdb openai defusedxml
4. .env を作成（.env.example を参考に）
   - 必須: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY（LLM を使う場合）
5. パッケージを開発モードでインストール（任意）
   - pip install -e .

## 基本的な使い方（コード例）
- 環境設定を読み込み、設定を参照する:
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env)

- DuckDB 接続を作って ETL を実行:
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントスコア（ai_scores）算出:
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を使用
  print("書き込んだ銘柄数:", n)

- 市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB の初期化:
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db(settings.duckdb_path)  # ":memory:" も可

- ファクター計算・リサーチ:
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  recs = calc_momentum(conn, target_date=date(2026, 3, 20))

※ 実行時は settings（環境変数）が正しく設定されていることを確認してください。

## 実運用での注意点
- OpenAI / J-Quants の API キーは漏洩しないよう管理してください。
- J-Quants API はレート制限（120 req/min）を考慮しています。jquants_client にレート制御が組み込まれていますが、大規模呼び出しは注意してください。
- ニュース取得は外部 HTTP に依存します。SSRF 対策やレスポンスサイズ上限など安全策が実装されていますが、プロダクション構成での監視が必要です。
- DuckDB や各種テーブルスキーマは変更に注意してください（互換性問題）。

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py (バージョン情報)
- config.py (環境変数・Settings)
- ai/
  - __init__.py
  - news_nlp.py         (ニュース NLU / LLM 呼び出し、ai_scores 書き込み)
  - regime_detector.py  (市場レジーム判定)
- data/
  - __init__.py
  - pipeline.py         (ETL パイプライン、run_daily_etl など)
  - etl.py              (ETLResult の再エクスポート)
  - jquants_client.py   (J-Quants API クライアント・保存関数)
  - news_collector.py   (RSS 収集・前処理)
  - calendar_management.py (市場カレンダー管理)
  - quality.py          (データ品質チェック)
  - stats.py            (zscore_normalize など)
  - audit.py            (監査ログスキーマ初期化)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記以外に strategy / execution / monitoring 等がパッケージ公開対象として示されていますが、コードベースの今回抜粋では data / ai / research を中心に実装されています）

## ロギングと環境
- LOG_LEVEL 環境変数でログレベルを制御（デフォルト INFO）
- KABUSYS_ENV: development / paper_trading / live のいずれか（デフォルト development）
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われます

## 開発者向けメモ
- Look-ahead バイアス防止を重視して設計されています（関数内で datetime.today() を参照しない等）。
- OpenAI 呼び出しは JSON mode を使用し、レスポンス検証・リトライを行います。テスト容易性のため _call_openai_api をモックできます。
- DuckDB への書き込みは基本的に冪等（ON CONFLICT）を使用します。
- news_collector は defusedxml を使い XML 攻撃を防ぎ、SSRF 対策を備えています。

---

問題の報告や機能追加の提案は Issue を立ててください。README の内容はコードの抜粋に基づく要約です。実際のプロジェクトでは pyproject.toml / requirements ファイル・.env.example を合わせて確認してください。