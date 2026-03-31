# KabuSys

日本株向けのデータ基盤・リサーチ・簡易自動売買補助ライブラリです。  
J-Quants API / RSS / OpenAI（LLM）などからデータを取得・加工し、DuckDB に格納して研究・シグナル生成・監査ログ保存までをカバーします。

主な用途
- J-Quants からの日次株価・財務・カレンダー ETL
- RSS ニュース収集と銘柄ごとの LLM ベースセンチメント算出
- マーケットレジーム判定（ETF の MA と LLM マクロセンチメントの合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- データ品質チェック・監査ログ（発注→約定トレーサビリティ）用ユーティリティ

---

## 機能一覧（抜粋）

- 環境設定管理
  - .env ファイル自動読み込み（プロジェクトルートを探索）
  - 必須環境変数チェックとデフォルト値管理

- データ取得 / ETL
  - J-Quants からの daily quotes / financial statements / market calendar 取得（ページネーション対応・レート制御・リトライ）
  - 差分更新（最終取得日からの自動算出・バックフィル）
  - ETL 結果を表す ETLResult

- データ品質（quality）
  - 欠損検出、前日比スパイク検出、重複、日付整合性チェック
  - run_all_checks でまとめて実行

- ニュース関連（news_collector / news_nlp）
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去）
  - ニュースの前処理・記事ID生成・raw_news への冪等挿入想定
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（score_news）

- レジーム判定（regime_detector）
  - ETF（1321）200日移動平均乖離 + マクロニュース LLM スコアを合成して market_regime を日次で書き込み

- 研究（research）
  - モメンタム / ボラティリティ / バリュー ファクター計算
  - forward returns, IC（Spearman）、ファクター統計サマリ
  - z-score 正規化ユーティリティ（data.stats）

- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義・初期化
  - init_audit_db で DuckDB を作成してスキーマ適用（UTC タイムゾーン固定）

---

## セットアップ手順

事前に Python 3.9+ を用意してください（型ヒントの union 省略表記などを使用）。

1. リポジトリをクローン（例）
   - git clone … && cd your-repo

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - requirements.txt が用意されている想定の場合:
     - pip install -r requirements.txt
   - 主な依存（本コードから参照）:
     - duckdb
     - openai
     - defusedxml
   - または開発時:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に自動で `.env` / `.env.local` が読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime 等で必要）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（注文周り）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 監視通知等で使う場合

   その他のオプション変数（デフォルト値あり）
   - KABUSYS_ENV (development | paper_trading | live) — default: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
   - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
   - DUCKDB_PATH — default: data/kabusys.duckdb
   - SQLITE_PATH — default: data/monitoring.db
   - PID_FILE_PATH — default: data/execution.pid
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値

   tip: settings オブジェクトで参照できます。
   - from kabusys.config import settings

---

## 使い方（代表例）

以下は簡単な Python スニペット例です（実行前に環境変数を設定してください）。

- DuckDB 接続準備（デフォルトパスを使用）
  - from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
    from datetime import date
    res = run_daily_etl(conn, target_date=date(2026,3,20))
    print(res.to_dict())

- ニュースのセンチメントスコア算出（score_news）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n_written = score_news(conn, target_date=date(2026,3,20))
    print("scored:", n_written)

- マーケットレジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, target_date=date(2026,3,20))

- 監査 DB 初期化（監査ログ専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
    # audit_conn を使って監査テーブルへ書き込み等を行う

- ファクター計算（研究用）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    from datetime import date
    mom = calc_momentum(conn, date(2026,3,20))
    val = calc_value(conn, date(2026,3,20))
    vol = calc_volatility(conn, date(2026,3,20))

- ETL の結果や品質チェック確認
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date(2026,3,20))
    for i in issues: print(i)

- RSS フィード取得（ニュース収集テスト）
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    for a in articles: print(a["title"], a["datetime"])

注意点
- AI モジュール（score_news / score_regime）は OpenAI API キー（OPENAI_API_KEY）または引数 api_key の指定が必須です。
- LLM 呼び出しは失敗時にフォールバック（スコア 0.0）する実装が多く、例外を全体に飛ばさないケースがあります。ログを確認してください。
- DuckDB の executemany に空リストを渡すと失敗する点に注意（モジュール内で対策済み）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（.env 自動読み込み等）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM ベースセンチメント算出（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limiting）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py — ETLResult 再エクスポート
  - news_collector.py — RSS 収集（SSRF対策・前処理）
  - quality.py — データ品質チェック
  - stats.py — z-score 正規化等統計ユーティリティ
  - calendar_management.py — 市場カレンダー管理（営業日判定・update job）
  - audit.py — 監査ログ（スキーマ定義・初期化）
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — forward returns / IC / factor summary
- research/*, ai/*, data/* でテスト可能な独立関数単位で設計されています。

---

## 開発・運用上の留意点

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml の存在）を基準に .env / .env.local を読み込みます。
  - テストなどで自動読み込みを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Look-ahead バイアス対策
  - AI・ETL・ファクター計算の多くは date 引数を外から与える方式で、内部で datetime.today() を直接参照しない設計になっています。バックテスト用途に配慮しています。

- 冪等性
  - J-Quants 保存処理、news の保存、監査テーブル作成等は冪等性を考慮（ON CONFLICT 等）しています。

- ロギング
  - モジュールごとに logger を利用しています。LOG_LEVEL 環境変数で制御してください。

---

## よくある操作（まとめ）

- ETL 実行（本番）
  1. 環境変数を設定（JQUANTS_REFRESH_TOKEN 等）
  2. python スクリプト / cron で run_daily_etl を実行

- LLM スコア実行
  - OPENAI_API_KEY を環境変数で設定 → score_news / score_regime を呼ぶ

- 監査ログ初期化
  - init_audit_db("path/to/audit.duckdb")

---

必要であれば、README に以下を追加できます：
- 開発用の requirements.txt（候補パッケージ一覧）
- .env.example（推奨のキー一覧テンプレート）
- より詳細な API 使用例（SQL スキーマ定義、期待するテーブル構造）
- CI / テストの実行例

追加してほしい項目があれば指示してください。