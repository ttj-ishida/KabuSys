# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に準拠します。  

最新リリース: 0.1.0 — 2026-03-31

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買プラットフォームの初期実装を追加しました。主要な機能群はデータ取得/ETL、カレンダー管理、ファクター計算、AI によるニュース評価（LLM）、環境設定/起動設定などです。主な追加点を以下にまとめます。

### Added
- パッケージ初期化
  - kabusys パッケージの基本（src/kabusys/__init__.py）を追加。バージョンを "0.1.0" に設定し、公開サブパッケージを定義（data, strategy, execution, monitoring）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動ロード機能を追加（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装（export フォーマット、クォートされた値のエスケープ、インラインコメント処理、無効行スキップ等に対応）。
  - OS 環境変数を保護する protected set 機構（.env.local は上書きだが OS 環境変数は保護）。
  - Settings クラスを追加し、各種設定値をプロパティで取得可能：
    - J-Quants / kabuステーション / Slack の API トークン取得
    - DB パス（duckdb, sqlite）
    - 監視閾値（CPU/MEM/DISK）
    - 環境（KABUSYS_ENV）の検証（development / paper_trading / live）
    - ログレベルの検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

- AI モジュール（src/kabusys/ai）
  - news_nlp: ニュースを LLM（gpt-4o-mini）でセンチメント判定し ai_scores テーブルへ書き込む機能を実装。
    - score_news(conn, target_date, api_key=None) を提供。
    - JST 時間ウィンドウ計算（前日15:00〜当日08:30 JST）を行う calc_news_window を実装。
    - 記事集約、1銘柄あたりのトリム（記事数・文字数制限）、バッチ（最大20銘柄）での API 送信、JSON Mode 応答のバリデーション、スコアの ±1.0 クリップを実装。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフリトライと、フェイルセーフでのスキップ動作を実装。
    - レスポンス復元（前後ノイズが混入した場合に最外の {} を抽出）や型チェックを行い、安全に空の辞書を返すことで部分失敗を許容。

  - regime_detector: ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定を実行する score_regime(conn, target_date, api_key=None) を実装。
    - ma200_ratio（ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用）算出。
    - マクロキーワードによる raw_news フィルタリング（最大20件）と LLM による macro_sentiment 評価。
    - LLM 呼び出し時のリトライ（指数バックオフ）、API 失敗時の macro_sentiment=0.0 フォールバック。
    - レジームスコア合成（重み: MA70% / Macro30%）, クリップ、ラベル付与（bull / neutral / bear）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データモジュール（src/kabusys/data）
  - calendar_management: JPX カレンダー管理機能を追加。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar にデータがある場合は DB を優先、未登録日は曜日ベースのフォールバック（土日を休日扱い）。
    - calendar_update_job(conn, lookahead_days=_CALENDAR_LOOKAHEAD_DAYS) で J-Quants から差分取得・保存（バックフィル・健全性チェック含む）を実装。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル日数等の安全機構を導入。

  - pipeline / etl:
    - ETLResult dataclass を実装し ETL の実行結果（取得数、保存数、品質問題、エラー等）を構造化して返却。
    - ETL の方針（差分取得、backfill、品質チェック）に基づくインターフェースを整備。
    - data.etl で ETLResult を公開再エクスポート。

- research モジュール（src/kabusys/research）
  - factor_research:
    - calc_momentum(conn, target_date)：1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility(conn, target_date)：20日 ATR、相対 ATR（atr_pct）、平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date)：最新財務（raw_financials）との結合により PER, ROE を算出（EPS 0/欠損は None）。
    - すべて DuckDB の prices_daily / raw_financials を参照し、外部 API に依存しない設計。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None)：複数ホライズンの将来リターンを一度に取得可能（horizons 検証あり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：スピアマンのランク相関（IC）を計算（有効レコードが 3 件未満の場合は None）。
    - rank(values)：同順位は平均ランクで扱うランク化ユーティリティ。
    - factor_summary(records, columns)：count/mean/std/min/max/median を計算する統計サマリー。

- 内部設計方針の明示
  - ルックアヘッドバイアス防止のため、各スコアリング関数で datetime.today()/date.today() を直接参照しない実装方針をドキュメント化。
  - DuckDB を前提とした SQL と Python の併用、部分失敗を回避するための部分的な置換（DELETE → INSERT）戦略を採用。
  - OpenAI API 呼び出しはモジュール単位で独立実装としており、テスト時にモックで差し替えやすい構成に。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 環境変数周りで保護機構を導入：
  - OS 環境変数を protected set として .env による上書きを防止（意図しない上書きを回避）。
  - 必須設定（API キー等）が未設定の場合は明示的な ValueError を送出して早期発見を促進。

### Notes / Migration
- OpenAI API の使用には環境変数 OPENAI_API_KEY を設定するか、各関数の api_key 引数にキーを渡してください。未設定時は ValueError が発生します。
- 自動的な .env ロードはプロジェクトルート検出に依存します。CI / テスト等で自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が必要です。ETL および分析機能はこれらのテーブルを前提とします。
- news_nlp と regime_detector は LLM レスポンスの不整合や API 障害に対してフェイルセーフ動作（スコア 0.0 またはスキップ）を採用しています。運用時の挙動を理解のうえ利用してください。

---

今後のリリースでは、strategy / execution / monitoring などの発注・実行系、より詳細な品質チェック・監視機能、テストカバレッジ向上やドキュメント整備を計画しています。