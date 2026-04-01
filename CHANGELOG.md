CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは「Keep a Changelog」規約に準拠しています。

フォーマット: [バージョン] - 日付  
例: [0.1.0] - 2026-04-01

[Unreleased]
-----------

- ドキュメント化・テスト用の改善、内部リファクタリング等の予定事項をここに記載します。

[0.1.0] - 2026-04-01
-------------------

初回リリース: 日本株自動売買プラットフォーム "KabuSys" のコア機能群を実装しました。

Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン __version__ = "0.1.0" を追加。
  - パッケージ公開用の __all__ に "data", "strategy", "execution", "monitoring" を登録。

- 環境設定
  - robust な .env 読み込み/パース機能を実装（src/kabusys/config.py）。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - .env/.env.local の自動読み込み（OS 環境変数を保護しつつ .env.local が上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - export KEY=val 形式やクォート/エスケープ、インラインコメント判定に対応するパーサ実装。
    - 環境変数取得ヘルパ _require と Settings クラスを提供（J-Quants, kabu API, Slack, DB パス, 監視しきい値などのプロパティを定義）。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）を実装。
    - Path 型でのファイルパス（duckdb/sqlite/pid）返却。

- データプラットフォーム
  - market_calendar 管理と営業日ロジック（src/kabusys/data/calendar_management.py）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB データ優先、未登録日は曜日（週末）フォールバックの一貫した挙動。
    - 夜間バッチ calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック実装）。
    - 最大探索範囲 _MAX_SEARCH_DAYS により無限ループを回避。

  - ETL パイプラインの公開インターフェース（src/kabusys/data/etl.py / pipeline.py）
    - ETLResult dataclass を実装（取得件数、保存件数、品質検査結果、エラーの集約、has_errors 等のユーティリティ）。
    - 差分更新・バックフィル・品質チェックを想定した設計（J-Quants クライアント呼び出し、idempotent 保存、エラー収集方針）。

- ニュース NLP / AI
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごと記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを取得して ai_scores に書き込む機能。
    - 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（1回最大 20 銘柄）、1銘柄あたり最大記事数/文字数制限（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - JSON レスポンスのバリデーションとスコアクリッピング（±1.0）。
    - API リトライ（429, 接続断, タイムアウト, 5xx）に対する指数バックオフ実装。
    - テスト用に _call_openai_api を patch して差し替え可能な設計。
    - DuckDB の executemany に対する空パラメータ回避（互換性対策）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime に保存。
    - LLM モデル gpt-4o-mini を使用、JSON mode で {"macro_sentiment": float} 形式を期待。
    - MA 計算でルックアヘッドバイアスを防止（target_date 未満のみ使用、データ不足時は中立 1.0 を返す）。
    - API リトライ・エラー時のフォールバック（macro_sentiment = 0.0）と、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK 保護）。
    - ノート: OpenAI クライアント呼び出しはモジュール間で共有しない（モジュール結合を低減）。

- リサーチ・ファクター
  - ファクター計算群（src/kabusys/research/factor_research.py）
    - calc_momentum: 1/3/6 ヶ月相当のリターン、200 日 MA 乖離を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR、ATR 相対値、20 日平均売買代金、出来高比を計算。NULL 処理を厳密に行う（true_range の NULL 伝播）。
    - calc_value: raw_financials から最新財務を取得し PER（EPS が 0/欠損時は None）と ROE を計算。
    - 共通方針: DuckDB SQL を多用し、外部 API や実取引へのアクセスは一切しない。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定日から各ホライズン（デフォルト 1,5,21 営業日）までの将来リターンを計算。horizons の検証あり。
    - calc_ic: Spearman ランク相関で IC を計算。サンプル不足時は None を返す。
    - rank: 同順位は平均ランクとするランク化実装（round(v,12) による安定化）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を計算。

Changed
- 設計方針の明示化
  - 複数モジュールで「ルックアヘッドバイアス防止」の原則を採用（日付参照に datetime.today()/date.today() を直接使わない設計）。
  - OpenAI 呼び出しの失敗を致命的にせずフォールバック/スキップして継続する方針（フェイルセーフ）。
  - DuckDB のバージョン差異（executemany の空リスト扱い等）を考慮した互換性対策を実装。

Fixed
- エラー・ログハンドリングの改善
  - .env 読み込み失敗時に warnings.warn を出すなど読み込み障害を明示化。
  - OpenAI API 呼び出しや DB 書き込み失敗時に適切にログ出力し、ROLLBACK の失敗も警告ログに記録。

Notes / Known limitations
- news_nlp の出力期待形式（JSON mode）に依存しており、LLM の挙動で余計なテキストが混入するケースを想定して補正ロジックを実装しているが、完全ではありません。
- calc_value は現時点で PBR・配当利回りを未実装。
- OpenAI API キーの取り扱い: api_key 引数を優先、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出する。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が前提。スキーマ未整備の場合は動作しません。

開発者向けメモ
- テスト容易性のため、AI 呼び出し箇所（各モジュールの _call_openai_api）を unittest.mock.patch で差し替え可能にしています。
- 自動環境変数ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログレベル・実行環境は KABUSYS_ENV / LOG_LEVEL で制御します（有効値チェックあり）。

--- 

この CHANGELOG はコードベースの内容から推測して作成しています。詳細や追加の変更はコミット履歴 / PR 差分に基づいて適宜追記してください。