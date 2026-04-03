# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のパッケージバージョンは src/kabusys/__init__.py に定義された __version__ = "0.1.0" です。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買プラットフォームのコアライブラリを実装・公開。

### Added
- パッケージ基盤
  - kabusys パッケージの公開（__version__ = 0.1.0）。モジュール群: data, research, ai, execution, strategy, monitoring（__all__ に含む）。
- 設定 / 環境変数管理 (kabusys.config)
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索する _find_project_root を実装。
  - .env 自動読み込み機能（優先度: OS 環境変数 > .env.local > .env）。自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーの実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理など）。
  - .env 読み込み時の保護キー (protected) ロジック（OS環境変数を上書きしない）。
  - Settings クラスを公開し、J-Quants / kabu ステーション / LINE / DB / 監視設定 / システム設定をプロパティとして提供。必須キー未設定時の ValueError、KABUSYS_ENV / LOG_LEVEL の値検証を実装。
- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini, JSON Mode) で銘柄ごとのセンチメントを算出して ai_scores テーブルへ保存。
    - タイムウィンドウ計算 calc_news_window（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）。
    - バッチ処理（最大 20 銘柄／チャンク）、1 銘柄あたり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - API 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）、レスポンス検証（JSON 抽出・results 構造検証・スコアの数値チェック・±1.0 でクリップ）。
    - DuckDB への冪等書き込み（該当コードのみ DELETE → INSERT）。部分失敗時に既存データを保護する設計。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込み。
    - ma200_ratio 計算（target_date 未満のみ利用しルックアヘッドを防止）、マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（リトライ・フォールバック macro_sentiment=0.0）。
    - レジームラベル: bull / neutral / bear。
- データ関連 (kabusys.data)
  - calendar_management
    - JPX カレンダー管理ロジック（market_calendar テーブルの有無判定、is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装）。
    - DB にデータがない場合は土日ベースのフォールバックを行う。最大探索日数 (_MAX_SEARCH_DAYS) により無限ループ防止。
    - 夜間バッチ job calendar_update_job(conn, lookahead_days) を実装（J-Quants API から差分取得して保存、バックフィル、健全性チェック）。
  - ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー情報を保持、辞書変換をサポート）。
    - ETL の設計方針文書に基づく差分取得・保存・品質チェックの骨子を実装（jquants_client 経由の安全な保存、バックフィル、品質問題の集計）。
    - etl モジュールで ETLResult を再エクスポート。
- 研究用ユーティリティ (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m と ma200_dev（データ不足時は None）。
    - calc_volatility(conn, target_date): atr_20 / atr_pct / avg_turnover / volume_ratio（ウィンドウ不足時は None）。
    - calc_value(conn, target_date): PER / ROE（raw_financials の最新値を使用、EPS が 0 または欠損なら None）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns(conn, target_date, horizons=None): 複数ホライズンの将来リターン取得（入力検証あり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）計算（有効データ数が 3 未満なら None）。
    - rank(values): 同順位は平均ランクとするランク計算（丸め処理で ties の安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を算出。
  - research パッケージの公開 API を整備（主要関数を __all__ で公開）。
- 共通実装・設計方針
  - ルックアヘッドバイアス対策: 日付判断に datetime.today()/date.today() を直接参照しない設計（target_date ベースで計算）。
  - DuckDB を主要なデータ層として使用（関数は DuckDB 接続を受け取る形）。
  - OpenAI API 呼び出しは各モジュールで独立実装（モジュール間でプライベート関数を共有しない）。
  - ロギングとフォールバック戦略を多用し、API 失敗時はフェイルセーフ（例: スコアに 0 を使う、処理を継続）を採用。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。ただし各モジュールで次のような堅牢化を実施：
  - .env ファイル読み込み失敗時に警告を出して継続（例外を投げない）。
  - OpenAI レスポンスパース失敗や API エラーで例外を上位に波及させず、警告ログを出して安全側のデフォルトを使用（ニュース/レジームのフェイルセーフ）。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キー未設定時は ValueError を送出し明示的に失敗する箇所がある（score_news / score_regime）。運用時は環境変数 OPENAI_API_KEY または関数引数でキーを提供する必要あり。

---

既知の注意点 / 運用メモ
- 本ライブラリは DuckDB と外部 API（J-Quants、OpenAI）に依存します。ローカルでのテストではモックを利用してください（多くの箇所に unittest.mock.patch を想定した注記あり）。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後の利用環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を適切に設定するか、環境変数を明示的に設定してください。
- ai モジュールは OpenAI の JSON Mode を利用する想定です。モデル名や応答フォーマットの変更によりパースロジックの調整が必要になる可能性があります。

もし CHANGELOG に追記してほしい項目（例えばリリース日や追加で強調したい機能、既知のバグ/将来の改善予定）があれば教えてください。必要に応じてリリースノートを分割したり、英語版を生成したりできます。