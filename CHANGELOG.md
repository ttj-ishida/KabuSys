# Changelog

すべての注目に値する変更をこのファイルで記録します。  
このプロジェクトは Keep a Changelog の慣例に従い、セマンティックバージョニングを使用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04
初回公開リリース。

### Added
- パッケージ基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。主要サブパッケージを `__all__` でエクスポート（data, strategy, execution, monitoring）。

- 環境設定 / config
  - .env/.env.local の自動ロード機能を実装（プロジェクトルート検出：.git または pyproject.toml を起点）。
  - .env ファイルパーサを実装。export 式のサポート、クォート内エスケープ、インラインコメント扱い、無効行のスキップ等に対応。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト等で利用可能）。
  - 環境変数読み出しユーティリティ `Settings` を追加。J-Quants、kabuステーション、LINE、DBパス、監視閾値、ログレベル、環境種別（development/paper_trading/live）など多くのプロパティを提供。
  - 必須環境変数未設定時に明示的にエラーを出す `_require` を実装。

- AI（自然言語処理）モジュール
  - ニュースセンチメント解析: `kabusys.ai.news_nlp.score_news`
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信。
    - バッチ単位制御（最大20銘柄／チャンク）、記事数・文字数トリム、リトライ（429/ネットワーク/5xx）付きの堅牢な呼び出し。
    - レスポンス検証（JSON抜粋、results配列検証、コード照合、数値変換、スコアクリップ）を実装。
    - 成功した銘柄のみ `ai_scores` テーブルに DELETE→INSERT（冪等・部分失敗耐性）。
    - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST のUTC変換）関数 `calc_news_window` を提供。
  - 市場レジーム判定: `kabusys.ai.regime_detector.score_regime`
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出（キーワードベース）、OpenAI呼び出し、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - APIエラー・パース失敗はフェイルセーフで macro_sentiment=0.0 にフォールバック。
    - OpenAI クライアント呼び出しは専用関数化しテスト時に差し替え可能。

- データプラットフォーム関連（Data）
  - カレンダー管理: `kabusys.data.calendar_management`
    - JPX カレンダー管理（market_calendar）に関する判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバックを採用（週末非営業日）。
    - 夜間バッチジョブ `calendar_update_job` を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、冪等保存）。
  - ETL / パイプライン: `kabusys.data.pipeline`（と `kabusys.data.etl` の再エクスポート）
    - ETL 実行結果を表す `ETLResult` データクラスを実装（取得数・保存数・品質問題・エラーの集計、辞書化メソッド）。
    - 差分取得、バックフィル、品質チェックの考え方を反映した設計（実装は ETL の骨子とユーティリティを提供）。
  - DB ユーティリティ: テーブル存在チェックや DuckDB からの日付変換などの内部ユーティリティを追加。

- リサーチ / ファクター
  - ファクター計算: `kabusys.research.factor_research`
    - Momentum（1M/3M/6M、200日MA乖離）、Volatility（20日ATR等）、Value（PER, ROE）等を計算する関数を追加（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL を用いた計算実装（外部 API へのアクセスなし）。データ不足時の None ハンドリング。
  - 特徴量探索: `kabusys.research.feature_exploration`
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンのランク相関）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。

### Changed
- （初版のため該当なし）

### Fixed
- .env ローダー:
  - ファイル読み込み失敗時に警告を出力して無視する堅牢性を追加。
  - override と protected（OS 環境変数保護）を導入し、.env/.env.local 読み込みの優先度と上書き制御を実現。

- OpenAI 呼び出しの頑健性:
  - rate limit/network/timeout/5xx に対するリトライと指数バックオフを導入。非再試行対象エラーやパース失敗は WARN ログでフェイルセーフに処理。

- DB トランザクションの安全化:
  - market_regime / ai_scores への書き込みで BEGIN / DELETE / INSERT / COMMIT を用い、例外時は ROLLBACK を試行し失敗時に警告を出力。

### Security
- 環境変数自動ロードについて、既存の OS 環境変数を保護するために読み込み時に保護セットを採用。自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意。

### Notes / Design decisions
- ルックアヘッドバイアス防止: すべてのアルゴリズム（AI スコアリング、レジーム判定、ファクター計算、将来リターン）において datetime.today()/date.today() を直接参照せず、明示的な target_date を入力として処理する設計を採用。
- 部分失敗耐性: 外部 API 呼び出し失敗時は対象のみスキップし、他データや既存スコアを保護する方針を採用。
- テスト容易性: OpenAI 呼び出しや内部 API 呼び出しを関数化して unittest.mock で差し替え可能にしている。

### Contributors
- 初回実装（多数のモジュールを含む）: コードベースの著者。

---

この CHANGELOG はコード内の docstring と実装内容から推測して作成しています。実際のリリースノートと差異がある場合は、必要に応じて編集してください。