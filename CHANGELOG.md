# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買システム「KabuSys」のコアモジュールを実装しました。

### 追加
- パッケージ基礎
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を定義。

- 環境設定 / config
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS 環境変数を保護する protected キーセットを用意し、上書き制御をサポート。
  - .env 行パーサーの改善:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のエスケープ処理対応。
    - クォート無しでのインラインコメント判定（直前が空白/タブの場合に '#' をコメント扱い）。
    - 無効行（空行・コメント・不正書式）は無視。
  - Settings クラスを提供（settings インスタンスをエクスポート）。主な設定:
    - J-Quants / kabuステーション / LINE Messaging / DB パス（DuckDB/SQLite）/ 監視設定（pid, kill flag, 閾値）/システム設定（env, log_level 等）。
    - 必須環境変数未設定時は ValueError を送出する _require() を実装。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）。
    - LOG_LEVEL のバリデーション。

- AI モジュール（kabusys.ai）
  - news_nlp
    - raw_news と news_symbols を元に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）を使って銘柄ごとのセンチメント（ai_score）を計算・ai_scores テーブルへ保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換済み）をサポート。calc_news_window ユーティリティを提供。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）とトークン肥大化対策（1銘柄あたり最大記事数・最大文字数でトリム）。
    - OpenAI 呼び出しは JSON Mode を利用し、レスポンスの厳密なバリデーションを実施（JSON 抽出、results フォーマット、コード照合、数値チェック）。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。非リトライエラーはスキップして処理継続（フェイルセーフ）。
    - DB 書き込みは冪等性を確保（対象コードのみ DELETE → INSERT）し、部分失敗時に既存データを保護。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - regime_detector
    - ETF 1321（TOPIX連動）を用いた市場レジーム判定モジュールを追加。
    - 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で算出。
    - マクロニュース抽出はマクロキーワードベース（デフォルトキーワード群を実装）。
    - OpenAI（gpt-4o-mini）を用いてマクロセンチメントを -1.0〜1.0 のスコアで取得。API エラー時は 0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアの合成と閾値判定（BULL_THRESHOLD / BEAR_THRESHOLD）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。例外発生時は ROLLBACK を試行。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- 研究用モジュール（kabusys.research）
  - factor_research
    - モメンタム、バリュー、ボラティリティ等の定量ファクター計算を実装。
    - calc_momentum(conn, target_date)：1M/3M/6M リターン、ma200_dev（200日 MA 乖離）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date)：20日 ATR（単純平均）・相対 ATR（atr_pct）・平均売買代金・出来高比率等を計算。データ不足時は None。
    - calc_value(conn, target_date)：raw_financials から最新財務を取得し PER（EPS が 0/null の場合は None）・ROE を計算。
    - 設計上、全て DuckDB の prices_daily / raw_financials テーブルのみを参照し、外部 API には依存しない。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None)：指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンのバリデーションあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：Spearman（ランク相関）に基づく IC を実装（重複・None を除外、十分なレコード数がなければ None）。
    - rank(values)：同順位は平均ランクを与えるランク化ユーティリティ（浮動小数誤差に対して round を使用）。
    - factor_summary(records, columns)：count/mean/std/min/max/median の基本統計量計算。
  - research パッケージは zscore_normalize（kabusys.data.stats から）、calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank をエクスポート。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダー管理ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得の際は曜日ベース（土日非営業）でのフォールバックを行う。DB 登録がある場合は DB 値を優先。
    - 最大探索日数上限（_MAX_SEARCH_DAYS）で無限ループ防止。
    - calendar_update_job(conn, lookahead_days=90)：J-Quants API から差分取得して market_calendar テーブルを更新（バックフィル・健全性チェックあり）。
  - ETL パイプライン
    - pipeline モジュールに ETL の結果を表す ETLResult dataclass を実装（取得・保存数、品質問題、エラーの一覧、ユーティリティ to_dict）。
    - ETL の設計方針に沿った差分取得/バックフィル/品質チェック用の構成を反映（実行ロジックの下地）。
  - etl パッケージは pipeline.ETLResult を再エクスポート。

### 変更
- （初回リリースのため変更履歴はありません）

### 破壊的な変更
- なし

### 修正
- （初回リリースのため修正履歴はありません）

### セキュリティ
- （初回リリースのため特記事項なし）

---

注記（設計上の重要ポイント）
- ルックアヘッドバイアス回避のため、全ての「日付基準」処理は内部で datetime.today() / date.today() を参照せず、呼び出し側が target_date を渡す設計になっています。
- OpenAI 呼び出しは JSON Mode を利用しつつ、レスポンスの堅牢なパース／バリデーションを行い、API 障害時はフェイルセーフで継続する方針です（システム安定性優先）。
- DuckDB を主要な内部 DB として想定しており、埋め込み SQL と Python の組合せで処理を実装しています。
- .env 自動ロードはプロジェクトルートの検出に依存します（配布後・テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。

今後の予定（例）
- strategy / execution / monitoring の詳細実装を追加（本リリースでは API とユーティリティに注力）。
- テストカバレッジの拡充、CI の整備、OpenAI 呼び出しの抽象化やレート制御の強化。