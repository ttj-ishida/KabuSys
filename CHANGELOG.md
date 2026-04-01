# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  

※以下は提示されたコードベースの内容から推測して作成した初回リリースの変更履歴です。

## [0.1.0] - 2026-04-01

### Added
- パッケージ初期リリース: kabusys (src/kabusys)
  - パッケージメタ情報と公開サブパッケージ定義を追加（src/kabusys/__init__.py）。
- 環境設定管理
  - .env ファイルおよび環境変数からの設定読み込みを実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env / .env.local を読み込む自動ロード機能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - .env のパースは export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理などをサポート。
    - override と protected（OS 環境変数保護）による上書き制御。
  - Settings クラスを提供し、アプリケーション設定（J-Quants、kabuステーション、Slack、DB パス、監視閾値、環境モード、ログレベル等）を型付きプロパティで取得可能に。
    - KABUSYS_ENV / LOG_LEVEL の値検証や is_live / is_paper / is_dev のユーティリティを提供。
    - 必須環境変数未設定時は ValueError を送出する _require を実装。
- AI モジュール（自然言語処理）
  - ニュースセンチメント分析機能（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価。
    - バッチ処理（最大20銘柄）、トークン肥大化対策（記事数／文字数上限）、レスポンスバリデーション、スコアのクリップ等を実装。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフ・リトライ処理とフェイルセーフ（失敗時はスキップ）を実装。
    - calc_news_window により JST 基準のニュース取得ウィンドウを計算（前日15:00〜当日08:30 JST 相当）。
    - スコア結果を ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込む。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily と raw_news を参照し、OpenAI を用いたマクロセンチメント評価（gpt-4o-mini, JSON mode）。
    - API 呼び出しのリトライ、JSON パース失敗時のフォールバック macro_sentiment=0.0、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を参照しない設計（target_date を明示的に与える）。
- データプラットフォーム（Data）
  - ETL パイプラインとユーティリティ（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass により ETL の実行結果（取得数・保存数・品質問題・エラー等）を構造化して返却。
    - 差分更新、バックフィル（デフォルト3日）、品質チェック（quality モジュールとの連携）に関する設計思想を実装。
    - ETLResult.to_dict により監査ログ用の辞書化をサポート。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定、next/prev_trading_day、get_trading_days、is_sq_day 等のユーティリティを提供。
    - カレンダー未取得時の曜日ベースフォールバック、DB 登録値の優先、最大探索日数による安全策を実装。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック含む）。
  - jquants_client を利用した外部 API 連携箇所を想定（fetch/save の呼び出し）。
- リサーチ/ファクター計算（src/kabusys/research）
  - factor_research.py: Momentum, Volatility, Value, Liquidity 等の定量ファクター計算を実装
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率等
    - calc_value: raw_financials を参照した PER/ROE 計算（EPS 0/欠損時は None）
    - 全関数とも DuckDB の SQL ウィンドウ関数を活用し、prices_daily / raw_financials のみ参照する設計
  - feature_exploration.py: 将来リターン計算、IC（Spearman の ρ）、rank、factor_summary（count/mean/std/min/max/median）等の統計ユーティリティを実装
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関を計算（有効レコード < 3 の場合は None）
    - 実装は標準ライブラリのみで pandas 等に依存しない
- 研究向け公開インターフェースを整備（src/kabusys/research/__init__.py）
  - 主要関数の再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）

### Changed
- （初回リリースのため変更履歴は無し。コード設計上の注記）
  - 各モジュールはルックアヘッドバイアス回避のため明示的な target_date を必要とする設計を採用。
  - OpenAI の呼び出しは JSON Mode を利用し、レスポンスの堅牢なパースとバリデーションを行う実装になっている。

### Fixed
- （初回リリースのため過去バグ修正は無し。堅牢性対策を多数実装）
  - DB 書き込み時の例外に対して ROLLBACK を試行し、失敗時はログ出力して例外を再スローするパターンを採用（冪等性と安全性の向上）。
  - DuckDB の executemany の空パラメータ制約に対するガードを追加（空リストを渡さない）。

### Security
- 環境変数の取り扱いについて保護機能を実装
  - .env 読み込み時に既存 OS 環境変数を protected として上書きから守る仕組みを採用。
  - 必須のシークレット（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は未設定時に明示的にエラーを出す設計により、誤動作を早期検出。

### Known issues / Notes
- OpenAI／J-Quants など外部 API 呼び出しは実稼働環境でのキー設定と通信環境に依存するため、ローカルテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD や unittest.mock によるモック化が必要。
- 一部モジュール（strategy / execution / monitoring）は __all__ で公開対象に含まれているが、提示コードには未掲載のため実装状況に注意。
- DuckDB のバージョン依存点（リスト型バインドや executemany の振る舞い）に対する互換性処理が施されているが、運用時に使用する DuckDB バージョンで検証を推奨。

---

今後のリリースでは、実装済みの strategy / execution / monitoring モジュールの追加、ユニットテスト拡充、ドキュメント（API 使用例・運用手順）の整備を予定してください。