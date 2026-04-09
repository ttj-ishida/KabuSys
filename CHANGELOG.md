# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」規約に準拠しています。  
次のバージョン番号は semver に従います。

- リリース日付のフォーマット: YYYY-MM-DD
- 本リリースはパッケージの初期公開（0.1.0）を想定して作成しています。

## [0.1.0] - 2026-04-09

### Added
- 初回公開: kabusys パッケージ（日本株自動売買システム）のコアモジュールを追加
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
    - パッケージ公開インターフェースとして data, strategy, execution, monitoring を __all__ に追加。

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
  - .env / .env.local の自動ロード機構（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサの強化:
    - export KEY=val 形式対応、シングル／ダブルクォート内のエスケープ対応、インラインコメントの扱い、無効行のスキップ等。
  - .env 読み込み時の保護機能:
    - OS 環境変数は protected として上書き不可（.env, .env.local の上書き順制御）。
  - Settings クラスで主要構成をプロパティとして提供:
    - J-Quants / kabu ステーション / LINE / DB パス（duckdb, sqlite, paper_trading）/監視閾値（CPU/Memory/Disk）/PID/KILL フラグ等。
    - PAPER_FILL_MODE（paper trading の fill モード）や KABUSYS_ENV, LOG_LEVEL のバリデーションを実装。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI 関連モジュールを追加（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント解析を行い ai_scores テーブルに書き込む。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの記事数/文字数制限、レスポンス検証、スコアの ±1.0 クリップ。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx 共通の指数バックオフ）、フェイルセーフで失敗時はスキップし続行。
    - テスト容易性のため API 呼び出し関数のパッチ可能化（unittest.mock.patch の想定）。
    - calc_news_window(target_date) による JST/UTC のウィンドウ計算（ルックアヘッドバイアスを避ける設計）。
    - パブリック API: score_news(conn, target_date, api_key=None) をエクスポート（src/kabusys/ai/__init__.py）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しに対する堅牢なリトライとフェイルセーフ（API失敗時は macro_sentiment=0.0 として継続）。
    - ルックアヘッドバイアス防止（target_date 未満のデータのみ使用）と DB トランザクション制御（BEGIN/DELETE/INSERT/COMMIT、失敗時に ROLLBACK）。
    - パブリック API: score_regime(conn, target_date, api_key=None)。

- Research（リサーチ）モジュールを追加（src/kabusys/research）
  - factor_research.py:
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日 ATR、相対ATR、出来高関連）、Value（PER, ROE）等を DuckDB 上で計算。
    - 欠損データ判定、ウィンドウスキャン範囲のバッファ処理、結果は (date, code) をキーとする dict リストで返却。
    - 関数: calc_momentum, calc_volatility, calc_value。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic／Spearman ランク相関）、rank, factor_summary（統計サマリー）を実装。
    - pandas 等に依存しない標準ライブラリ実装。データ結合は code キーで対応。
  - research パッケージのトップレベルで主要関数を再エクスポート。

- Data（データ基盤）モジュールを追加（src/kabusys/data）
  - calendar_management.py:
    - JPX カレンダーの管理（market_calendar テーブル）と夜間更新ジョブ（calendar_update_job）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定・探索 API を提供。
    - DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）。
    - 探索上限 (_MAX_SEARCH_DAYS) による無限ループ防止、バックフィルと健全性チェック。
    - J-Quants クライアントとの連携（kabusys.data.jquants_client 経由）を想定。
  - pipeline.py / etl.py:
    - ETLResult データクラス（ETL 実行結果の構造化）と ETL パイプライン用のインターフェースを追加。
    - 差分取得、保存（idempotent）、品質チェック（quality モジュールと連携）等の方針を実装するための基盤コード。
    - ETLResult に to_dict / has_errors / has_quality_errors 等のユーティリティを実装。
  - data パッケージのトップレベルで ETLResult を再エクスポート（src/kabusys/data/__init__.py / src/kabusys/data/etl.py）。

- DuckDB を前提とした DB 操作:
  - 多くのモジュールが duckdb 接続を引数に取り SQL と Python を組み合わせて処理。
  - 性能・互換性のため executemany の空リスト回避、ROW_NUMBER / ウィンドウ関数の活用など。

### Changed
- 初期リリースのため、既知の設計方針や制約を各モジュールの docstring/コメントで明示化
  - ルックアヘッドバイアスの回避設計（datetime.today()/date.today() を直接参照しない等）
  - API 呼び出しのフェイルセーフ化（OpenAI API 失敗時のフォールバック、部分失敗時の DB 保護）

### Fixed
- （初回リリースのコードベース）トランザクション失敗時の安全処理を各所で実装
  - score_regime / score_news などで ROLLBACK の試行と失敗時のログ出力を追加。

### Security
- 環境変数/秘密情報の扱いについて注意を明記
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を要求する（未設定時は ValueError を送出）。
  - OS 環境変数は .env による上書きを保護（protected set）。

### Notes / Developer conveniences
- OpenAI 呼び出し部分はテスト容易性を考慮してパッチ可能（関数単位で差し替え可能）。
- .env パーサは様々な現実的ケース（エスケープ、コメント、export 形式）に対応するよう設計済み。
- DuckDB バージョン差異（executemany の挙動等）に対応するためのガード実装を随所に配置。

---

今後の予定（想定）
- strategy / execution / monitoring モジュールの実装拡張（発注ロジック、実取引インターフェース、実行監視）。
- 単体テスト・統合テストの充実（OpenAI 呼び出しのモック化、DuckDB テストデータ）。
- ドキュメント整備（API リファレンス、運用手順、環境構築手順）。