CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。
このプロジェクトはセマンティックバージョニングに従います。

Unreleased
----------

- （なし）

0.1.0 – 2026-03-29
------------------

Added
- パッケージ初回リリース: kabusys v0.1.0 を公開。
- パッケージ公開インターフェース
  - src/kabusys/__init__.py で data, strategy, execution, monitoring を __all__ として公開。
- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび OS 環境変数の読み込み機能を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロード。
    - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - export KEY=val、クォート、エスケープ、行末コメント等の細かい .env パース対応。
    - 必須環境変数取得時の _require() と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）、ログレベル、環境 (development/paper_trading/live) の検証ロジック。
- AI（自然言語処理）機能
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を使いニュースを銘柄別に集約して OpenAI（gpt-4o-mini）でセンチメントを評価し、ai_scores テーブルへ書き込むワークフローを実装。
    - 時間ウィンドウ計算（JST基準の前日15:00〜当日08:30 に対応）、チャンク処理（最大20銘柄/チャンク）、記事・文字数トリム、JSON Mode を用いた堅牢なレスポンス処理を実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリッピング、部分書き込み（成功した銘柄のみ DELETE→INSERT）による冪等性／部分失敗耐性を備える。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みする処理を実装。
    - マクロキーワードで記事抽出、OpenAI（gpt-4o-mini）によるマクロセンチメント評価、APIエラーフェイルセーフ（失敗時 macro_sentiment=0.0）、リトライロジックを実装。
    - ルックアヘッドバイアス回避のため日次の比較やクエリに排他条件を採用。
- Data（データ基盤）機能
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダー管理（market_calendar）とそれに基づく営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日操作関数を提供。
    - market_calendar が未取得の場合は曜日ベースでフォールバックする設計、最大探索日数制限（_MAX_SEARCH_DAYS）を実装。
    - calendar_update_job による夜間バッチ更新（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）を実装。
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプラインの基盤を実装。差分更新、idempotent 保存、品質チェック連携を想定した構成。
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題・エラー情報の保持、to_dict によるシリアライズ）。
    - _get_max_date 等のユーティリティ関数を実装。
  - src/kabusys/data/__init__.py と etl の再エクスポートを追加。
  - jquants_client との連携を想定（fetch/save 関数を利用する設計）。
- Research（リサーチ）機能
  - src/kabusys/research/factor_research.py
    - ファクター計算群を実装（モメンタム: 1M/3M/6M、ma200乖離; ボラティリティ: 20日ATR; バリュー: PER/ROE; 流動性: 20日平均売買代金等）。
    - DuckDB の SQL ウィンドウ関数を活用し日付レンジや欠損扱いを考慮した実装。結果は (date, code) をキーとする dict のリストで返す。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas に依存せず標準ライブラリのみで完結する設計。
  - src/kabusys/research/__init__.py で主な関数を再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。
- ロギングと設計方針
  - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない設計（一部ジョブは実行時に today を使うが、データ計算ロジックは target_date を受け取る）。
  - OpenAI 呼び出しは各モジュール内で独立実装し、モジュール間でプライベート関数を共有しない設計（テスト時に差し替え可能）。
  - API 呼び出し失敗時のフォールバックやログ出力、部分失敗保護（DB 書き込みでの部分的保護）を重視した安全設計。

Changed
- 初回パブリックリリースのための API 設計と初期実装を追加（以降のリリースで API 安定化・拡張予定）。

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーや外部サービスの認証情報は環境変数で扱う設計。必須キーが未設定の場合は明示的に ValueError を送出して呼び出し元に通知。

Notes / Known limitations
- OpenAI 呼び出しは gpt-4o-mini モデルを想定。API のバージョンや SDK による差分で例外種類や属性名が変わる可能性があるため、API エラー処理で互換性確保コードを組み込んでいる（status_code の安全取得等）。
- DuckDB バインドの空リスト executemany の制約（バージョン依存）を考慮した実装がある（空リストの場合は実行をスキップ）。
- news_nlp / regime_detector は OpenAI API のレスポンスを JSON モードで期待する。LLM の出力形式逸脱時はフェイルセーフでスコア 0.0 または該当銘柄スキップとなる。
- 一部ジョブ（calendar_update_job 等）は date.today() を利用するため実行時の環境時刻依存がある。研究系の計算関数は target_date 引数で明示的に日付を制御することを推奨。

開発者向けメモ
- テスト容易性のため、AI 呼び出し箇所（_call_openai_api）を unittest.mock.patch で差し替え可能にしている。
- .env 自動読み込みは開発時に便利だが、CI/テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能。
- Settings クラスのプロパティは実行時に環境変数の存在を検証するため、ユニットテストでは環境変数の注入/モックを行ってください。

以上。