Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティック バージョニングを使用します。

[0.1.0] - 2026-03-29
-------------------

初回リリース。

### Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定／環境変数管理
  - kabusys.config モジュールを追加。
  - .env / .env.local ファイルの自動ロード機能を実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理等）。
  - OS 環境変数を保護する protected 機能（.env の上書きを制御）。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level, is_live 等）をプロパティで取得。未設定時や不正値時は ValueError を送出。

- AI: ニュース NLP / レジーム判定
  - kabusys.ai.news_nlp: raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でバッチ評価して ai_scores テーブルへ書き込む機能を実装。
    - ニュースウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 に対応する UTC 範囲）。
    - バッチ処理（1回あたり最大 20 銘柄）、1銘柄あたり最大 10 記事・最大 3000 文字でトリム。
    - JSON Mode を期待したレスポンス検証・パース処理（余分な前後テキストの復元ロジック含む）。
    - 再試行（429/ネットワーク/タイムアウト/5xx）用の指数バックオフ実装。
    - スコアを ±1.0 にクリップ、失敗はフェイルセーフでスキップ。
    - DuckDB の executemany の制約を考慮した DELETE→INSERT の冪等書き込み。

  - kabusys.ai.regime_detector: ETF 1321（Nikkei225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ書き込む機能を実装。
    - ma200_ratio 計算、マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）での macro_sentiment 評価、重み付け合成、閾値判定、冪等 DB 書き込み。
    - API 失敗時のフォールバック（macro_sentiment=0.0）とリトライ（指数バックオフ）。
    - モジュール間の結合を避けるため OpenAI 呼び出し関数を独立実装（テスト容易性のため差し替え可）。

- Research（ファクター・特徴量探索）
  - kabusys.research パッケージを追加。calc_momentum / calc_value / calc_volatility / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank を公開。
  - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。データ不足時の None 処理。
  - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。入力データ不足時は None を返す設計。
  - calc_value: raw_financials の最終財務データと価格を組み合わせて PER / ROE を算出。
  - calc_forward_returns: 指定ホライズン（既定 [1,5,21]）の将来リターンを一括 SQL で取得。
  - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。レコード不足時は None。
  - rank / factor_summary: ランク付け（同位は平均ランク）と基本統計量計算を実装。
  - 実装は DuckDB / 標準ライブラリのみで pandas 等に依存しない。

- Data（カレンダー・ETL・パイプライン）
  - kabusys.data.calendar_management:
    - market_calendar を基にした is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB 未登録日は曜日ベースでフォールバック（週末除外）。最大探索日数による無限ループ防止。
    - calendar_update_job: J-Quants API から差分取得し冪等保存。バックフィル（直近 _BACKFILL_DAYS 日間）と健全性チェック（将来日付の異常検出）を実装。
  - kabusys.data.pipeline:
    - ETLResult dataclass を追加（取得件数・保存件数・品質チェック・エラー一覧などを保持、to_dict によるシリアライズ）。
    - ETL の差分更新方針、backfill、品質チェックポリシー等を文書化。
    - DuckDB のテーブル存在チェック / 最大日付取得ユーティリティを提供。
  - kabusys.data.etl: pipeline.ETLResult を再エクスポート。

- モジュール再エクスポート／API 整備
  - kabusys.ai.__init__ は score_news を公開。
  - kabusys.research.__init__ で主要関数を公開。

### Changed
- ログとエラーハンドリングの強化
  - 各処理で詳細な logger.info / logger.warning / logger.exception を追加し、失敗時の挙動（フォールバックや部分スキップ）を明確化。
  - DB 書き込み失敗時は ROLLBACK を試行し、ROLLBACK 自体の失敗を警告ログで通知。

- Lookahead バイアス防止
  - AI / Research / Pipeline の日付処理は内部で datetime.today() / date.today() を参照しない設計（外部から target_date を与えることでルックアヘッドを防止）。ただし一部（calendar_update_job）は運用上 date.today() を使用。

- DuckDB 互換性対応
  - DuckDB 0.10 系の executemany に関する制約を考慮した実装（空 params の場合は実行しない等）。

### Fixed
- .env パーサの堅牢化
  - export プレフィックス、クォート内バックスラッシュエスケープ、インラインコメントの取り扱いなどを正しく処理するよう修正（不正な行を無視し、空キーをフィルタリング）。

- OpenAI API 呼び出しの堅牢化
  - RateLimitError / APIConnectionError / APITimeoutError / 5xx に対するリトライ処理を追加。
  - APIError の status_code 不在ケースにも安全に対応。
  - JSON パース失敗時やレスポンス検証失敗時のフォールバック（0.0 やスキップ）を追加し、例外を上位に漏らさないフェイルセーフ動作を実装。

### Security
- 環境変数保護
  - .env 自動ロード時に既存 OS 環境変数を protected として扱い、.env による上書きを防止するデフォルト動作を導入。

### Documentation / Notes
- 各モジュールの docstring に処理フロー・設計方針・DB 前提を明記。
- OpenAI のモデルはデフォルトで gpt-4o-mini を使用するよう設定。
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY）は Settings プロパティ経由で取得し、未設定時に ValueError を発生させる。

### Breaking Changes
- 初回リリースのため breaking change はなし。

今後の予定
- strategy / execution / monitoring モジュールの実装・公開（パッケージ __all__ に名称を準備済み）。
- 単体テスト・統合テストの整備、CI ワークフローへの組み込み。
- J-Quants / kabu API クライアントの詳細実装および実運用向けの追加監視・アラート機能。