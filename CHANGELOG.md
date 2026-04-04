# CHANGELOG

すべての変更は「Keep a Changelog」形式に従って記載しています。  
初期リリース v0.1.0 の内容をソースコードから推測してまとめています。

v0.1.0 - 2026-04-04
-------------------

### Added
- 初回公開: KabuSys 日本株自動売買システムの基盤機能群を追加。
  - パッケージ情報
    - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
    - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に設定。

  - 設定・環境変数管理 (`kabusys.config`)
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（読み込み順: OS 環境 > .env.local > .env）。
    - プロジェクトルートを .git または pyproject.toml を基準に探索する実装（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env 行パーサー `_parse_env_line` を実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの取り扱い等）。
    - `_load_env_file` は既存 OS 環境変数を保護する protected セットをサポートし、override 挙動を制御。
    - 必須設定取得ヘルパ `_require` と Settings クラスを実装。主要プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
      - DUCKDB_PATH, SQLITE_PATH
      - PID/KILL フラグ関連パスと監視閾値（CPU/MEM/DISK）
      - KABUSYS_ENV 検証（development, paper_trading, live）と LOG_LEVEL 検証
      - is_live, is_paper, is_dev のユーティリティプロパティ

  - AI モジュール (`kabusys.ai`)
    - ニュースセンチメント: `kabusys.ai.news_nlp.score_news`
      - 前日 15:00 JST ～ 当日 08:30 JST を対象とするニュースウィンドウ計算 `calc_news_window` を実装（JST→UTC で DB 比較用の naive datetime を返す）。
      - raw_news と news_symbols を結合して銘柄ごとに最新記事を集約（1銘柄あたり最大記事数・文字数でトリム）。
      - OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄/チャンク）、JSON Mode を期待してレスポンスを検証・抽出。
      - レート制限/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ実装。部分失敗時に他銘柄データを保護するために書き込みは「対象コードのみ DELETE → INSERT」。
      - レスポンスバリデーション（JSON 抽出、results 配列、code/score の検証、スコアクリップ ±1.0）を実装。
      - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch 可能）。

    - 市場レジーム判定: `kabusys.ai.regime_detector.score_regime`
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
      - マクロニュース抽出はキーワードベース（日本・米国等のマクロ語彙セット）で raw_news のタイトルを取得。
      - OpenAI（gpt-4o-mini）へ JSON 出力を期待した呼び出し、API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
      - レジームスコアの合成、閾値に基づくラベル付け、market_regime テーブルへの冪等（BEGIN / DELETE / INSERT / COMMIT）保存を実装。
      - API 呼び出しはテスト用に差し替え可能に設計。

  - データ処理・ETL (`kabusys.data`)
    - カレンダー管理: `kabusys.data.calendar_management`
      - JPX カレンダーを扱うユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
      - market_calendar の有無に応じた DB 優先動作・未登録日は曜日ベースのフォールバック（週末除外）。
      - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止、カレンダー差分取得バッチ `calendar_update_job`（J-Quants クライアント呼び出し、バックフィル、健全性チェック）を実装。
    - ETL パイプライン: `kabusys.data.pipeline`
      - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー一覧・ユーティリティメソッド to_dict）。
      - 差分取得、保存（jquants_client の save_* を想定）、品質チェックの実装方針とヘルパを準備。
      - DuckDB 固有の挙動（executemany の空リスト回避など）に配慮した実装。
    - ETL の公開インターフェース `kabusys.data.etl` で ETLResult を再エクスポート。

  - 研究用ユーティリティ (`kabusys.research`)
    - ファクター計算: `kabusys.research.factor_research`
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）、データ不足時は None を返す。
      - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
      - calc_value: raw_financials から最新財務を参照して PER（EPS が 0/欠損時は None）、ROE を計算。
      - 実装は DuckDB の SQL ウィンドウ関数を活用し、外部 API 非依存で設計。
    - 特徴量探索: `kabusys.research.feature_exploration`
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一度に取得。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 件未満は None）。
      - rank: 同順位の平均ランク計算（round(..., 12) による安定性対策）。
      - factor_summary: 各ファクターに対する count/mean/std/min/max/median を計算。
    - research パッケージの __all__ に主要関数をエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 設定ロード時に OS 環境変数を上書きしないデフォルト挙動（protected set を使用）を採用。重要な環境変数の保護を意図。
- .env 読み込み失敗は warnings.warn で通知し、致命的にはしない（安全性重視）。

### Notes / 実装上の設計判断（重要）
- ルックアヘッドバイアス防止: AI スコアリング・レジーム判定・ETL・研究モジュールはいずれも内部で datetime.today()/date.today() に依存せず、外部から target_date を受け取る設計になっている。
- API 呼び出しは冪等性・部分失敗耐性を重視。DB 書き込みは「DELETE → INSERT（対象のみ）」あるいは ON CONFLICT を想定して既存データを不必要に消さない実装。
- OpenAI 呼び出しは JSON Mode を期待しつつ、実運用で混入し得る余計なテキストを復元するフォールバックや、各種例外（429/接続断/タイムアウト/5xx）のリトライ処理を備えている。
- DuckDB 特有の制約（executemany に空リストを渡せない等）に配慮した実装。
- テスト容易性のため、外部 API 呼び出し（OpenAI 呼出し）は内部関数を patch して差し替え可能。

### Breaking Changes
- （初回リリースのため該当なし）

もし特定の変更点（例: 個別ファイルの追加日や Issue/PR 番号）をCHANGELOGに含めたい場合は、該当情報を教えてください。上記は提供されたコードベースの内容から推測してまとめた初回リリース向けの変更履歴です。