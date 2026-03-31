# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに従います。  
配布済みの安定版はセマンティックバージョニングに従います。

なお、本 CHANGELOG はコードベースから推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を提供します。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
  - パッケージ公開 API に data / strategy / execution / monitoring を含める。

- 環境設定管理
  - 環境変数／.env ファイルを読み込む設定管理モジュールを追加（kabusys.config）。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しない .env 自動読み込みを実装。
  - .env / .env.local 読み込み順・上書き（override）ルールを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - 複雑な .env 行解析を実装（コメント、export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ対応）。
  - 必須環境変数取得のヘルパー `_require` と各種設定プロパティ（API トークン、DB パス、監視閾値、環境判定、ログレベルなど）を提供。

- AI（自然言語処理）機能
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信して ai_scores に書き込むワークフローを実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）、文字数／記事数トリム、バッチ化（最大 20 銘柄）を実装。
    - JSON mode 応答の堅牢なバリデーションおよびパース処理を実装（JSON 前後に余計なテキストが混入するケースへの復元処理含む）。
    - エラー耐性：429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、その他エラーはフェイルセーフでスキップ。
    - テストしやすさのため API 呼び出し関数をパッチ可能に設計（_call_openai_api を差し替え可能）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を計算。
    - prices_daily / raw_news / market_regime テーブルへの参照・冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API キー注入可能、API エラーやパース失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ動作。
    - ルックアヘッドバイアス対策（date 未満のデータのみ参照、date.today() を参照しない設計）。

- データ処理・ETL
  - ETL の公開インターフェース ETLResult をエクスポート（kabusys.data.etl）。
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分更新ロジック、バックフィル、品質チェックの設計方針と ETLResult dataclass を実装。
    - DuckDB を前提としたテーブル存在チェック、最大日付取得、結果の集合的表現などを実装。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - market_calendar を用いた営業日判定ユーティリティ（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を追加。
  - J-Quants API からのカレンダー差分取得・夜間バッチ（calendar_update_job）を追加。バックフィルや健全性チェックを実装。
  - DB データが不足する場合の曜日ベースのフォールバック実装（カレンダー未取得時の安全動作）。

- リサーチ / ファクター系
  - リサーチモジュールの公開（kabusys.research.__init__）と主要関数の実装。
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）等の計算関数を追加。
    - DuckDB 内で SQL とウィンドウ関数を組み合わせて効率的に算出する設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を提供。
    - 外部依存を避け、標準ライブラリのみで実装。

### Changed
- （初版のため履歴なし）

### Fixed
- （初版のため履歴なし）

### Security
- （初版のため履歴なし）

---

注記（設計上の主な判断）
- ルックアヘッドバイアス防止のため、time.now()/date.today() に依存しない設計を各所で採用。
- OpenAI など外部 API 呼び出しは堅牢化（リトライ、タイムアウト、エラーハンドリング、部分失敗の隔離）されている。
- DuckDB の互換性制約（executemany の空リスト問題など）に配慮した実装が行われている。
- テスト容易性のため、API 呼び出し箇所はモック差し替え可能にしてある。

もし個別の変更点詳細（コミット単位や設計判断の補足）を反映したい場合は、コミットログや追加情報を提供してください。