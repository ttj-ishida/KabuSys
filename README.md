# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants や各種ニュースソースからデータを取り込み、ETL、品質チェック、ニュースセンチメント評価、マーケットレジーム判定、ファクター計算、監査ログ（オーディット）などを行うコンポーネント群を提供します。

主に研究（research）、データパイプライン（data）、AI を使ったニュース解析（ai）、および実行監視や設定（config）を含む設計です。

---

## 特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分で取得・永続化
  - 差分取得・バックフィル・ページネーション対応、レート制限管理、トークン自動リフレッシュ
- データ品質管理
  - 欠損、重複、スパイク（急騰・急落）、日付不整合の検出（QualityIssue）
  - run_all_checks による一括チェック
- ニュース収集 / 前処理
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、サイズ上限）
  - raw_news / news_symbols への冪等保存（ID は正規化 URL のハッシュ）
- ニュース NLP（OpenAI）
  - 銘柄毎のニュースをまとめて LLM（gpt-4o-mini）でセンチメント評価して ai_scores に保存（バッチ処理・リトライ）
  - マクロニュースを扱うレジーム判定（ETF 1321 の MA200 と LLM センチメントの混合）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査テーブルを DuckDB に冪等初期化
  - order_request_id を冪等キーとして二重発注を防止
- 設定管理
  - .env ファイル（.env.local 優先）および環境変数から設定読み込み、自動ロード機能
  - 各種しきい値（CPU/MEM/DISK）や DB パスの設定を提供

---

## 必要条件

- Python 3.10 以上（型注釈に「|」構文を使用）
- 主な依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- ネット接続（J-Quants / OpenAI / RSS フィードへのアクセス）

具体的な依存関係はプロジェクトの packaging / requirements ファイルに合わせてください。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   - 例:
     - git clone <repo>
     - cd <repo>
     - pip install -e ".[dev]"  # 実際の extras 名はプロジェクト側に合わせてください
     - あるいは最低限: pip install duckdb openai defusedxml

2. Python のバージョン確認
   - Python >= 3.10 を使用してください（3.11 推奨）。

3. 環境変数 / .env の準備
   - プロジェクトルート（pyproject.toml または .git があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
     - KABU_API_PASSWORD: kabu ステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を使う場合）
   - デフォルトの DB パスは以下:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db

   - .env 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. DuckDB ファイルの準備
   - デフォルトでは data/ 配下を想定します。必要ならディレクトリを作成してください（多くの初期化関数が自動生成します）。

---

## 使い方（簡単な例）

- 共通準備: DuckDB 接続の取得
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")  # ":memory:" も可能
  ```

- ETL（日次パイプライン）の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # today を対象に ETL 実行
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai.news_nlp.score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI キーを明示的に渡すか、環境変数 OPENAI_API_KEY を設定する
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログスキーマ初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # データベースを初期化して接続を返す
  ```

- 研究用関数例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
  from kabusys.data.stats import zscore_normalize

  target = date(2026, 3, 20)
  momentum = calc_momentum(conn, target)
  volatility = calc_volatility(conn, target)
  value = calc_value(conn, target)

  # forward returns
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

  # IC 計算（例）
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)       # Path オブジェクト
  print(settings.kabu_api_base_url) # デフォルトは http://localhost:18080/kabusapi
  ```

---

## 実装上の注意点 / 設計方針（抜粋）

- Look-ahead bias を防ぐ設計:
  - 多くのモジュール（news_nlp、regime_detector、pipeline 等）は内部で date.today() を直接参照せず、呼び出し元が target_date を渡す方式。
  - データ取得や処理は「target_date を基準に過去ウィンドウのみ参照」するように実装されています。
- 冪等性:
  - ETL 保存関数（save_daily_quotes など）は ON CONFLICT を使い冪等にデータを更新。
- フェイルセーフ:
  - LLM 呼び出しや外部 API の一部が失敗しても例外を上位へあげず、スコアを 0.0 にフォールバックする等の挙動で継続する設計（ただし重大な DB 書き込み失敗は例外を伝播）。
- セキュリティ配慮:
  - RSS 収集は SSRF 対策（ホスト/リダイレクト先検証）、defusedxml を使用して XML 脆弱性に対応。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下の主要モジュール）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースを LLM でスコアリング、ai_scores への書込み
    - regime_detector.py   — マクロ＋ETF MA200 から市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得 & DuckDB 保存）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult 再エクスポート
    - news_collector.py    — RSS 収集と前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py           — 品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py             — 統計ユーティリティ（zscore_normalize）
    - audit.py             — 監査ログテーブル初期化（signal / order / execution）
  - research/
    - __init__.py
    - factor_research.py   — Momentum / Value / Volatility 等の計算
    - feature_exploration.py — 将来リターン / IC / summary
  - ai、data、research モジュールは相互に依存しますが、LLM 呼び出しの抽象化や DB 操作は明確に分離されています。

---

## トラブルシューティング / よくある質問

- .env の自動読み込みが動作しない
  - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して決定されます。テスト環境やパッケージ配布後は期待通り検出されない場合があります。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、明示的に環境変数を設定してください。
- OpenAI API 呼び出しの失敗
  - ネットワークエラーや RateLimit、5xx はリトライ・バックオフします。最終的に失敗した場合はスコアを 0 にフォールバックする設計です。API キーは環境変数 `OPENAI_API_KEY` または各関数の `api_key` 引数で渡してください。
- DuckDB の executemany が空リストでエラーになる
  - 一部 DuckDB バージョンでは executemany に空リストを渡せない処理があり、コード中で予め空チェックを行っています。もしエラーが出る場合は DuckDB のバージョンを確認してください。

---

README は主要な使い方・設定と内部モジュールの要約を示しています。詳細な API（各関数の引数・戻り値・例外）については、該当モジュールの docstring（ソース内コメント）を参照してください。必要であれば README に追加の使用例や CI / デプロイ手順も作成できます。