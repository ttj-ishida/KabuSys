# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
詳細はリポジトリのコミット履歴および各モジュールの docstring を参照してください。

## [Unreleased]

## [0.1.0] - 2026-03-29

Added
- 基本パッケージ初期実装（kabusys v0.1.0）
  - パッケージメタ情報を src/kabusys/__init__.py に定義（__version__ = "0.1.0"）。パブリックサブパッケージを __all__ で公開。
- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能（プロジェクトルートの検出：.git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ実装：コメント、export プレフィックス、シングル/ダブルクォート・バックスラッシュエスケープのサポート。
  - OS 環境変数を保護する protected オプション、override フラグによる上書き制御。
  - Settings クラスでアプリ設定をプロパティ化して提供（J-Quants、kabu API、Slack、DB パス、環境種別・ログレベルの検証等）。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）。
- AI モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini、JSON mode）へバッチ送信し、銘柄ごとのセンチメント（ai_scores）を書き込む処理を実装。
    - タイムウィンドウ計算（JSTベース → UTC変換）を提供する calc_news_window 関数を公開。
    - バッチサイズ、記事数・文字数上限、429/ネットワーク/タイムアウト/5xx に対する指数バックオフ・リトライ、レスポンスバリデーション（JSON 抽出・results 構造・コード照合・数値チェック）を実装。
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）。
    - テスト用フック：_call_openai_api を unittest.mock.patch で差し替え可能。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出しのリトライ/フォールバック処理を実装。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。
- Data モジュール（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得／一部欠損時の曜日ベースフォールバック実装（土日は非営業日扱い）。
    - 夜間バッチ更新ジョブ calendar_update_job：J-Quants API から差分取得して保存/バックフィル（_BACKFILL_DAYS）・健全性チェックを行う。
  - ETL・パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass（ETL 実行結果の集約）を実装（品質チェック結果・エラー一覧・数値情報等）。
    - 差分取得、保存（jq.save_* による冪等保存）、品質チェックの統合を想定した設計。
    - etl モジュールで ETLResult を再エクスポート。
  - jquants_client 連携想定（モジュール参照箇所あり。実装は jquants_client 側に依存）。
- Research モジュール（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）などの定量ファクター計算を実装。
    - DuckDB を用いた SQL ベース計算。データ不足時は None を返す安全設計。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン対応）、IC（Spearman の ρ）計算、ランク変換ユーティリティ、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージの __all__ を整備し、外部公開 API を明確化。
- その他の実装・設計上の配慮
  - DuckDB との互換性（日付型変換ユーティリティ、executemany の空リスト回避など）を考慮した実装。
  - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を確保。例外発生時は ROLLBACK を試行し、失敗時はログ出力。
  - LLM 呼び出しに対してはフェイルセーフを基本とし、API 全体失敗時はスコアを中立（0.0 または 1.0 相当の中立値）にフォールバックする設計。
  - 設計方針として「ルックアヘッドバイアス防止」「外部発注 API へのアクセスを行わない（データ処理／リサーチは読み取り専用）」を明示。

Changed
- 該当なし（初期リリース）

Fixed
- 該当なし（初期リリース）

Security
- OpenAI API キー（OPENAI_API_KEY）や各種トークンは必須設定（Settings クラスで未設定時は ValueError を送出）。環境変数や .env の管理に注意してください。
- .env 自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Notes / Known limitations
- OpenAI への依存（gpt-4o-mini）と JSON mode を前提としているため、API 仕様変更に注意が必要。
- jquants_client の実装と DB スキーマ（raw_news, prices_daily, ai_scores, market_regime, market_calendar, raw_financials など）がプロジェクトに存在することが前提です。
- DuckDB のバージョン依存（特に executemany の空リスト挙動）に注意。コード内で互換性対策を施していますが、実行環境の DuckDB バージョンにより挙動が変わる可能性があります。
- news_nlp/regime_detector のテストは _call_openai_api をモックすることを想定しています。

参考
- 各モジュールの詳細な仕様・設計方針はソース内の docstring に記載しています。特に AI（news_nlp / regime_detector）、ETL（pipeline）、calendar_management の docstring を参照してください。

--- 
（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はコミットログ・リリース要件に基づき適宜調整してください。）