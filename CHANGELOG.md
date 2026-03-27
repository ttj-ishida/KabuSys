Keep a Changelog に準拠した CHANGELOG.md（日本語）
全ての重要な変更履歴をこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。

## [Unreleased]
- ドキュメント・設定の微調整や追加検討項目（将来のリリース候補）。

## [0.1.0] - 2026-03-27
初期リリース。以下の主要機能と実装が含まれます。

### Added
- パッケージ基盤
  - kabusys パッケージの初版を追加。公開 API として data, strategy, execution, monitoring を __all__ に定義。
  - バージョンを __version__ = "0.1.0" として設定。

- 設定・環境読み込み
  - 環境変数/設定管理モジュールを追加（kabusys.config）。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み機能を実装。
  - 読み込み順序: OS環境変数 > .env.local (override) > .env（override の保護キー機能あり）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env パース機能を高精度に実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント取り扱いの制御）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベースパス / 実行環境・ログレベル等のプロパティを公開。
  - 必須環境変数未設定時は ValueError を送出する _require を実装。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値を限定）および is_live/is_paper/is_dev ヘルパーを提供。

- データプラットフォーム（DataLayer）
  - ETL パイプラインインターフェース: ETLResult データクラスを追加（kabusys.data.pipeline）。
    - ETL の取得件数/保存件数、品質チェック結果、エラーの集約をサポート。
    - has_errors / has_quality_errors / to_dict を実装。
  - カレンダー管理（kabusys.data.calendar_management）:
    - market_calendar を用いた営業日判定 API を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job により J-Quants から差分取得して冪等に保存（バックフィル、健全性チェックを組込）。
    - 最大探索日数・先読み・バックフィル等のパラメータを定義して安全に動作するように設計。

- 研究モジュール（Research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対ATR(atr_pct)、20日平均売買代金、出来高比を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を算出（EPS が 0 または欠損時は None）。
    - 全関数は DuckDB を用いた SQL ベースで実装し、外部 API にアクセスしない。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定 horizon に対応する将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）を実装。3 銘柄未満なら None を返す。
    - rank: 平均ランク方式（同順位は平均ランク）を実装（丸めで ties の漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーを提供。
  - zscore_normalize は kabusys.data.stats から再エクスポート。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - score_news: raw_news と news_symbols を集約して銘柄ごとのニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を取得し ai_scores テーブルへ書き込む。
    - ニュース収集ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換済）を計算する calc_news_window を提供。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1 銘柄あたりの記事数と文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装。
    - OpenAI 呼び出しのリトライ／エクスポネンシャルバックオフ（429, ネットワーク断, タイムアウト, 5xx を対象）。
    - レスポンスの堅牢なバリデーション（JSON の抽出、results キー検証、コード照合、数値チェック、スコアの ±1.0 クリップ）。
    - DuckDB の executemany の制約に配慮して部分的な DELETE→INSERT ロジックで冪等性を確保（失敗時に他銘柄の既存スコアを保護）。
    - テスト容易性のため _call_openai_api を差し替え可能に実装（unittest.mock.patch を想定）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime: ETF 1321（日経225連動型）の 200 日移動平均乖離とマクロセンチメント（LLM）を重み付け合成（MA 70% / Macro 30%）して日次の market_regime を算出・保存。
    - MA 計算は target_date 未満のデータのみ使用してルックアヘッドを防止。
    - マクロニュースは raw_news からキーワードフィルタで抽出（キーワードリストを内包）。
    - LLM 呼び出しはリトライとフェイルセーフ（API失敗時は macro_sentiment=0.0）を備える。
    - レジームスコアのクリップ、ラベリング（bull/neutral/bear）および DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して不正使用を防止。

### Notes / Implementation Decisions
- ルックアヘッドバイアス対策: 日付の基準に datetime.today()/date.today() を参照しない実装方針を採用（各関数は target_date を引数で受ける）。
- DuckDB を主要なローカルデータストアとして使用し、SQL と Python を併用して高性能な集計を行う。
- 外部依存を最小化（研究モジュールは pandas 等に依存しない）し、テストの差し替えポイントを意図的に設置。
- ロギングと警告を多用して動作異常の早期検出を補助。
- DB 書き込み時はトランザクション（BEGIN/COMMIT/ROLLBACK）で整合性を確保。ROLLBACK 失敗時の警告ログも出力。

---

今後のリリースで検討する項目（例）
- strategy / execution / monitoring の具体的な実装・テストケース追加
- ai モジュールのモデル選択やプロンプトの改善、評価メトリクス導入
- ETL のスケジューラ統合、監視（Alerting）機能
- CI 上での DuckDB を用いた統合テスト整備
- ドキュメント（API リファレンス、運用ガイド）充実

（以上）