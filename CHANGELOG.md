KEEP A CHANGELOG
=================

すべての注目すべき変更点をバージョン別に記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- 未リリースの変更は [Unreleased] に記載します。
- 各リリースには追加 (Added)、変更 (Changed)、修正 (Fixed) 等のセクションを付けます。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。国内株自動売買プラットフォームのコアライブラリ群を追加。

### Added
- パッケージ基本情報
  - kabusys パッケージの初期化（src/kabusys/__init__.py）およびバージョン 0.1.0 を設定。

- 環境変数/設定管理
  - .env ファイルまたは実行環境の環境変数から設定を読み込む設定モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート検出: .git / pyproject.toml を基準に自ファイル位置から探索（CWD に依存しない）。
    - .env の自動ロード順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - .env パーサは export 形式、クォート付き値、インラインコメント、エスケープをサポート。
    - Settings クラスを提供し、各種必須/任意設定（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境・ログレベル等）を型付きプロパティで取得・バリデーション。
    - 環境名 (KABUSYS_ENV) と LOG_LEVEL の許容値検査を実装。

- AI（自然言語処理）機能
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントを取得。
    - バッチサイズ、トークン肥大対策（記事数上限・文字数トリム）、JSON レスポンスの堅牢なパースを実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）、レスポンス検証、スコア ±1.0 クリップ、部分成功時の DB 書き換え保護（対象コードの限定 DELETE→INSERT）。
    - テスト容易性のため _call_openai_api の差し替えが可能（unittest.mock での patch を想定）。
    - タイムウィンドウ計算 calc_news_window を提供（JST ベースの前日 15:00 ～ 当日 08:30 を UTC で比較する設計）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロニュースは news_nlp の calc_news_window に従って抽出、OpenAI 呼び出しは個別実装でモジュール結合を避ける。
    - API エラーやレスポンスパース失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試行）。
    - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を参照しない設計。

- リサーチ / ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、ATR 比、流動性指標）、Value（PER, ROE）を DuckDB 上で計算する関数群を追加。
    - データ不足時の None 処理や営業日・スキャン範囲などの安全対策を実装。
    - DuckDB のウィンドウ関数活用により効率的に計算。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず、標準ライブラリと DuckDB のみで実装。
    - calc_ic はスピアマンρ（ランク相関）を実装し、十分なサンプルがない場合は None を返す。

  - research パッケージ初期化（src/kabusys/research/__init__.py）で主要 API を公開。

- Data（データ基盤）機能
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルの有無に応じた営業日判定ロジックを提供（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録有無でのフォールバック（DB 登録があれば優先、未登録は曜日ベース）で一貫性を確保。
    - 夜間バッチ更新ジョブ calendar_update_job を提供（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数やバックフィル日数等の安全設定を設計に組み込み。

  - ETL パイプラインおよび結果クラス（src/kabusys/data/pipeline.py と src/kabusys/data/etl.py）
    - ETLResult データクラスを追加し、ETL の取得/保存件数、品質問題、エラー一覧を集約。辞書化メソッドを提供。
    - ETL モジュールは差分更新、バックフィル、品質チェックの設計方針を反映（J-Quants クライアント経由での取得・保存、品質チェックを収集して返す）。
    - data/etl は pipeline.ETLResult を再エクスポート。

  - data パッケージの基礎構成（src/kabusys/data/__init__.py ほか）。

- 汎用設計・運用に関する注意点（ドキュメント内明記）
  - DuckDB を主なストレージとして利用（DuckDB バインドの互換性注意: executemany の空リスト回避など）。
  - 外部 API（OpenAI, J-Quants）呼び出しに対する堅牢なリトライ/フェイルセーフ設計。
  - ルックアヘッドバイアス防止のため、target_date ベースの計算と DB クエリの排他条件（date < target_date 等）を徹底。
  - テスト用フック（_call_openai_api の差し替え等）を用意。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

Notes / 依存関係
- OpenAI SDK（chat completions / JSON mode）を利用する設計。環境変数 OPENAI_API_KEY を期待。
- DuckDB 必須（データ保存/クエリ実行用）。
- J-Quants クライアントインタフェース（kabusys.data.jquants_client）への依存がある（calendar/pipeline のデータ取得・保存で使用）。
- 実行環境に応じた .env 設定を推奨（.env.example を参考）。

今後の予定（想定）
- 監視・実行モジュール（execution / monitoring）や運用向け CLI、テストカバレッジ、ドキュメントの整備。
- 実運用に向けたセキュリティ監査と依存ライブラリの固定化。

--- 
この CHANGELOG はコードベースの公開 API と振る舞いから推測して作成しています。実際のリリースノートとして利用する場合は、追加の確認や補足（既知の制限・互換性情報等）を反映してください。