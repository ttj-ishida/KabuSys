CHANGELOG
=========

すべての注目すべき変更はここに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。

0.1.0 - 2026-04-03
-----------------

Added
- 初回リリース。パッケージ名: kabusys（src/kabusys）。
- 基本モジュール構成を追加:
  - data: データ取得・カレンダー管理・ETL パイプライン（data/calendar_management.py, data/pipeline.py, data/etl.py 等）
  - research: ファクター計算と特徴量探索（research/factor_research.py, research/feature_exploration.py 等）
  - ai: ニュース NLP と市場レジーム判定（ai/news_nlp.py, ai/regime_detector.py）
  - config: 環境変数と設定管理（config.py）
- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml を使用）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント (スペース直前の # を考慮) に対応。
  - Settings クラスを提供し、J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）等を取得。
  - 環境値検証: KABUSYS_ENV および LOG_LEVEL の許容値チェックを実装（不正な場合は ValueError）。
- データプラットフォーム（src/kabusys/data）
  - ETLResult データクラス（pipeline.ETLResult を etl モジュール経由で公開）。
  - calendar_management: market_calendar を利用した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）と夜間更新ジョブ calendar_update_job を実装。
  - pipeline/etl: 差分取得・バックフィル・品質チェックのためのユーティリティを実装（バックフィル日数、カレンダー先読み等のデフォルト設定を含む）。
  - DuckDB 互換性を考慮した実装（executemany の空リスト回避等）。
- AI モジュール（src/kabusys/ai）
  - news_nlp.score_news:
    - 前日 15:00 JST ～ 当日 08:30 JST 相当のニュースウィンドウ計算（calc_news_window）。
    - raw_news と news_symbols を銘柄別に集約し、最大 20 銘柄ずつ OpenAI（gpt-4o-mini）の JSON モードでバッチ評価。
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実装。
    - レスポンスの厳格なバリデーション、スコアの ±1.0 クリップ、ai_scores テーブルへの冪等書き込み（DELETE → INSERT、部分失敗時に既存データ保護）。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次レジーム判定（'bull'/'neutral'/'bear'）。
    - マクロ記事抽出（キーワードによるフィルタ）→ OpenAI 呼び出し → 合成スコア → market_regime テーブルへ冪等書き込み。
    - API 問題時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ。
- Research（src/kabusys/research）
  - factor_research: モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日ATR、出来高・売買代金指標）、バリュー（PER/ROE）を DuckDB SQL で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic: スピアマンρ）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
  - zscore_normalize を data.stats から再エクスポート（research.__init__）。
- ロギングと監視
  - 各モジュールで詳細ログ（info/debug/warning）を追加。失敗時には例外の伝播制御と ROLLBACK の試行を行う。

Changed
- （初回リリース）パッケージ設計上の基本方針を明確化:
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() をスコープ内の計算に直接多用しない（target_date 引数依存）。
  - 外部 API 呼び出し失敗時はフェイルセーフ（スキップやデフォルト値）で継続し、致命的エラーは上位へ伝播。
  - モジュール間でプライベート関数を共有しない設計（例: OpenAI 呼び出しの内部関数はモジュール毎に独立実装）。

Fixed
- .env パーサの堅牢化:
  - クォート内のバックスラッシュエスケープ処理、export プレフィックス対応、行内コメントの判定改善を実装。
- LLM レスポンス処理の堅牢化:
  - JSON mode でも前後に余計なテキストが混入するケースへの復元処理を追加（最外側の {} を抽出して JSON パースを試みる）。
  - API エラー種別ごとのリトライ制御（RateLimit / Connection / Timeout / 5xx をリトライ、その他はスキップ）を実装。

Security
- OpenAI API キーとその他秘密情報は Settings 経由で取得する設計。キー未設定時は ValueError を発生させて明示的に通知。
- .env 自動ロード時に OS 環境変数を保護するため、既存の環境変数キー群を protected として上書きを制御。

Notes / Implementation details
- DuckDB を想定した SQL 実装（WINDOW 関数・ROW_NUMBER・LEAD/LAG 等）により多数の集計処理を単一クエリで実行。空の executemany を呼ばない等の互換性対策あり。
- calendar_update_job は J-Quants クライアント（data.jquants_client）に依存。取得→保存（save_market_calendar）を idempotent に処理する。
- ai モジュールの OpenAI 呼び出し関数はテスト容易性のためモジュール内で差し替え可能（ユニットテストで patch 可能）。
- デフォルト設定値（DB パス、PID / kill flag パス、閾値など）は Settings に定義。必要に応じて環境変数で上書き可能。

Deprecated
- なし

Removed
- なし

Security
- なし（初回リリースのため特記事項なし）

今後の予定（短期）
- 統合テストやモックを用いた OpenAI / J-Quants 依存部のテスト実装。
- PBR・配当利回り等、バリューファクター拡張。
- ai モジュールのモデル切替・プロンプト改善・キャパシティ管理。

お問い合わせ
- 各関数の詳細な挙動や DB スキーマ依存の注意点は該当モジュールの docstring を参照してください。