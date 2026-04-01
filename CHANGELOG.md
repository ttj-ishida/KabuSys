Unreleased
---------

- 今後の変更点をここに記載します。

[0.1.0] - 2026-04-01
-------------------

Added
- 初回リリース。パッケージ kabusys の基本機能を実装・公開。
- パッケージメタ情報
  - バージョン: 0.1.0
  - パッケージ説明: "KabuSys - 日本株自動売買システム"（src/kabusys/__init__.py）
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env/.env.local の読み込み順序（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - export 形式やクォート、インラインコメントを考慮した堅牢な .env パーサ実装。
  - Settings クラスでアプリ全体の設定をプロパティ経由で取得（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境等）。
  - バリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）と必須環境変数取得用の _require 関数。
- AI モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON Mode でセンチメント評価。
    - バッチ処理（最大 20 銘柄/チャンク）、銘柄ごとのトリミング（記事数・文字数上限）およびレスポンス検証を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで処理し、部分失敗時でも既存スコアを保護するために対象コードのみ置換（DELETE→INSERT）。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
    - calc_news_window：JST ウィンドウ（前日 15:00 ～ 当日 08:30）を UTC naive datetime で計算。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは独立した実装で、API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）により market_regime テーブルを更新。
- Research モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER、ROE）などのファクター計算を実装。
    - DuckDB のウィンドウ関数を用い、prices_daily / raw_financials のみ参照する安全設計。
    - データ不足時の安全な None 戻しやログ出力を含む実装。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算、rank、factor_summary（統計サマリ）などを実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - 研究用ユーティリティの再エクスポート（__all__）。
- Data モジュール（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar を元にした営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。探索上限で無限ループを防止。
    - calendar_update_job：J-Quants から差分取得し冪等保存、バックフィルや健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを公開。ETL のフェーズごとの取得/保存数、品質チェック・エラー集約を保持。
    - 差分更新・バックフィル・品質チェックの設計方針を実装（jquants_client 経由の保存を想定）。
  - etl モジュールで ETLResult を再エクスポート（src/kabusys/data/etl.py）。
- research と data パッケージの初期公開 API を整備（__all__ 等）。

Security
- OpenAI API キーや各種トークンは環境変数で供給する設計。OpenAI のキーが未設定の場合は各関数（score_news / score_regime）が ValueError を発生させる。
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能で、テスト環境での誤動作を防止。

Notes / Implementation details
- ルックアヘッドバイアス対策：date.today() / datetime.today() を参照せず、呼び出し時に target_date を明示的に渡す設計。
- OpenAI 呼び出し周りはリトライ・エラーハンドリングを念入りに実装。API レスポンスのパース失敗や API エラー時は例外を投げずフォールバック（0.0）する箇所があるため、呼び出し側で結果の有無を確認すること。
- DuckDB 関連の executemany 空パラメータ挙動に対するガード（空リスト時の呼び出し回避）を実装。
- テスト容易性のため、OpenAI 呼び出し部分（_call_openai_api 等）をモック差し替え可能にしてある。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。