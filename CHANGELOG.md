# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース

### Added
- 基本パッケージ
  - パッケージ名: kabusys（__version__ = 0.1.0）
  - 公開サブパッケージ群: data, research, ai, execution, strategy, monitoring（__all__）

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env パーサ実装（export 形式対応、クォート内のエスケープ、インラインコメント処理）
  - override / protected オプションにより OS 環境変数を保護して上書き制御
  - Settings クラス（J-Quants / kabuステーション / Slack / DB パス / 環境種別等のプロパティ）
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）

- AI（kabusys.ai）
  - ニュースNLP（news_nlp.score_news）
    - raw_news / news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI（gpt-4o-mini）へ送信
    - バッチ処理（最大20銘柄/チャンク）、トークン肥大対策（記事数/文字数制限）
    - JSON Mode を用いたレスポンス検証とスコア抽出
    - リトライ（429、ネットワーク、タイムアウト、5xx）に対する指数バックオフ
    - レスポンス検証/数値正規化/±1.0 クリップ、DuckDB 互換性のための executemany 空リスト回避対策
    - calc_news_window（前日15:00 JST〜当日08:30 JST に対応する UTC ウィンドウ計算）
    - テスト容易性: API 呼び出し関数の差し替えポイント（_call_openai_api）を提供
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満データのみ使用）
    - マクロニュース抽出（キーワードフィルタ）→ LLM 評価（gpt-4o-mini）→ 合成スコアリング
    - フェイルセーフ: API 失敗時は macro_sentiment=0.0 にフォールバック
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - テスト容易性: API キー注入、内部 OpenAI 呼び出しポイントの分離

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の計算（prices_daily ベース）
    - calc_value: raw_financials と価格を組み合わせて PER / ROE を計算（最新財務レコードの取得ロジック）
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率の計算
    - SQLベース実装により DuckDB 上で直接高速に計算
  - feature_exploration
    - calc_forward_returns: 複数ホライズンに対応した将来リターン計算（LEAD を利用）
    - calc_ic: スピアマン（ランク）ベースの IC（Information Coefficient）計算
    - rank: 同順位は平均ランクにする実装（丸めで ties の誤差を回避）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出
  - zscore_normalize を data.stats から再エクスポート

- データプラットフォーム（kabusys.data）
  - calendar_management
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、健全性チェック
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に更新（バックフィル、健全性チェック）
  - pipeline / ETL
    - ETLResult データクラスによる ETL 実行結果の集約（取得数、保存数、品質問題、エラー等）
    - 差分更新、バックフィル、品質チェック統合を想定した設計（jquants_client との連携、quality モジュール参照）
  - etl モジュールで ETLResult を再エクスポート

- 実装上の設計方針（横断的）
  - ルックアヘッドバイアス防止: datetime.today() / date.today() をスコア計算ロジック内部で参照しない設計（target_date ベース）
  - DuckDB 上で SQL + Python を組み合わせた一貫したデータ処理
  - DB 書き込みは冪等性を重視（DELETE→INSERT など）
  - ログ出力を充実（警告・情報・デバッグ）
  - テスト容易性を考慮した注入ポイント・モック可能な内部関数
  - 依存: openai, duckdb（その他は標準ライブラリ中心）

### Changed
- （初回リリースのため特になし）

### Fixed
- （初回リリースのため特になし）

### Deprecated
- （初回リリースのため特になし）

### Removed
- （初回リリースのため特になし）

### Security
- （初回リリースのため特になし）

### Known limitations / Notes
- news_nlp の出力は現在 sentiment_score と ai_score が同値（将来的に差別化の余地あり）
- バリューファクターでは PBR・配当利回りは未実装
- DuckDB のバージョン差異（executemany の空リストなど）に対する互換性ワークアラウンドを含む
- OpenAI API 呼び出しは外部サービスに依存するため、APIキー管理とコスト・レート制限に注意

-----
この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は変更履歴やコミットログを参照して適宜更新してください。