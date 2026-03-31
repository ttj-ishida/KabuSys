# Changelog

すべての公開済み変更は Keep a Changelog の形式に従います。  
このファイルは、コードベース（src/kabusys 以下）の実装内容から推測して作成した初期の変更履歴です。

フォーマット:
- Unreleased: 今後の変更向け（現状は未記載）
- 各リリースは機能追加/変更/不具合修正などのセクションで要約

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-31
初期リリース — 日本株自動売買システムのコア機能群を実装。

### Added
- パッケージ基礎
  - パッケージ名: kabusys。公開モジュールとして data, strategy, execution, monitoring をエクスポート。
  - バージョン: 0.1.0

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定をロードする自動ロード機能を実装。
    - 読み込み順: OS 環境 > .env.local > .env
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサーは以下に対応:
    - 空行/コメント行（#）を無視
    - export KEY=val 形式をサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしの値におけるインラインコメント処理（'#' の前が空白/タブの場合）
  - Settings クラスを導入し、環境変数の取得と型変換をプロパティ経由で提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など
    - DB パスのデフォルト（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db）
    - 監視閾値（CPU/MEM/DISK）や PID ファイルパス
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（限定列挙値）

- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp:
    - raw_news を対象に OpenAI（gpt-4o-mini）でニュースごとのセンチメントを算出し、ai_scores テーブルに書き込む。
    - 処理の特徴:
      - JST の前日 15:00 〜 当日 08:30 のウィンドウを基に記事を集計（calc_news_window）
      - 1 銘柄あたり最大記事数・文字数でトリム（トークン肥大化対策）
      - 最大 20 銘柄/チャンクでバッチ送信（_BATCH_SIZE）
      - OpenAI の JSON Mode を用いた厳格な JSON レスポンス期待
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ付きリトライ
      - レスポンスのバリデーション（構造・型・未知コード除外・スコアの有限性）
      - スコアを ±1.0 にクリップ
      - 書き込みは部分失敗に強い方式（対象コードのみ DELETE → INSERT）
    - テスト容易性: OpenAI 呼び出し箇所をパッチ差し替え可能（_call_openai_api の差し替え）

  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルに冪等的に保存。
    - マクロ記事は事前にキーワードでフィルタ（_MACRO_KEYWORDS）し、LLM に送信。
    - 設計上の特徴:
      - ルックアヘッドバイアス防止（datetime.today()/date.today() を内部参照しない、prices_daily は target_date 未満のデータのみ参照）
      - API 失敗時は macro_sentiment=0.0 にフォールバック（例外を上げず継続）
      - OpenAI 呼び出しは専用関数で行い、再試行・5xx の扱いなどを管理

- Data / ETL / カレンダー (kabusys.data)
  - pipeline:
    - ETLResult データクラスを公開。各種取得件数・品質問題・エラーの集約を提供。
    - ETL の差分取得、バックフィル、品質チェックを想定した設計。
  - etl: pipeline.ETLResult の再エクスポートを提供（公開インターフェース）
  - calendar_management:
    - JPX カレンダー管理、営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - 動作特徴:
      - market_calendar テーブルが無い/未取得の場合は曜日ベースでフォールバック（土日を非営業日）
      - DB 登録がある場合は DB 値優先、未登録日は曜日フォールバックで一貫性を保つ
      - calendar_update_job による J-Quants からの差分取得・冪等保存（バックフィル・健全性チェックあり）
    - 安全対策: 最大探索日数による無限ループ防止、直近データの再フェッチ（バックフィル）

- Research（調査）モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1/3/6 ヶ月リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB 上の SQL で計算する関数を提供:
      - calc_momentum, calc_volatility, calc_value
    - データ不足時の扱い（None 戻し）や営業日スキャンバッファを考慮した実装
  - feature_exploration:
    - 将来リターン算出（calc_forward_returns）、IC 計算（calc_ic: Spearman ランク相関）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装
    - pandas 等外部依存なしで標準ライブラリと DuckDB のみで実装

### Changed
- 設計方針の明確化（実装に反映）
  - 全ての AI / リサーチ処理はルックアヘッドバイアス防止を優先（外部現在時刻への暗黙参照を避ける）
  - OpenAI 呼び出しに対して堅牢なフェイルセーフ（API 失敗時は例外を上げずにスコアを中立化する等）
  - DuckDB との互換性に配慮した SQL / executemany の使用（空リスト時の挙動対策を実装）

### Fixed / Implemented Safeguards
- .env パーサーの堅牢化:
  - クォート内のバックスラッシュエスケープや export プレフィックス、インラインコメント処理を正しく扱うように実装
- OpenAI 呼び出し周り:
  - 429 / 接続エラー / タイムアウト / 5xx を対象に再試行ロジックを実装し、再試行上限超過時はログを残してフェイルセーフ動作（スコア 0）にフォールバック
  - JSON パース失敗時の復元（文字列から最外の {} を抽出して再パースする）を実装し、応答のばらつきに耐性を持たせた
- DuckDB 書き込みの冪等性確保:
  - market_regime / ai_scores などは対象日やコードで既存レコードを削除してから INSERT する方式を採用
  - executemany に空リストを渡さないガード（DuckDB のバージョン差異への対応）

### Documentation / Tests (設計上の注記)
- テスト容易性を考慮して OpenAI 呼び出し部分（_call_openai_api）を差し替え可能に実装
- ログ出力・警告を多用し、異常時の追跡性を確保

### Known required environment variables（重要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（AI 機能を利用する際に必須）
- その他: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL

---

注意:
- 本 CHANGELOG は提供されたコード内容から機能・設計・実装上の挙動を推測して作成した初期リリースノートです。実際のコミット履歴・差分が存在する場合は、そちらに基づく正確な変更履歴へ差し替えてください。