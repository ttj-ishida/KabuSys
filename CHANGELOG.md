# Changelog

すべての重要な変更履歴を記載します。本プロジェクトは Keep a Changelog の方針に準拠しています。

## [0.1.0] - 2026-04-02

### Added
- 初期リリース。日本株自動売買プラットフォームのコア機能を追加。
- パッケージ構成
  - kabusys パッケージの公開モジュール: data, strategy, execution, monitoring をエクスポート。
  - バージョン: 0.1.0
- 環境設定管理（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数の読み込み機能を実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途）。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD 非依存）。
  - .env パーサー: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱い等に対応。
  - 上書き保護: OS 環境変数を protected として .env による上書きを制御可能。
  - Settings クラス: 必須環境変数取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、デフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）、閾値設定（CPU/MEMORY/DISK）および環境検証（KABUSYS_ENV, LOG_LEVEL）。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合。
    - OpenAI（gpt-4o-mini）へのバッチ送信（最大20銘柄/チャンク）と JSON Mode を利用した応答取得。
    - レスポンスの厳格バリデーション、スコアの ±1.0 クリップ。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
    - DuckDB 互換性のため executemany の空リスト回避などの保護処理。
    - calc_news_window: JST 時間ウィンドウ（前日 15:00 ～ 当日 08:30 JST）を UTC naive datetime に変換するユーティリティ。
    - テスト容易性のため _call_openai_api をモック差替え可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）と LLM によるマクロセンチメント（重み30%）を合成して日次レジーム（bull / neutral / bear）判定。
    - マクロニュース抽出（マクロキーワードリスト）と OpenAI 呼び出しを用いた JSON 出力パース。
    - API エラー時のフェイルセーフ（macro_sentiment=0.0）とリトライ実装。
    - レジーム計算結果を market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策（日時の直接参照を行わず、target_date 未満のデータのみ参照）。
- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定関数群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 未登録日は曜日ベースのフォールバック（土日非営業）を使用。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等に更新（バックフィル・健全性チェック付き）。
    - 最大探索日数制限やバックフィル（直近数日再取得）の実装で安全性を確保。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（target_date, fetched/saved counts, quality_issues, errors 等）。
    - ETL の差分更新方針、バックフィル、品質チェックとの連携を仕様として実装。
    - DuckDB 用のテーブル存在チェック・最大日付取得ユーティリティ。
  - jquants_client を介した取得/保存フックを想定した設計（DataPlatform.md に基づく）。
- リサーチ（kabusys.research）
  - factor_research: ファクター計算関数を提供
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率。
    - calc_value: PER、ROE（raw_financials の最新値を用いる）。
    - DuckDB 上の SQL を主体に計算し、外部 API には依存しない。
  - feature_exploration: 特徴量探索ユーティリティ
    - calc_forward_returns: 将来リターン（任意ホライズン、デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関に基づく IC 計算（rank を内部で処理）。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクとするランク計算（丸めによる ties 対応）。
- 複数箇所での設計方針
  - ルックアヘッドバイアスを避けるため、datetime.today() / date.today() を計算の基準に直接使わない実装方針を採用（target_date ベースの処理）。
  - OpenAI 呼び出しに対するフェイルセーフ（API 失敗時に例外を上位に投げずスキップまたは中立スコアで継続）を導入。
  - DuckDB のバージョン差異に配慮した実装（executemany 空配列回避など）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- .env 読み込み時に OS の既存環境変数を保護する仕組みを導入（protected set）。  
  ※ 機密情報の扱いは Settings の必須チェック等により安全性に配慮。

### Notes / Implementation details
- OpenAI API は gpt-4o-mini を想定し、JSON mode（response_format={"type":"json_object"}）で厳密な JSON 出力を期待する仕様。ただし実運用で前後に余計なテキストが混入するケースを考慮してパースの回復処理を実装。
- テスト容易性のため、OpenAI 呼び出し部分を内部的に分離しており unittest.mock.patch 等で差し替え可能。
- DuckDB を主要なローカルデータストアとして利用する想定（パスは Settings で指定可能）。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡張（本リリースではパッケージ公開のみ）。
- jquants_client の具象実装と ETL パイプラインの統合テスト。
- 追加の品質チェックルール、モニタリングアラート機能の強化。