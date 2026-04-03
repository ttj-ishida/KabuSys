CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージ内の __version__（0.1.0）に基づきます。

Unreleased
----------

- 現在未リリースの変更はありません。

0.1.0 - 2026-04-03
------------------

Added
- 初回公開リリース。
- パッケージ構成（主要モジュール）を追加:
  - kabusys.config: 環境変数／.env 管理。プロジェクトルート探索（.git / pyproject.toml）に基づく自動 .env ロード、.env と .env.local の優先度制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。必須キー未設定時は ValueError を送出するユーティリティ _require を提供。
  - kabusys.ai:
    - news_nlp: ニュース記事の銘柄別センチメント解析機能。gpt-4o-mini を JSON Mode で呼び出し、バッチ（最大 20 銘柄/回）で処理、スコアを ±1.0 にクリップして ai_scores テーブルへ書き込み。リトライ（429・ネットワーク断・タイムアウト・5xx は指数バックオフ）とレスポンスバリデーション（JSON 抽出、results 配列検査）を実装。
    - regime_detector: ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。LLM 呼び出し失敗時は macro_sentiment=0.0 でフェイルセーフ。レジームは market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - kabusys.data:
    - calendar_management: JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）、夜間バッチ更新 job（calendar_update_job）を実装。DB 未登録日は曜日ベースのフォールバックを行う。
    - pipeline / etl: ETL 用インターフェースと ETLResult データクラスを提供。差分取得・バックフィル戦略、品質チェックの統合振る舞いを設計。
    - jquants_client を経由した外部データ取得との連携を想定（save_* / fetch_* 系は別モジュール）。
  - kabusys.research:
    - factor_research: モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER、ROE）等のファクター計算を実装。DuckDB 上の SQL ウィンドウ関数を活用し (date, code) 単位で結果を返す。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマンρ）計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。外部依存を避け標準ライブラリのみで実装。
- 全体設計方針／品質配慮:
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接内部計算に参照しない（関数は target_date を引数に取る）。
  - DL API（OpenAI）呼び出しまわりは各モジュールで独立実装し、テスト時にパッチしやすい設計（_call_openai_api を patch 可能）。
  - DuckDB への書き込みは冪等性を意識（DELETE → INSERT や ON CONFLICT など）して実装。部分失敗時に既存データを不必要に上書きしない工夫あり（ai_scores 書き込み時に対象 code を絞る等）。
  - API 呼び出し失敗時は例外をそのまま投げるのではなくログ記録してフォールバック（継続）する設計を採用（フェイルセーフ）。
  - リトライ／バックオフ戦略を共通パターンで導入（基本は指数バックオフ、最大 retries 指定あり）。
- 設定と検証:
  - Settings クラスで各種環境変数を型変換して提供（パス、閾値、ログレベル等）。KABUSYS_ENV と LOG_LEVEL のバリデーションを実施（許容値集合をチェック）。
  - デフォルトの DB パス (DUCKDB_PATH, SQLITE_PATH)、監視用 PID/KILL ファイルパスおよび監視閾値（CPU/MEM/DISK）を環境変数で設定可能。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 外部 API キー（OpenAI など）は引数注入または環境変数（OPENAI_API_KEY）から取得。未設定時は明確な ValueError を投げることで誤った運用を防止。

Notes（重要な実装上の注意）
- OpenAI との通信は gpt-4o-mini を想定し JSON Mode を利用するプロンプトになっているため、API レスポンスの形式が変わるとパースに失敗する可能性があります。パース失敗時はログを出して該当データをスキップするフェイルセーフ動作を行います。
- DuckDB の executemany に関する互換性（空リスト渡し不可）に配慮した分岐を実装しています。
- calendar_update_job は最終取得日の極端な将来日時（SANITY_MAX_FUTURE_DAYS 超）を検出した場合は安全のためスキップします。
- news_nlp / regime_detector ともに API 呼び出し部分はテスト時にモック差し替え可能な点を意識して実装しています。
- research 系モジュールは本番注文処理や外部発注 API へは一切アクセスしない安全設計です。

Deprecated
- なし

Removed
- なし

Acknowledgements
- 初版実装では J-Quants API や kabuステーション、OpenAI 等の外部サービス連携点を含みます。実運用前に各種 API キー、エンドポイント設定、DuckDB スキーマ（prices_daily / raw_news / ai_scores / market_regime / market_calendar / raw_financials 等）が揃っていることを確認してください。

-----