# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠し、セマンティックバージョニングに従います。

現在のパッケージバージョン: 0.1.0

## [Unreleased]
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-04

初期リリース — 日本株自動売買／リサーチ／データ基盤のコア機能群を提供します。以下は実装された主な機能と設計上の重要点の要約です。

### Added
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加。__version__ = "0.1.0"、公開サブパッケージを __all__ で定義。

- 環境設定モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、カレントワーキングディレクトリに依存しない実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応。
  - .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
  - _load_env_file によるファイル読み込みで override / protected ロジックを導入（OS 環境変数を上書きさせない保護）。
  - Settings クラスを提供し、主要な設定値をプロパティで取得可能に：
    - J-Quants / kabuステーション / LINE / DB パス（DuckDB / SQLite）/ 監視関連（PID, kill flag）/ CPU/メモリ/ディスク閾値 等
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証（不正値は ValueError）。
    - is_live / is_paper / is_dev の便宜プロパティ。

- AI モジュール (kabusys.ai)
  - news_nlp モジュール
    - ニュース記事を銘柄ごとに集約し OpenAI （gpt-4o-mini, JSON mode）でセンチメントを評価。
    - バッチ（最大 20 銘柄）での API 呼び出し、トークン肥大対策（記事数・文字数上限）、リトライ（429/ネットワーク/タイムアウト/5xx の指数バックオフ）を実装。
    - レスポンス検証（JSON パースの堅牢化、results フォーマット検査、未知コードの無視、スコアの ±1.0 クリップ）。
    - ai_scores テーブルへの冪等書き込み（対象コードのみ DELETE → INSERT、DuckDB executemany 空リスト対策）。
    - calc_news_window ユーティリティ（JST ベースのニュース収集ウィンドウ算出）。
  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース（LLM センチメント、重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news からのデータ抽出、OpenAI 呼び出し、スコア合成、market_regime への冪等書き込みを提供。
    - API エラー時のフォールバック（macro_sentiment = 0.0）やリトライ処理、ルックアヘッドバイアス回避設計を採用。

- Research（因子計算・特徴量探索）
  - factor_research モジュール
    - calc_momentum：1M/3M/6M リターン、200日 MA 乖離（データ不足時に None を返す）。
    - calc_volatility：20日 ATR（平均）、相対 ATR、20日平均売買代金、出来高比率など。
    - calc_value：最新の raw_financials に基づく PER / ROE（EPS が無効な場合は None）。
    - DuckDB を用いた SQL ベースの実装で外部 API に依存しない設計。
  - feature_exploration モジュール
    - calc_forward_returns：指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（営業日ベース、入力検証あり）。
    - calc_ic：ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコードが少ない場合は None）。
    - rank：同順位は平均ランクで処理（丸めによる ties 対策）。
    - factor_summary：count/mean/std/min/max/median の統計サマリーを算出。

- Data（データ基盤・ETL・カレンダー）
  - calendar_management モジュール
    - market_calendar を用いた営業日判定 API：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB 登録値優先、未登録日は曜日（平日）ベースでフォールバックする一貫したロジック。
    - calendar_update_job：J-Quants からの差分取得、バックフィル日数の考慮、健全性チェック（将来日付の異常検出）、冪等保存を実装。
  - pipeline / etl モジュール
    - ETLResult データクラス（取得/保存数、品質問題、エラー一覧、has_errors / has_quality_errors / to_dict を提供）。
    - ETL パイプラインの骨格（差分取得、バックフィル、品質チェックの収集方針）を実装。jquants_client と quality モジュールを利用する設計。
    - DuckDB の存在チェックや最大日付取得等のユーティリティ関数を追加。
  - data.etl から ETLResult を再エクスポート。

- テスト可能性・拡張性の配慮
  - OpenAI 呼び出し箇所で _call_openai_api を分離し、単体テスト時に patch で差し替え可能に設計。
  - 環境依存を抑える（プロジェクトルート探索など）実装。

### Changed
- 設計上の重要方針（実装段階で明確化）
  - すべての時刻ロジックで datetime.today()/date.today() への直接依存を避け、外部から target_date を渡すことでルックアヘッドバイアスを防止。
  - OpenAI API との連携は失敗しても致命的に停止させずフォールバック（中立スコアやスキップ）で処理継続するフェイルセーフ設計を採用。
  - DuckDB の互換性（executemany 空リスト問題など）を考慮した実装細部の調整。

### Fixed
- 初期リリースのため該当なし（既知のランタイム動作確認は今後のイシューで管理）。

### Security
- .env 読み込み時に OS 環境変数上書きから保護する protected セットを導入。
- 必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）の欠如は明示的に ValueError を発生させることで起動時の不整合を早期検出。

### Notes / 注意事項
- OpenAI API キーは引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を投げる実装になっています。
- DuckDB を前提とした SQL 実装になっています。データモデル（prices_daily / raw_news / ai_scores / market_regime / market_calendar / raw_financials 等）のスキーマ準備が必要です。
- 一部関数は外部クライアント（jquants_client 等）に依存しています。実運用前に API クライアントの設定・テストが必要です。
- ルックアヘッドバイアス回避のため、すべてのスコア計算関数は target_date を明示的に受け取ります。運用時は意図した基準日を渡して実行してください。

---

今後の予定（例）
- 単体テストの充実（モック API を含む）。
- 監視/自動再起動のための execution/monitoring モジュール実装（初期エクスポートに含まれるが詳細は未実装）。
- スコア付与ロジックやプロンプトのチューニング、モデル切替オプションの追加。