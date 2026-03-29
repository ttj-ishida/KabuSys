# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュース収集、AIによるニュースセンチメント評価、ファクター計算・リサーチユーティリティ、監査ログ（オーダー/約定トレーサビリティ）などの機能を含みます。

## 概要（Project Overview）
KabuSys は以下を目的とした内部向けライブラリです。

- J-Quants API からの差分取得（株価・財務・マーケットカレンダー）と DuckDB への冪等保存
- RSS ベースのニュース収集と前処理（SSRF・サイズ制限等の安全対策付き）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / マクロレジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ等）と研究用ユーティリティ（forward returns, IC, summary）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（信号 → 発注 → 約定のトレーサビリティ）
- 設定管理（環境変数 / .env 自動読み込み）

設計上の方針として、バックテストやモデル検証におけるルックアヘッドバイアスを避けるため、内部実装は明示的な target_date を受け取り、datetime.today()/date.today() を暗黙的に参照しないようになっています。

---

## 主な機能（Features）
- ETL パイプライン（kabusys.data.pipeline.run_daily_etl）
  - 市場カレンダー、株価日足、財務データの差分取得・保存・品質チェック
- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（refresh token → id token）、ページネーション、レートリミット、リトライ
  - save_* 関数により DuckDB へ冪等保存
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、ID（SHA-256）、前処理、SSRF 対策、保存前のチャンク処理
- AI スコアリング（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA やマクロニュースの LLM 評価を合成して市場レジームを判定
  - 冗長な API 失敗時にはフォールバック（例: macro_sentiment=0.0）するフェイルセーフ
- リサーチ（kabusys.research）
  - calc_momentum / calc_value / calc_volatility 等のファクター計算
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（クロスセクション正規化）
- データ品質（kabusys.data.quality）
  - 欠損 / 重複 / スパイク / 日付不整合チェック
  - QualityIssue を返し、ETL 側で収集・ログ出力可能
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブル定義および初期化ユーティリティ
- 設定管理（kabusys.config）
  - OS 環境変数 / .env / .env.local の読み込み（プロジェクトルートは .git / pyproject.toml で探索）
  - 必須キーの取得ラッパー（settings オブジェクト）

---

## 動作要件（Requirements）
- Python 3.10 以上（コード内で `|` 型注釈などを使用）
- 主な依存パッケージ（少なくとも以下が必要）
  - duckdb
  - openai
  - defusedxml
- その他は標準ライブラリで実装されています。

（プロジェクトに requirements.txt / pyproject.toml があればそちらを優先してください）

---

## セットアップ手順（Setup）
1. リポジトリをクローン
   - git clone ... (省略)

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - 例（最低限）:
     - pip install duckdb openai defusedxml

   - またはプロジェクトの manifest に従って:
     - pip install -r requirements.txt
     - または poetry / pipx 等を使用

4. 環境変数を用意
   - プロジェクトルートに .env（または .env.local）を作成します。config モジュールは自動で .env をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN=...   （必須）
     - KABU_API_PASSWORD=...       （kabuステーション連携用）
     - SLACK_BOT_TOKEN=...         （Slack 通知用）
     - SLACK_CHANNEL_ID=...       （Slack 通知用）
     - OPENAI_API_KEY=...         （AI スコアリング用。score_news / score_regime の api_key 引数でも指定可）
     - DUCKDB_PATH=data/kabusys.duckdb  （省略可）
     - SQLITE_PATH=data/monitoring.db   （省略可）
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - LOG_LEVEL=INFO|DEBUG|...   （デフォルト: INFO）

   - 例 .env:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

5. 必要に応じてデータディレクトリを作成
   - mkdir -p data

---

## 使い方（Examples / Usage）

以下は Python REPL やスクリプトから利用する例です。target_date などは明示的に与えることでルックアヘッドバイアスを回避します。

- 設定値の参照
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.is_live など

- DuckDB 接続（ファイル）
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- news_nlp（銘柄ごとのニューススコア）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20), api_key="sk-xxx")  # api_key None の場合は OPENAI_API_KEY 環境変数を使用
  - print(f"scored {n} symbols")

- regime_detector（市場レジーム判定）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20), api_key=None)

- ファクター計算 / リサーチ
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  - momentum = calc_momentum(conn, date(2026,3,20))
  - forward = calc_forward_returns(conn, date(2026,3,20))
  - ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")

- 監査ログ DB 初期化（監査用に別 DB を使う場合）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- データ品質チェック
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026,3,20))
  - for i in issues: print(i)

注意点:
- OpenAI API 呼び出しは gpt-4o-mini（JSON mode）を前提としたプロンプト設計になっています。レスポンスのフォーマットを厳格に期待しています。
- score_news/score_regime は API エラー時のフォールバック・リトライロジックを持ちますが、API キーが未設定の場合は ValueError を送出します。
- ETL と品質チェックは個別ステップで例外を捕捉して続行する設計です。ETLResult に errors / quality_issues が集約されます。

---

## .env 自動読み込みの挙動
- 自動読み込み条件:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていない（未設定 / 0 の場合有効）
  - パッケージの __file__ を起点に親ディレクトリで .git または pyproject.toml を発見したら、そのディレクトリをプロジェクトルートと見なす
- 読み込み優先順位:
  - OS 環境変数 > .env.local > .env
- .env のパースは一般的なシェル形式（export KEY=val、引用符、コメントの扱いなど）に対応しています。

---

## ディレクトリ構成（Directory Structure）
（主要なファイル・モジュールの概要）

- src/kabusys/
  - __init__.py  — パッケージ初期化、バージョン定義
  - config.py  — 環境変数 / .env 管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py  — ニュースを LLM に投げて銘柄別スコアを ai_scores テーブルへ保存
    - regime_detector.py  — ETF MA とマクロニュースを合成して market_regime を算出
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - etl.py  — ETLResult の再エクスポート
    - news_collector.py  — RSS 収集・前処理・保存ロジック
    - calendar_management.py  — 市場カレンダー管理・営業日判定・更新ジョブ
    - quality.py  — データ品質チェック（各種）
    - stats.py  — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py  — 監査ログスキーマ定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  — モメンタム / バリュー / ボラティリティファクター計算
    - feature_exploration.py  — forward returns / IC / summary / rank
  - monitoring/ (パッケージに含まれる想定の監視関連モジュールなど ※実装状況による)

---

## 運用上の注意（Operational Notes）
- API レート制限、リトライ、フェイルセーフの設計をしていますが、運用環境でのスロットリングやコストに注意してください（OpenAI / J-Quants の利用料・レート制限）。
- 本リポジトリ内の関数は多くが明示的な target_date を要求します。自動化ジョブではジョブ実行時点の「営業日」に調整して ETL を実行することを推奨します（pipeline.run_daily_etl は calendar_etl 実行後に営業日に補正します）。
- 監査ログ（audit）を利用する場合は init_audit_db / init_audit_schema でスキーマを作成してください。監査テーブルは削除せず累積保存する前提です。

---

## 補足
- ライセンスや貢献ルール、CI 等はリポジトリのトップ（LICENSE, CONTRIBUTING, .github/workflows 等）を参照してください（本 README には含めていません）。
- 追加のユーティリティや CLI、メトリクス連携（Prometheus / CloudWatch 等）は本パッケージ外で実装する想定です。

---

必要であれば、README に以下を追記できます：
- 実行スクリプトの例（systemd / cron / airflow / kubernetes cronjob）
- さらに詳しい API 使用例（J-Quants / OpenAI のレスポンス例）
- データベーススキーマ（CREATE TABLE 定義の抜粋）  
どの情報をより詳しく載せたいか教えてください。