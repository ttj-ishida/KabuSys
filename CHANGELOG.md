# Changelog

すべての重要な変更点を記録します。  
このファイルは "Keep a Changelog" の慣例に従います。  

フォーマット:
- 変更はセクション（Added, Changed, Fixed, Removed, Security）に分類しています。
- 新しいリリースはバージョンヘッダ（例: 0.1.0 - YYYY-MM-DD）で記載します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買・データ基盤・リサーチ・AI 補助モジュールの骨格実装を追加。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にて version と主要サブパッケージ（data, research, ai, ...）を公開。
- 設定・環境変数管理
  - kabusys.config
    - .env/.env.local の自動読み込み機能（プロジェクトルートを .git / pyproject.toml から検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 高機能な .env パーサ（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱い等）。
    - Settings クラスを提供し、アプリケーション向けの設定プロパティ（J-Quants トークン、kabu API、Slack、DB パス、環境/ログレベル判定 等）を安全に取得。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の有効値チェック）と必須値取得時の明確なエラーメッセージ。
- AI モジュール
  - kabusys.ai.news_nlp
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを取得して ai_scores テーブルへ保存する機能。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window 関数で提供。
    - バッチ処理（最大 20 銘柄チャンク）、記事トリム（文字数上限）、結果バリデーション、スコアクリップ（±1.0）。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）と指数バックオフ、フェイルセーフ（失敗時は個別チャンクをスキップ）。
    - テスト容易性: _call_openai_api を patch で差し替え可能。
  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（70% 重み）とマクロニュース LLM センチメント（30% 重み）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - prices_daily / raw_news を参照、ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 取得、スコア合成、market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API リトライ、レスポンスパース失敗時のフォールバック macro_sentiment=0.0。
    - モジュール結合を避ける目的で、news_nlp 側と _call_openai_api 実装を共有しない設計。
- データプラットフォーム
  - kabusys.data.calendar_management
    - JPX カレンダー管理と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合の曜日ベースフォールバック、DB 存在時は DB 値優先の一貫した挙動。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants から差分取得→保存（バックフィル、健全性チェック等）。
  - kabusys.data.pipeline / etl
    - ETLResult データクラス（ETL の取得数・保存数・品質チェック・エラー集約等）を公開（kabusys.data.ETLResult）。
    - 差分取得・バックフィル・品質チェックを想定した ETL パイプライン基盤のユーティリティ関数群（内部ユーティリティとしてテーブル存在チェック・最大日付取得等）。
- リサーチ / ファクター計算
  - kabusys.research
    - factor_research: モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。DuckDB の SQL ウィンドウ関数を活用して効率的に集計。
    - feature_exploration: 将来リターン calc_forward_returns、IC（スピアマンの rho）計算 calc_ic、ランク付け rank、統計サマリー factor_summary を提供。外部ライブラリに依存しない純 Python 実装。
    - kabusys.research.__init__ で主要関数を再エクスポート。
- テスト・運用配慮
  - 各所でルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る関数群）。
  - DuckDB を前提としたトランザクション（BEGIN/COMMIT/ROLLBACK）と、部分失敗時に既存データを保護する書き込み戦略（対象コードを絞った DELETE → INSERT）。
  - ログ出力（warning/info/debug）を充実させ、障害時の診断を容易にする。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI APIキー等の必須シークレットは Settings を通じて環境変数から取得する設計。ソース内にハードコードする実装は含まれていません。

---

注記:
- 本リリースはライブラリのコア機能群（データ ETL/カレンダー、ファクター計算、AI ベースのニュース評価・レジーム判定、環境設定）を実装した初期バージョンです。  
- 実装上の設計判断（例: フェイルセーフでのスコア 0.0 フォールバック、API リトライポリシー、DB への冪等書き込み）は CHANGELOG に記載した通りで、運用時に重要な動作保証を提供します。