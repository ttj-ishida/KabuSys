# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータストアとして利用し、J-Quants API からの ETL、ニュース収集と NLP による銘柄センチメント評価、マーケットレジーム判定、ファクター計算やデータ品質チェック、監査ログ（発注・約定トレーサビリティ）など、研究〜運用に必要な主要機能を提供します。

---

## 主な特徴 (Features)

- データ取得 / ETL
  - J-Quants API からの株価日足 / 財務データ / 上場・カレンダー情報の差分取得と DuckDB への冪等保存
  - 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質管理
  - 欠損、スパイク、重複、日付不整合などの品質チェック（QualityIssue レポート）
- ニュース収集・前処理
  - RSS から記事取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策などの堅牢な収集処理
- ニュース NLP / AI
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント算出（score_news）
  - マクロニュース + ETF 200 日移動平均乖離を組み合わせた市場レジーム判定（score_regime）
  - API 呼び出しに対するリトライやフェイルセーフ設計
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル群で戦略→発注→約定のトレーサビリティを保証
  - 監査 DB 初期化ユーティリティを提供

---

## セットアップ手順

前提:
- Python 3.10+（型アノテーションに PEP 604 等を使用）
- ネットワークアクセス（J-Quants API / OpenAI 等）

1. リポジトリをクローンしてインストール（編集モード推奨）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e ".[dev]"  # 必要な依存を extras で分けている場合
   ```
   ※ 実際のパッケージ配布設定に応じて requirements を確認してください。主な依存例:
   - duckdb
   - openai
   - defusedxml

2. 環境変数 / .env の準備  
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   主に必要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須、ETL に使用）
   - OPENAI_API_KEY: OpenAI API キー（AI 関連処理に必要）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注連携する場合）
   - LOG_LEVEL, KABUSYS_ENV（development / paper_trading / live）など（任意）
   - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH などはデフォルト値を使用可能

3. データベース用ディレクトリの作成（必要に応じて）
   デフォルトの DuckDB ファイルは `data/kabusys.duckdb` です。自動で親ディレクトリが作成されるユーティリティもいくつかありますが、適宜ディレクトリ権限を確認してください。

---

## 使い方（簡易ガイド）

以下は代表的な利用パターンの例です。実行は Python スクリプト / Jupyter Notebook 等から行います。

- 共通設定オブジェクト
  ```python
  from kabusys.config import settings
  # settings.jquants_refresh_token などで環境変数にアクセスできる
  ```

- DuckDB 接続を開いて日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

  ETL では市場カレンダー → 株価 → 財務 → 品質チェックの順で処理され、ETLResult オブジェクトが返ります。

- ニュースセンチメントを算出して ai_scores に保存する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

  注意: OPENAI_API_KEY が環境変数に設定されている必要があります（引数 api_key に明示的に渡すことも可）。

- マーケットレジームを判定して market_regime テーブルへ保存する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（監査 DB）の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/monitoring_audit.duckdb")
  # conn_audit に対して発注ログ等を記録するためのテーブルが作成される
  ```

- 研究用ユーティリティの利用例
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  res = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- ニュース収集（RSS フェッチ） — 取得結果は NewsArticle 型
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```
  fetch_rss は SSRF ガード・サイズ制限・XML の安全パーサーを使用しています。RSS の保存ロジックはプロジェクトの ETL / 保存層と組み合わせて利用してください。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN (必須: ETL 用)
- OPENAI_API_KEY (AI モジュール利用時に必要)
- KABU_API_PASSWORD (kabu ステーション連携時)
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB など)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます

.env ファイルの読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を起点に行われ、.env → .env.local の順に読み込まれます（.env.local が優先され上書きします）。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュールとファイルの概観（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（ai_scores 生成）
    - regime_detector.py      — 市場レジーム判定（ma200 + マクロセンチメント）
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py       — J-Quants API クライアント & DuckDB 保存ロジック
    - news_collector.py       — RSS 収集・前処理（SSRF 対策等）
    - calendar_management.py  — 市場カレンダー管理・営業日判定
    - etl.py                  — ETLResult の再エクスポート
    - stats.py                — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログ（テーブル作成 / 初期化）
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 等
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー

（上記は主要ファイルのみ抜粋しています。プロジェクト全体は src/kabusys 以下にモジュール群が格納されています。）

---

## 注意点 / 設計方針（重要）

- Look-ahead Bias 対策:
  - 各 AI / 研究関数は内部で datetime.today() を直接参照せず、target_date を明示的に受け取る設計です。バックテストや日次処理では target_date を明示してください。
- 冪等性:
  - J-Quants から取得したデータは DuckDB へ ON CONFLICT DO UPDATE/DELETE を使って冪等に保存します。
- フェイルセーフ:
  - OpenAI や外部 API の一時的失敗時はリトライやフォールバック（例: マクロセンチメント 0.0）を行い、パイプライン全体の停止を避ける設計です。ただし重大エラーや設定不足（API キー未設定等）は例外になります。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査 / プライベート IP 拒否）や XML パーサのハードニング（defusedxml）を実装しています。
- DuckDB の互換性:
  - 一部処理では DuckDB の executemany の挙動や型バインドの挙動に配慮した実装があります（空リストの executemany 回避など）。

---

## よくある利用例（チェックリスト）

- ETL を自動化する際は JQUANTS_REFRESH_TOKEN が正しく設定されているか確認する。
- AI 関連処理を実行する前に OPENAI_API_KEY をセットする。
- 本番口座での発注連携を行う場合は KABUSYS_ENV を `live` に設定し、発注前に十分なテストを行う。
- 監査ログを有効にするには init_audit_db で監査用 DB を初期化してから利用する。

---

これで README の概要は以上です。必要であれば以下を追加で作成できます:
- .env.example のテンプレート
- より詳細な API リファレンス（各関数の引数例）
- デプロイ / Systemd / Supervisor 用の実行例スクリプト
- テスト実行方法とモックのガイダンス

どれを追加しますか？