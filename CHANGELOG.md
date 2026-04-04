# Changelog

すべての注記は Keep a Changelog の方針に準拠します。  
このファイルは、提供されたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

全般
- 初期実装リリース v0.1.0（初期機能群の追加）
- パッケージ名: kabusys
- 内部的に DuckDB を主要なローカルデータストアとして利用
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定の統合
- 設計方針として「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」「テスト容易性」を明確に採用

## [0.1.0] - 2026-04-04

### Added
- 基本パッケージ・公開 API
  - パッケージメタ情報（src/kabusys/__init__.py）を追加。公開サブパッケージ: data, strategy, execution, monitoring（エントリ一覧）。
  - バージョン: 0.1.0

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサ実装: コメント、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いに対応。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境（development/paper_trading/live） / ログレベル検証等をプロパティ経由で取得可能。
  - 必須環境変数チェック（_require）で未設定時に ValueError を送出。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を入力に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を使ってセンチメントを取得。
  - タイムウィンドウ計算: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換する calc_news_window() を実装。
  - バッチ処理: 最大 20 銘柄 / API コール（_BATCH_SIZE）。
  - 1 銘柄あたり記事上限・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - API 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ）。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results リストの検証、コード正規化、スコア数値検査）。
  - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に（DELETE→INSERT）書き込む。部分失敗時に他銘柄データを保護する実装。
  - テスト容易性: _call_openai_api の差し替え（patch）を想定。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）の直近 200 日 MA 乖離とマクロニュース（LLM センチメント）を組み合わせて日次レジームを判定。
  - 重みづけ: MA (70%) / マクロ (30%)、スケーリング・クリッピングにより最終スコアを -1.0〜1.0 に制限。
  - 閾値: bull / bear 判定は ±0.2。
  - マクロニュース抽出は _MACRO_KEYWORDS に基づき raw_news からタイトルを取得。
  - OpenAI 呼び出しは JSON mode を使い再試行ロジックを実装。API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
  - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック処理を実装。
  - ルックアヘッドバイアス回避: date 引数ベースで過去データのみ参照。API キー注入可能。

- リサーチモジュール（src/kabusys/research/*）
  - factor_research.py
    - モメンタム: mom_1m / mom_3m / mom_6m、200 日 MA 乖離（ma200_dev）。
    - ボラティリティ・流動性: 20日 ATR（atr_20）、atr_pct、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - バリュー: PER（price/EPS, EPS が 0 または欠損のとき None）、ROE（raw_financials から取得）。
    - DuckDB 上の SQL ウィンドウ関数を活用した実装。
    - データ不足時の None 処理・ログ出力。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: デフォルト horizons=[1,5,21]、horizons のバリデーション、1クエリで複数ホライズン取得。
    - IC 計算（calc_ic）: スピアマン相関（ランク相関）を自前で計算（ties の平均ランク対応）。
    - ランク関数（rank）: 同順位は平均ランク、浮動小数の丸め対策を実装。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - research/__init__.py で主要関数を再エクスポート。

- データプラットフォーム（src/kabusys/data/*）
  - calendar_management.py
    - market_calendar を基に営業日判定ロジック提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベース（週末）でフォールバックする一貫した振る舞い。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を冪等的に保存。バックフィル・健全性チェックを実装。
  - pipeline.py / etl.py
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー情報を格納）。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を想定したパイプライン設計。
    - id_token 等の注入でテスト容易性を確保。
  - etl.py は pipeline.ETLResult を再エクスポート。

- テスト・運用配慮
  - 多くの箇所でテスト時に差し替え可能なフックを設置（例: _call_openai_api の patch、_sleep_fn の注入、api_key 引数）。
  - DuckDB の executemany に関する互換性考慮（空リストチェック）など実装互換性への配慮。

### Changed
- （初回リリース）設計上の決定や方針をコード内ドキュメントとして明示。
  - ルックアヘッドバイアスの防止方針を全 AI / 研究処理で徹底。
  - DB 操作は可能な限り冪等に（DELETE→INSERT / ON CONFLICT を想定）実装。

### Fixed
- （実装内の堅牢化）
  - OpenAI API レスポンスのパース失敗や API エラー時に例外を上位に伝えずフェイルセーフで継続する箇所を整備（警告ログ出力、デフォルト値の採用）。
  - .env 読み込み失敗時の警告と失敗耐性を実装。

### Security
- 機密情報（API キー等）は Settings にて環境変数から取得する設計。デフォルトで .env 自動読み込みが有効だが、テスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

### Known limitations / Notes
- 一部モジュール（例: jquants_client）の実体は今回のスニペットに含まれていないため、外部 API クライアント実装に依存する。
- strategy / execution / monitoring の具体的な実装は本差分に含まれていない（__all__ で公開予定のサブパッケージ名のみ）。
- AI モデルは現状 gpt-4o-mini を指定。将来的なモデル差し替えは _MODEL 定数を変更することで可能。
- DuckDB バージョン依存（executemany の空リスト等）に配慮した実装が行われているが、動作確認は実行環境で行う必要あり。

貢献者
- 初期実装 (推測に基づく記載)

（以上）