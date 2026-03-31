# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムのコアライブラリを公開します。主にデータ基盤、研究（ファクター計算）、AI ベースのニュースセンチメント、環境設定ユーティリティを含みます。

### Added
- パッケージ初期化
  - kabusys.__init__ によるバージョン情報と主要サブパッケージの公開（data, strategy, execution, monitoring）。
- 環境設定 / ロード
  - kabusys.config
    - .env / .env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env 行パーサ（コメント、export 形式、クォート内のエスケープ対応）。
    - Settings クラスを提供（J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / 環境フラグ等の取得）。
    - 必須環境変数未設定時の明確な ValueError。
- AI（自然言語処理）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を用いた銘柄別ニュース集約。
    - OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価（JSON Mode）。
    - バッチ処理（最大 20 銘柄／回）、記事数・文字数トリム、リトライ（429/ネットワーク/5xx）、レスポンス検証、スコアの ±1.0 クリップ。
    - calc_news_window(target_date) によるニュース収集ウィンドウ計算（JST→UTC 変換）。
    - score_news(conn, target_date, api_key=None): ai_scores テーブルへの安全な置換書き込み（DELETE → INSERT、トランザクション）。
    - テスト容易性のため OpenAI 呼び出し関数は差し替え可能。
  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価、リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）。
    - _calc_ma200_ratio / _fetch_macro_news / _score_macro / score_regime を提供。market_regime テーブルへ冪等書き込み。
    - ルックアヘッドバイアス回避（date を明示的に渡す設計）。
- データ基盤（DuckDB ベース）
  - kabusys.data.calendar_management
    - JPX カレンダー管理（market_calendar）。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days といった営業日ユーティリティ。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・保存処理（健全性チェック付き）。
    - DB データがまばらな場合の曜日ベースフォールバック実装。
  - kabusys.data.pipeline / kabusys.data.etl
    - ETLResult データクラス（ETL 実行結果の集約・シリアライズ用）。
    - 差分取得・保存・品質チェックを想定した ETL パイプラインの骨組み（jquants_client / quality モジュールと連携する設計）。
    - ETL の設計方針やバックフィル挙動、品質問題の扱い（Fail-Fast 非採用）を文書化。
- 研究（ファクター計算・特徴量探索）
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
    - calc_value: raw_financials と prices_daily を用いて PER / ROE を計算（EPS が 0/欠損なら None）。
    - 全関数は DuckDB の prices_daily/raw_financials のみ参照する設計（外部発注 API にはアクセスしない）。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用）。
    - calc_ic: ファクター列と将来リターンのスピアマンランク相関（IC）を計算（3 銘柄未満は None）。
    - rank: 同順位は平均ランクとするランク変換（丸めて ties を防止）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを算出。
- 共通設計・実装上の注意点（ドキュメント化）
  - ルックアヘッドバイアス防止のため、各種関数は内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - OpenAI 呼び出しはリトライとフォールバック（失敗時に例外を上位へ投げない、代替値で継続）に配慮。
  - DuckDB 0.10 の挙動（executemany に空リストを渡せない等）を考慮した実装。
  - 外部 API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY を参照する挙動。
  - ロギングを各モジュールで積極的に行い、警告やデバッグ情報を出力。

### Changed
- （該当なし）初回公開のため変更履歴はありません。

### Fixed
- （該当なし）初回公開のため修正項目はありません。

### Security
- OpenAI API キー等の秘密情報は Settings 経由で環境変数から取得する想定。.env の自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Migration / Requirements
- 必須環境変数:
  - OPENAI_API_KEY（AI 機能を利用する場合）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（対応機能使用時）
- DB スキーマ（DuckDB）:
  - modules は prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のテーブルを前提に実装されています。実行前にスキーマを準備してください。
- .env 自動ロード:
  - プロジェクトルートの検出はソースファイル位置を基に行うため、配布後の動作にも配慮しています。CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨します。
- テスト可能性:
  - OpenAI 呼び出し箇所はモック差し替え可能（各モジュール内の _call_openai_api を patch することでシミュレーション可能）。

---

今後の予定（例）
- strategy / execution / monitoring の具体的な実装（注文発注ロジック・監視アラート連携）
- jquants_client の詳細実装と ETL の具体的な実行フロー
- ユニットテスト・統合テストの追加、CI ワークフロー整備

（必要があれば、この CHANGELOG にリリースノートの追記・日付修正を行います。）