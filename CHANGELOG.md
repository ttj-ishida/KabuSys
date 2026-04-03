# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回公開リリース。日本株自動売買・データ基盤・研究用ユーティリティをまとめた基盤機能を提供します。

### Added
- パッケージ基本情報
  - kabusys パッケージ初期化（__version__ = "0.1.0"）と公開サブパッケージ指定（data, strategy, execution, monitoring）。

- 環境設定/設定管理（kabusys.config）
  - .env 自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を基準）。
  - .env と .env.local の読み込み順序サポート（OS 環境変数を保護する設計）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 柔軟な .env パーサ（コメント、export プレフィックス、クォート内のエスケープ対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB /監視/システム設定のプロパティを環境変数から取得。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）と便宜的プロパティ（is_live / is_paper / is_dev）。
  - デフォルトの DB パス（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）や監視ファイルパスの既定値設定。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いた銘柄別ニュース集約（前日15:00 JST 〜 当日08:30 JST のウィンドウ）。
    - OpenAI（gpt-4o-mini）を JSON Mode でバッチ呼び出し（1回最大20銘柄）。
    - チャンク単位リトライ（429・ネットワーク断・タイムアウト・5xx で指数バックオフ）。
    - レスポンス検証（JSON パース耐性、results フィールド検証、コード照合、スコア数値検証）。
    - スコアの ±1.0 クリップ、ai_scores テーブルへの冪等書き込み（DELETE → INSERT）。
    - lookahead バイアス回避のため datetime.today()/date.today() を直接参照しない設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
    - マクロニュースはキーワードフィルタで抽出、LLM（gpt-4o-mini）で -1.0〜1.0 を返却する想定（JSONのみ）。
    - API 呼び出しのリトライ・フォールバック（失敗時 macro_sentiment=0.0）。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を再送出。
    - lookahead バイアス防止のクエリ/設計方針を採用。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定 API（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB 未取得日の曜日ベースフォールバック（週末を非営業日とする）。
    - 夜間バッチ更新 job（calendar_update_job）：J-Quants から差分取得 & 冪等保存、バックフィル・健全性チェックを実装。
    - 最大探索日数・先読み・バックフィル等の安全制約を実装し無限ループや過度な将来日付を防止。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラス（target_date, fetch/save カウント、品質問題、エラー一覧、シリアライズ用 to_dict）。
    - 差分更新・バックフィル・品質チェック・idempotent 保存の仕様に基づく設計方針を実装（実際の jquants_client/quality は別モジュールで利用）。
    - DuckDB を前提としたテーブル存在チェック・最大日付取得ユーティリティ等。
  - jquants_client 等のクライアントを前提とした差分取得/保存フローに対応するインターフェースを用意。
  - パッケージ内で ETLResult を再エクスポート（kabusys.data.etl）。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。NULL取り扱いを明示。
    - calc_value: raw_financials から最新財務データを取得して PER/ROE を計算。
    - DuckDB のウィンドウ関数を活用した高効率 SQL 実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）について将来リターンを計算。ホライズンのバリデーションあり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。十分な有効レコードが無い場合は None。
    - rank: 同順位は平均ランクで処理（丸め誤差対策で round を使用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - research パッケージから上記関数群とデータ系ユーティリティ（zscore_normalize の再エクスポート）を公開。

- その他
  - duckdb を前提とした型ヒントと SQL 実行を多数実装。
  - OpenAI クライアント（openai.OpenAI）を使ったチャット補助関数をモジュールごとに個別実装し、テスト時に差し替えやすく設計。
  - API 呼び出し周りでのフェイルセーフ設計（非致命的な API 失敗はスキップ・フォールバックすることでバッチの継続を優先）。
  - ロギングメッセージとデバッグ情報を充実させ、運用時のトラブルシュートを支援。

### Changed
- （該当なし）初回リリースのため "Changed" はありません。

### Fixed
- （該当なし）初回リリースのため既知のバグ修正履歴はありません。ただし多くの箇所でエラーハンドリングと ROLLBACK／リトライ等を実装して運用耐性を高めています。

### Security
- 重要な外部 API キー（OpenAI, J-Quants など）を環境変数から取得する設計。キーの誤公開を避けるため .env の取り扱いと自動読み込みに注意してください（KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化を提供）。

### Breaking Changes
- （該当なし）初回リリースのため互換性破壊はありません。

---

参考: 本リリースで想定される必須/推奨環境設定
- 環境変数（必要に応じて）:
  - OPENAI_API_KEY（news_nlp / regime_detector の API 呼び出しに必須）
  - JQUANTS_REFRESH_TOKEN（J-Quants クライアント用）
  - KABU_API_PASSWORD（kabu ステーション連携用）
- DuckDB（ローカルファイル path を settings.duckdb_path で指定）
- 実運用では .env / .env.local をプロジェクトルートに配置して設定を管理してください。

もし、特定モジュール（例: news_nlp の出力フォーマット、regime_detector の重み・閾値、calendar_update_job の lookahead/backfill 設定等）についてCHANGELOGの記述をより詳細に分けたい場合は、そのモジュール名と注目点を教えてください。