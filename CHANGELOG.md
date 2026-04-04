# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買プラットフォームのコアライブラリを収録します。主要なモジュールはデータ取得・ETL、マーケットカレンダー、リサーチ用ファクター計算、AI を用いたニュース NLP、環境設定ユーティリティなどです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）を追加。
  - パブリック API として data / strategy / execution / monitoring を __all__ に定義（将来モジュールの公開を想定）。

- 環境設定（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - .env パーサの堅牢化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理対応、インラインコメント処理（クォート外のみ）。
    - 無効行のスキップ、読み込み失敗時の警告出力。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを導入し、以下の設定プロパティを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）
    - 監視関連（PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値）
    - 環境判定（KABUSYS_ENV: development/paper_trading/live）と LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev の補助プロパティ
  - 必須環境変数未設定時に ValueError を投げる _require 実装。

- データモジュール（kabusys.data）
  - ETL / パイプライン基盤（pipeline.py / etl.py）
    - ETLResult データクラスを提供（取得件数、保存件数、品質問題、エラー集約）。
    - 差分取得・バックフィル・品質チェック方針を反映する設計（ドキュメント記載）。
  - マーケットカレンダー管理（calendar_management.py）
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがない場合は曜日ベース（土日）でフォールバックする一貫した動作。
    - 夜間バッチで J-Quants から差分取得して保存する calendar_update_job（バックフィル・サニティチェック含む）。
    - 最大探索日数やバックフィル日数等の安全策を実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（news_nlp.py）
    - raw_news / news_symbols を用いて銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode でバッチ評価して ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ、記事/文字数の上限、リトライ（429/ネットワーク/5xx）を考慮した堅牢な API 呼び出し実装。
    - レスポンスのバリデーション（JSON 抽出、results フォーマット検証、コード整合性チェック、スコアの数値化・有限性チェック、±1.0 でクリップ）。
    - 部分失敗に備え、書き込みは該当コードのみ DELETE→INSERT で置換（部分失敗時に既存データを保護）。
  - レジーム判定（regime_detector.py）
    - ETF 1321（日経225 連動）200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成し日次で market_regime を更新。
    - マクロ記事抽出はキーワードベースで raw_news からタイトルを取得し、OpenAI によりマクロセンチメントを JSON で取得。
    - 失敗フェイルセーフ（API 失敗時は macro_sentiment=0.0 として継続）、冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - Look-ahead バイアス防止（target_date 未満のデータのみ使用）を徹底。

- リサーチ（kabusys.research）
  - factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER / ROE）ファクターを DuckDB クエリベースで実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の挙動や NULL 処理を明示。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部依存を持たず標準ライブラリと DuckDB のみで動作する設計。

- そのほか
  - data.etl から ETLResult を再エクスポート（kabusys.data.etl）。
  - 各所で DuckDB を前提とした SQL 実装と安全策（executemany 空リスト回避、ROW_NUMBER を使った最新財務取得など）を導入。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- API キー等の取り扱いは Settings 経由で環境変数を参照する設計。OpenAI キー未設定時は明示的に ValueError を送出して安全に失敗させる。

### Notes / Requirements / マイグレーション
- 必要な環境変数（主なもの）
  - OPENAI_API_KEY: News/Regime の LLM 呼び出しに必須（score_news/score_regime は未設定時 ValueError を送出）。
  - JQUANTS_REFRESH_TOKEN: J-Quants API 連携に必須（settings.jquants_refresh_token）。
  - KABU_API_PASSWORD: kabu ステーション API のパスワード。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定すると .env 自動ロードを無効化。
- 想定 DB テーブル（DuckDB）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などが前提。
  - ETL / calendar_update_job / score_news / score_regime はこれらテーブルの存在を前提に動作する。
- Look-ahead バイアス対策として、全ての「日付ベース処理」は target_date を明示的に受け取り、今日の日付関数を直接参照しない設計になっています。
- 初期リリースでは一部 __all__ に列挙したモジュール（strategy / execution / monitoring 等）が存在する想定だが、実装内容は順次追加される予定です。

---

今後のリリースでは以下を想定しています:
- strategy/ execution の実注文・バックテスト実装
- 監視・実行プロセスの監視モジュール追加
- より詳細な品質チェック結果の UI/出力強化

もし CHANGELOG に特定のコミットやチケット番号を含めたい場合は、該当情報を提供してください。