# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このリポジトリの初回公開リリースを以下に記載します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-09
初期リリース。自動売買システム KabuSys のコア機能群を実装。

### Added
- 全般
  - パッケージ初版を追加（src/kabusys）。バージョンは 0.1.0。
  - パッケージのエクスポート定義（__all__）を設定。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数からの設定読み込みを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を起点）により、CWD に依存しない .env 自動ロードを実現。
  - .env/.env.local の読み込み優先順位を実装（OS 環境変数 > .env.local > .env）。
  - override/protected による上書き制御（OS 環境変数の保護）。
  - export KEY=val 形式やクォート・インラインコメントの扱いに対応した .env パーサを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能（テスト向け）。
  - 必須キー取得用の _require と各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE 関連、DB パス、監視閾値、env/log_level 等）。
  - Paper Trading 向け設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）を実装。PAPER_FILL_MODE の妥当性検証あり。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 銘柄選定関数 select_candidates（スコア降順、signal_rank によるタイブレーク）。
  - 等配分 calc_equal_weights とスコア加重 calc_score_weights（全スコアが 0 の場合は等配分にフォールバックして WARNING ログ）。
  - セクター集中防止 apply_sector_cap（既存保有比率が閾値を超えるセクターの新規候補除外。unknown セクターは除外対象外）。
  - レジーム乗数 calc_regime_multiplier（bull/neutral/bear に基づく投下資金乗数、未知レジームは 1.0 でフォールバック）。
  - 銘柄ごとの株数決定 calc_position_sizes（risk_based / equal / score の割当手法、単元株丸め、per-stock 上限、aggregate cap、cost_buffer を考慮したスケーリングと残差分配処理）。
  - 将来的拡張に備えた lot_size/lot_map の注記。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - ファクター計算モジュール（factor_research.py）
    - モメンタム: 1M/3M/6M リターン、200 日移動平均乖離（MA200）。データ不足時は None を返す。
    - ボラティリティ/流動性: 20 日 ATR, ATR 比率, 20 日平均売買代金, 出来高変化率。true_range の NULL 伝播を厳密に扱う実装。
    - バリュー: raw_financials と prices_daily を結合して PER・ROE を計算（EPS 欠損/0 の場合は None）。
  - 特徴量探索モジュール（feature_exploration.py）
    - 将来リターン calc_forward_returns（複数ホライズン一括取得、horizons の検証）。
    - IC（Information Coefficient）calc_ic（スピアマンのランク相関、十分なサンプルがなければ None）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸めによる ties 対応）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
  - research パッケージは zscore_normalize など外部ユーティリティを再エクスポート。

- AI 関連（src/kabusys/ai/*）
  - ニュース NLP（news_nlp.py）
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄毎センチメントスコアを計算。
    - タイムウィンドウの計算（JST ベース → UTC 変換）を実装（ルックアヘッドバイアス回避のため datetime.today() を使用しない）。
    - 最大記事数・最大文字数でトリムするバッチ処理、1 バッチ最大 20 コード、スコアは ±1.0 にクリップ。
    - OpenAI 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx に対して指数バックオフ）、API レスポンスの JSON バリデーション（部分的に余計なテキストが混入した場合の復元ロジック含む）。
    - DuckDB（ai_scores テーブル）へ冪等的に書き込む処理（DELETE→INSERT、部分失敗時に他コードを保護）。
    - テストのため _call_openai_api を差し替え可能に実装。
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
    - マクロ記事抽出はキーワードベース（複数キーワード）でタイトルを取得し、LLM でスコア化。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - レジームスコア合成と閾値判定、market_regime テーブルへの冪等書き込みを実装。
    - news_nlp の calc_news_window を利用して時間窓計算を共有。OpenAI 呼び出し関数はモジュール内で独立実装（モジュール結合防止）。

- モニタリング永続化（src/kabusys/monitoring/monitoring_db.py）
  - SQLite を用いた監視ログ永続化層を実装（init_monitoring_db）。以下のテーブル作成（冪等）をサポート:
    - system_status（CPU/メモリ/ディスク/プロセス状態）
    - trade_logs（発注ログ）
    - positions（保有ポジション）
    - risk_logs（リスク関連ログ、実装途中の可能性あり）
    - インデックスを含むスキーマ作成スクリプトを提供。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは明示的な引数または環境変数 OPENAI_API_KEY から取得し、未設定時は ValueError を発生させる仕様を明示（誤って公開しない運用を促す）。

注意:
- DuckDB / SQLite のスキーマ・テーブル名（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）に依存する実装が多数あるため、実行前に想定スキーマとデータの準備が必要です。
- OpenAI 連携部分は外部 API に依存するため、API レスポンスの変化により挙動が影響される可能性があります。ユニットテストでは外部呼び出し箇所を差し替え可能に設計されています。

--- 

今後のリリースで追加予定（例）
- 銘柄別 lot_size をサポートするためのマスタデータ連携
- より詳細なエラーメトリクスと監視アラート機能
- research モジュールの追加ファクター、PBR・配当利回り対応
- テストカバレッジの拡充と CI/CD 用の設定ファイル

（以上）