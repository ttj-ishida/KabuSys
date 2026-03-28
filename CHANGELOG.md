# Keep a Changelog — CHANGELOG.md

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています: https://semver.org/

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース

### Added
- 基本パッケージとバージョン情報
  - pakage: kabusys、バージョン `0.1.0` を追加。

- 環境設定管理 (kabusys.config)
  - .env および環境変数から設定を読み込む自動ローダーを追加（優先順位: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
  - .env パーサの実装: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理等をサポート。
  - 必須環境変数取得関数 `_require`、および Settings クラスを提供。
  - Settings で下記の設定を参照可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）の JSON Mode を用い銘柄ごとのセンチメント（ai_score）を算出する `score_news` を実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を考慮した UTC naive のウィンドウ計算（calc_news_window）。
  - バッチ処理: 最大 20 銘柄ずつ API へ送信、1銘柄あたり最大記事数/文字数でトリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
  - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
  - レスポンス検証: JSONの堅牢なパース、"results" フォーマット検証、未知コードや非数値を無視、スコアを ±1.0 にクリップ。
  - データベース書き込みは冪等性を考慮（DELETE → INSERT を実行）し、部分失敗時に既存スコアを保護。
  - テスト容易性: OpenAI呼び出し部分を internal 関数で分離しモック可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出する `score_regime` を実装。
  - マクロニュース抽出はキーワードベース（日本・米国等のマクロ語彙リスト）。
  - OpenAI の呼び出しに対するリトライ・フェイルセーフ実装（API エラー時は macro_sentiment=0.0 として継続）。
  - レジーム結果は DuckDB の market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）、例外発生時は ROLLBACK を試行。
  - テスト容易性: ニュース評価用の OpenAI 呼び出しは独立実装（モジュール結合を避ける）。

- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理機能を追加。
    - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB に market_calendar が存在しない場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - カレンダーの夜間差分更新 job（calendar_update_job）を実装。J-Quants クライアント経由で取得 → 保存（バックフィル・健全性チェック含む）。
  - pipeline: ETL パイプライン用のインターフェースを提供。
    - ETLResult dataclass を追加（取得数・保存数・品質チェック結果・エラー一覧を保持、to_dict を提供）。
    - ETL の差分取得／バックフィル／品質チェックの設計に沿ったユーティリティを用意（jquants_client / quality との連携を前提）。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200日MA乖離を計算。
    - ボラティリティ（calc_volatility）: 20日 ATR、相対ATR、平均売買代金、出来高比率を計算。
    - バリュー（calc_value）: PER・ROE を raw_financials と prices_daily から計算（未実装項目は注記あり）。
    - DuckDB を用いた SQL＋Python 実装、欠損・データ不足時の None ハンドリング。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンの fwd リターンを一括 SQL で取得。
    - IC（calc_ic）: スピアマンのランク相関を計算（欠損・同順位処理を考慮）。
    - ランク（rank）ユーティリティ: 同順位は平均ランク方式で処理。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
  - research パッケージの __all__ に主要関数を再エクスポート。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

補足（設計・実装上の重要ポイント）
- ルックアヘッドバイアス回避: date.today()/datetime.today() を主要処理で参照しない実装方針を維持（target_date を明示的に受け取る）。
- OpenAI 呼び出しまわりは JSON Mode を利用し、レスポンス妥当性検査・堅牢なエラーハンドリング（リトライ・フォールバック）を実装。
- DuckDB 互換性に配慮した実装（executemany の空リスト回避、日付型変換ユーティリティ等）。
- DB 書き込みは可能な限り冪等化（DELETE→INSERT、トランザクション）し、例外時は ROLLBACK を試行して安全性を確保。
- テスト容易性: OpenAI 呼び出し箇所は内部関数で切り出し、ユニットテストでモック可能。

（今後のリリース案）
- ai_scores や market_regime のスキーマ説明、jquants_client の実装／モック、ETL 実行シーケンスの CLI 化や監視ジョブの追加などを予定。