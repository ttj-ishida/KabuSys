CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは「Keep a Changelog」規約に準拠し、セマンティック バージョニングを採用します。

## [Unreleased]

（無し）

## [0.1.0] - 2026-03-29

初回リリース。

### Added
- パッケージ骨格を追加
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - 主要サブパッケージを __all__ に公開: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local 自動ロード機能（プロジェクトルートを .git または pyproject.toml から特定）
  - export KEY=val 形式やクォート・エスケープ・インラインコメントに対応する .env パーサ実装
  - OS 環境変数保護（読み込み時に既存の OS 環境変数を保持する protected 機能）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須環境変数チェック用 _require と Settings クラスを提供
  - 設定項目（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルト値あり）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（値検証あり）
  - Settings の利便性プロパティ: is_live / is_paper / is_dev

- AI ツール群
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとにテキストを構築し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_scores）を生成
    - 時間ウィンドウ計算（JST基準 → UTC変換）を提供する calc_news_window
    - チャンク処理、1チャンク最大銘柄数（デフォルト20）やトークン肥大化対策（記事数・文字数制限）
    - 再試行（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装
    - JSONレスポンスの堅牢なバリデーションと復元ロジック（余分な前後テキストの除去）
    - DuckDB への冪等的書き込み（DELETE → INSERT、executemany 対応）
    - 公開 API: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定
    - MA 計算時にルックアヘッドを防止（target_date 未満のみ使用）
    - マクロニュース抽出（タイトルベースのキーワードフィルタ）
    - OpenAI 呼び出し（gpt-4o-mini）とリトライ・フォールバック（失敗時 macro_sentiment=0.0）
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - 公開 API: score_regime(conn, target_date, api_key=None)

- Research（因子・特徴量） (src/kabusys/research/)
  - factor_research.py: モメンタム / ボラティリティ / バリューファクターの計算
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日データ不足時は None）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（データ不足時は None）
    - calc_value: per, roe（raw_financials から最新財務を取得）
  - feature_exploration.py: 特徴量探索ユーティリティ
    - calc_forward_returns: 複数ホライズンの将来リターンを一括計算（範囲バッファあり）
    - calc_ic: スピアマンのランク相関 (IC) を計算（null/不足レコード処理）
    - factor_summary: 各列の基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクを返すランク化実装（丸めによる ties 対策）
  - research パッケージで主要関数を再エクスポート（使いやすく公開）

- Data プラットフォーム（src/kabusys/data/）
  - calendar_management.py
    - 市場カレンダー管理 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
    - market_calendar が未取得でも曜日ベースのフォールバックを提供
    - calendar_update_job: J-Quants から差分取得 → 保存（バックフィル・健全性チェックを含む）
  - pipeline.py / etl.py
    - ETLResult データクラス（ETL 実行結果の集約、品質問題とエラーの集計）
    - 差分取得、バックフィル、品質チェックの設計方針を反映した ETL ユーティリティ（パイプラインの骨格）
    - データベース最大日付取得ユーティリティ等を含む
    - data.etl で ETLResult を再エクスポート

- テスト容易性を考慮した設計
  - OpenAI 呼び出し部分をモジュール内の private 関数として分離しており、unittest.mock.patch で差し替え可能
  - 設定読み込みの自動化は環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）

### Changed
- （初回リリースのため該当なし）

### Fixed
- フェイルセーフなフォールバックを多く実装
  - OpenAI API 呼び出し失敗時は局所的にフォールバック（例: macro_sentiment=0.0、該当チャンクはスキップ）して処理を継続
  - データ不足時の既定値（例: ma200_ratio=1.0）や None の扱いを明示
  - DuckDB executemany に対する互換性対策（空リストバインド回避）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種シークレットは必須チェックを実装（score_news / score_regime は API キー未設定時に ValueError を送出）
- .env ロード時に既存の OS 環境変数を保護する機構を追加（意図しない上書きを防止）

Notes / 利用上の注意
- 必要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OPENAI_API_KEY は AI 関連関数を利用する際に必須
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。CWD には依存しません。
- AI モジュールは gpt-4o-mini と JSON mode を前提に設計されています。レスポンスの安定性に依存する部分は復元処理やリトライで対処していますが、API バージョン差分に注意してください。
- 時刻処理はルックアヘッドバイアス回避のため、score_* 系関数内部で datetime.today()/date.today() を参照せず、明示的な target_date を必ず与える設計です。
- DuckDB 周りの互換性（executemany の空リスト等）に配慮した実装になっています。

作者・貢献
- 初回実装（機能追加）：開発者による一括導入

（以上）