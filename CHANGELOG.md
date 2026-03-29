# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
このプロジェクトはセマンティックバージョニングを使用します。（https://semver.org/）

## [Unreleased]
- 開発中の変更や次バージョンでの予定をここに記載します。

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。

### Added
- パッケージ初期構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - 公開モジュール: data, research, ai, execution, monitoring, strategy（__all__ に準拠）

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能
  - .env のパース機能（export 形式、クォート・エスケープ、インラインコメント対応）
  - 環境値取得用 Settings クラス（必須値チェック _require、env/log_level のバリデーション）
  - デフォルト値: KABUS_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（news_nlp.score_news）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄ごとのセンチメントを算出
    - チャンク処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数制限）
    - JSON Mode を利用した厳密な JSON レスポンス期待、レスポンス検証とクリッピング（±1.0）
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ・リトライ、API 失敗時は安全にスキップし継続
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST に対応する UTC 範囲）
    - DuckDB への書き込みは部分書換え（該当コードのみ DELETE → INSERT）で部分失敗時の既存データ保護
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）の合成により market_regime を算出
    - マクロニュース選定はキーワードベース（複数キーワード定義）
    - OpenAI 呼び出しは専用の実装で JSON レスポンスを期待、API の失敗は macro_sentiment=0.0 にフォールバック
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装
  - テスト容易性のため、内部の OpenAI 呼び出し関数をモックパッチ可能に設計

- データプラットフォーム（src/kabusys/data）
  - ETL パイプライン（pipeline.ETLResult を公開）
    - 差分取得、バックフィル、品質チェックの設計方針に基づくデータ構造（ETLResult）
    - DuckDB 上での最終取得日判定ユーティリティやテーブル存在チェックを実装
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルの管理、JPX カレンダーの差分取得バッチ（calendar_update_job）
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録ありの場合は DB 値優先、未登録日は曜日フォールバック（週末は非営業日）
    - 最大探索日数・バックフィル・健全性チェックなどの安全装置を実装
  - jquants_client 等の外部クライアントとの連携想定（fetch/save 関数を使用）

- Research（src/kabusys/research）
  - ファクター計算（factor_research）
    - calc_momentum: モメンタム（1M/3M/6M）と ma200_dev（200日乖離率）
    - calc_volatility: ATR(20), atr_pct, avg_turnover, volume_ratio（20日窓）
    - calc_value: per（株価/EPS）, roe（raw_financials から最新財務を取得）
    - DuckDB によるウィンドウ関数利用、データ不足時は None を返す仕様
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 将来リターン（任意ホライズン: デフォルト [1,5,21]）
    - calc_ic: スピアマン（ランク）相関で IC を計算（レコード不足時は None）
    - rank: 同順位は平均ランクで処理（丸めによる ties 対策）
    - factor_summary: count/mean/std/min/max/median の統計サマリー

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / Migration / Compatibility
- 必須環境変数（未設定時は ValueError を送出）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI API キーは score_news / score_regime の引数として注入可能。省略時は OPENAI_API_KEY 環境変数を参照。
- .env の自動読み込みはプロジェクトルートをベースに行うため、パッケージ配布後も動作する設計。ただしプロジェクトルートが特定できない場合は自動ロードをスキップ。
- DuckDB の executemany に対する挙動（空リスト不可など）を考慮しているため、DuckDB バージョン互換性に注意。
- OpenAI（gpt-4o-mini）の JSON Mode を使用するため、API レスポンスの形式に依存。将来 SDK の挙動変更があった場合は呼び出しラッパーの修正が必要。
- 日付・時間は原則 Python の date / naive datetime で扱い、タイムゾーン混入を防止する設計。news のウィンドウは JST を基準に UTC へ変換した naive datetime を使用。

もし特定の変更点をより詳しく（例えば関数単位の挙動・例外仕様・使用例など）知りたい場合は、どのモジュール/関数についての詳細が必要か教えてください。