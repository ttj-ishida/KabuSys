CHANGELOG
=========

すべての重要な変更は Keep a Changelog の方針に従って記載しています。
このファイルは人間に読みやすく、後でリリースノート生成に使えるように設計されています。

フォーマット:
- 各リリースは日付付きでセクション化
- セクション: Added / Changed / Deprecated / Removed / Fixed / Security

[Unreleased]
-----------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - パブリックサブパッケージのエクスポートを定義（data, strategy, execution, monitoring）。

- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（OS 環境変数 > .env.local > .env の優先順）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ対応。
  - .env のパースはコメント、export プレフィックス、シングル/ダブルクォート、エスケープに対応。
  - 必須環境変数取得用 _require()、各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI 関連、DB パス、Paper Trading 設定、監視閾値など）を提供。
  - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の検証）を実装。

- AI 関連モジュールを追加（src/kabusys/ai/）
  - ニュースNLP: score_news（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとにテキスト結合・トリムし、OpenAI（gpt-4o-mini）の JSON Mode で一括センチメントスコアを取得。
    - バッチ処理（最大 20 銘柄/チャンク）、トークン制御（記事数・文字数制限）、リトライ（429/ネットワーク/タイムアウト/5xx 共通の指数バックオフ）を実装。
    - レスポンスのバリデーション機構（JSON 抽出、results 配列、code/score 検証、スコアクリッピング）を実装。
    - スコアは ai_scores テーブルへ冪等的に（DELETE→INSERT）書き込み。部分失敗時に既存スコアを保護する動作。
    - calc_news_window ユーティリティ（JST の前日 15:00〜当日 08:30 相当の UTC ウィンドウ算出）を提供。
    - OpenAI API キーを引数経由または環境変数 OPENAI_API_KEY から解決。

  - 市場レジーム判定: score_regime（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書込。
    - マクロキーワードで raw_news をフィルタし、OpenAI（gpt-4o-mini）により JSON レスポンスで macro_sentiment を取得。
    - API エラー時はフェイルセーフで macro_sentiment=0.0 を使用。リトライ/バックオフを実装。
    - ルックアヘッドバイアス防止の設計（target_date 未満のデータのみ利用、datetime.today() を参照しない）。

  - AI パッケージ __init__ に score_news をエクスポート。

- Research（リサーチ）モジュールを追加（src/kabusys/research/）
  - factor_research.py: calc_momentum, calc_volatility, calc_value
    - Momentum: 1M/3M/6M リターン、200日MA乖離（データ不足時は None 又は中立判定）。
    - Volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率（データ不足時は None）。
    - Value: PER, ROE（raw_financials から target_date 以前の最新財務データを取得）。
    - DuckDB を用いた SQL ウィンドウ関数主体の実装。
    - 全関数とも外部 API にアクセスせず prices_daily / raw_financials のみ参照。

  - feature_exploration.py: calc_forward_returns, calc_ic, rank, factor_summary
    - 将来リターンの一括取得（任意ホライズン、入力検証、効率的なリード取得）。
    - IC（Spearman ランク相関）計算、ランク付け（同順位は平均ランク）ロジック。
    - 統計サマリー（count/mean/std/min/max/median）を提供。
    - pandas 等に依存しない実装。

  - research パッケージの __init__ で主要関数群を再エクスポート（及び zscore_normalize を data.stats から再利用）。

- Data（データ基盤）モジュールを追加（src/kabusys/data/）
  - calendar_management.py:
    - market_calendar ベースの営業日判定とユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB の有無に応じた曜日ベースのフォールバックや、最大探索日数で無限ループ回避。
    - calendar_update_job により J-Quants API から差分取得・バックフィル（直近 _BACKFILL_DAYS）を行い、冪等保存を想定（jquants_client を使用）。
    - 異常時の健全性チェック（遠すぎる last_date のスキップ等）。

  - pipeline.py / etl.py:
    - ETLResult データクラスを実装（ETL 実行結果の集約、品質チェック情報・エラー情報の格納、ヘルパー to_dict）。
    - ETL の設計方針（差分更新、バックフィル、品質チェック継続、id_token 注入可能性など）を明記。
    - etl.py では ETLResult を公開インターフェースとして再エクスポート。

- 共通実装/運用面の設計・改善点
  - DuckDB をクエリ実行・分析基盤として利用。SQL + Python の組み合わせで多数の計算処理を実装。
  - DB 書き込みは可能な限り冪等性を確保（BEGIN / DELETE / INSERT / COMMIT パターン、失敗時は ROLLBACK）。
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢なバリデーションを実装。
  - ルックアヘッドバイアスを防ぐため、date 引数ベースで処理し datetime.today()/date.today() を直接参照しない設計を徹底。

Changed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- API キーの取り扱い:
  - OpenAI API は関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を発生させ利用者へ明示。
  - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト時の安全性向上）。
  - .env ファイル読み込みはデフォルト UTF-8 とし、読み込みエラーは警告を出力して処理を継続。

注記（設計上の重要なポイント）
- フェイルセーフ: 外部 API の失敗やパースエラーは、基本的に例外を投げてプロセスを停止するのではなく、フェイルセーフ値（例: macro_sentiment=0.0）や個別チャンクのスキップで処理を継続する方針を採用。
- 部分書き込み耐性: AI スコアなどは「書き込み対象コードのみを削除して挿入」することで、部分失敗時に既存データを不必要に失わないように設計。
- テスト容易性: OpenAI 呼び出しを内部関数として切り分け（_call_openai_api）､ユニットテスト時にパッチ差し替え可能にしている。

今後の予定（例）
- strategy / execution / monitoring の実装拡張（現在はパッケージレベルでエクスポートを準備）。
- 追加の品質チェックルールや ETL の進化（並列化、差分検証の強化）。
- モデル選択やプロンプト改善、レスポンス処理の堅牢化。

もし特定の変更点をより詳細に（関数単位や SQL クエリ単位で）記載したい場合は、どのモジュール／関数にフォーカスするか指示してください。