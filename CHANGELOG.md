# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog のフォーマットに従います。  

※ バージョン番号はパッケージの `__version__`（src/kabusys/__init__.py）に従います。

## [Unreleased]

（現時点のコードベースでは未リリースの追加変更はありません）

## [0.1.0] - 2026-03-29

初回公開リリース。以下の主要機能と実装を含みます。

### Added

- パッケージ基盤
  - パッケージ初期化および公開 API を追加（src/kabusys/__init__.py）。
    - __version__ = "0.1.0"
    - サブパッケージ公開: data, strategy, execution, monitoring

- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みするユーティリティを実装。
    - プロジェクトルート検出機能（.git または pyproject.toml を探索）により CWD に依存しない自動ロード。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は既存値を上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト向け）。
  - .env パーサ実装:
    - 空行・コメント・`export KEY=val` 形式に対応。
    - シングル／ダブルクォートのエスケープ処理、インラインコメント取り扱い、キー・値のトリム処理を実装。
  - 環境変数取得ヘルパとバリデーション実装（Settings クラス）。
    - 必須設定取得時の ValueError 投げ替え。
    - KABUSYS_ENV（development|paper_trading|live）・LOG_LEVEL の妥当性チェック。
    - デフォルト値: KABUSYS_API_BASE_URL など一部にデフォルトを用意。
    - データベースパスの Path 型化（duckdb/sqlite の既定パス）。

- AI（自然言語処理）モジュール（src/kabusys/ai/）
  - ニュースセンチメント（news_nlp.py）
    - raw_news と news_symbols を用いて銘柄別に記事を集約し、OpenAI（gpt-4o-mini の JSON mode）でセンチメントを評価。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
    - バッチ処理（最大 20 銘柄／API 呼び出し）、1 銘柄あたり記事数と文字数の上限（トリム）を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数的バックオフ再試行。
    - レスポンスバリデーション（JSON 抽出・構造チェック・未知コード無視・数値変換・有限性確認）。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。部分失敗時に既存スコアを保護する挙動。
    - テスト容易性: OpenAI 呼び出し箇所は内部関数を通し、patch による差し替えが可能。
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照して計算。マクロ判定は gpt-4o-mini の JSON mode を使用。
    - API 失敗時は macro_sentiment = 0.0 にフォールバックするフェイルセーフを実装。
    - レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - リトライ・エラー処理、JSON パース失敗時のログとフォールバック動作を実装。
  - AI パッケージ公開 API: score_news, score_regime（src/kabusys/ai/__init__.py）。

- データプラットフォーム（src/kabusys/data/）
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルを元に営業日判定ユーティリティを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値優先・未登録日は曜日ベースのフォールバック（週末判定）で一貫した結果を返す設計。
    - next/prev の探索は最大探索日数制限（_MAX_SEARCH_DAYS）を設け、安全性を確保。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants API から差分取得し保存、バックフィル・健全性チェックを実装。
    - DuckDB 型変換ユーティリティやテーブル存在チェックを実装。
    - jquants_client との統合ポイント（fetch/save）を用意。
  - ETL パイプライン（pipeline.py）および公開インターフェース（etl.py）
    - 差分更新の設計方針に基づく ETLResult データクラスを実装（取得数／保存数／品質問題／エラーの集約）。
    - ETL パイプラインユーティリティ（差分取得、backfill、品質チェック）用の基盤を整備。
    - DuckDB のテーブル存在チェック・最大日付取得ユーティリティを実装。
    - etl.py で ETLResult を再エクスポート。
  - data パッケージの jquants_client / quality 等の統合を想定した設計（モジュール分離）。

- Research（src/kabusys/research/）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離率）、Volatility（20 日 ATR/相対 ATR）、Liquidity（20 日平均売買代金・出来高比率）、Value（PER、ROE）を DuckDB の SQL と Python で計算するユーティリティを実装。
    - データ不足時の None 処理、結果を (date, code) ベースの dict リストで返す設計。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）での将来終値リターンを計算。
    - IC（Information Coefficient）計算: Spearman 的ランク相関でファクター有効性を評価（calc_ic）。
    - ランキングユーティリティ（rank）と統計サマリー（factor_summary）を実装。
  - research パッケージの公開 API を __all__ で整理。

### Changed

- （初回リリースのため該当なし）

### Fixed

- （初回リリースのため該当なし）

### Security

- （該当なし）

### Notes / Implementation details / 注意点

- 時刻 / 日付扱い:
  - ニュースウィンドウ等は JST の要件に合わせ UTC naive datetime に変換して DB 比較に使用し、ルックアヘッドバイアスを排除する実装方針を採用。
  - モジュールは datetime.today() / date.today() を直接参照しない設計（引数で target_date を受ける）。
- OpenAI 連携:
  - gpt-4o-mini と JSON モードを前提にプロンプト設計を行い、レスポンスは JSON の厳密な出力を期待するが、実運用では前後テキスト混入への耐性（{} の抽出など）を持たせている。
  - API 呼び出しは専用の内部関数経由で行い、ユニットテスト時にモック差し替えしやすくしている。
- DB 書き込み:
  - ai_scores, market_regime への書き込みは冪等化（削除して挿入）を行い、部分失敗時に他データを消さない工夫をしている。
  - DuckDB の executemany に関する互換性（空リスト不可）を考慮した条件分岐を実装している。
- ロギング:
  - 各モジュールで詳細なログ（INFO/DEBUG/WARNING/exception）を出力するようにしており、失敗は可能な限りフォールバックで継続する（例: LLM 失敗時にスコア 0.0 を使う等）。

### Breaking Changes

- なし（初回リリース）

---

参照: 実装ファイル群（src/kabusys/*）からの推測に基づく CHANGELOG です。必要であれば各モジュール単位でさらに詳細な変更点・設計意図を追記します。