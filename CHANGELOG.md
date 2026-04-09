# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトの初期リリース（推測に基づくまとめ）を以下に示します。

## [0.1.0] - 2026-04-09

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys（__version__ = 0.1.0）
  - パブリック API: data, strategy, execution, monitoring（__all__）

- 環境設定・ロード機能（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）
  - プロジェクトルートの自動検出ロジック（.git または pyproject.toml を探索）
  - .env のパース機能を実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント対応）
  - .env 読み込み時の上書き制御（override）と OS 環境変数保護（protected set）
  - Settings クラスでアプリ設定を統一的に取得
    - J-Quants / kabuステーション / LINE / DB パス等のプロパティを提供
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の許容値チェック
    - 各種監視パラメータ（PID ファイル、kill フラグ、CPU/メモリ/ディスク閾値等）

- ニュース NLP / LLM スコアリング（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し銘柄単位の ai_score を計算
  - 時間ウィンドウ計算（JST の前日 15:00 ～ 当日 08:30 を UTC に変換）を提供（calc_news_window）
  - バッチング（最大 20 銘柄 / チャンク）・記事トリム（最大記事数／最大文字数）を実装
  - 再試行（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）を実装
  - レスポンスの堅牢なバリデーションとパース（JSON mode の前後ノイズ復元、results 構造検証）
  - スコア値を ±1.0 にクリップ、成功分のみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗から既存データを保護
  - テスト容易性のため _call_openai_api を差し替え可能

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定
  - MA200 の計算（lookahead を防ぐため target_date 未満のデータのみ使用、データ不足時は中立扱い）
  - マクロキーワードで raw_news をフィルタし LLM に渡す実装
  - OpenAI 呼び出しの再試行・フォールバック（API 失敗時は macro_sentiment=0.0）を実装
  - 冪等な DB 書き込み（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）を行う

- Research / ファクター計算（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20 日 ATR）、バリュー（PER, ROE）などのファクター計算関数を提供
    - calc_momentum, calc_volatility, calc_value を実装
    - DuckDB のウィンドウ関数を活用して営業日ベースの計算を行う
    - データ不足時は None を返す設計
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換（rank）を提供
    - horizons の入力検証、複数ホライズンを1クエリで取得する最適化
    - スピアマン相関（ランク）による IC 計算（ties は平均ランク）
    - pandas 等に依存せず標準ライブラリのみで実装

- Data platform（kabusys.data）
  - calendar_management:
    - market_calendar に基づく営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB の存在有無に応じた曜日ベースのフォールバック（DB 登録値を優先）
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants から差分取得して market_calendar を更新、バックフィルと健全性チェックを実装
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の取得/保存件数、品質問題、エラーの集約）
    - 差分更新、バックフィル、品質チェックを想定した設計（jquants_client と quality モジュールを利用）
  - ETL や calendar 更新でのエラー処理を明示（API エラー時の安全なフォールバック・ログ記録）

### Changed
- （初期リリースのため該当なし。設計上の注意点・既定値をドキュメント内に明記）
  - AI モジュールで日付参照に datetime.today() / date.today() を直接使わない設計（ルックアヘッドバイアス防止）
  - DuckDB のバージョン非互換性を考慮した実装（executemany に空リストを渡さないガード等）

### Fixed
- （初期リリース：実装内で想定されたフェイルセーフを多数導入）
  - OpenAI API の各種失敗ケースに対してフェイルセーフ（ゼロスコア／スキップ）を導入
  - .env ファイル読み込み失敗時に警告を出して続行（OSError のハンドリング）

### Security
- 環境変数読み込みに関して OS 環境変数を保護する仕組みを実装（.env 読み込みで protected set を使い上書きを防止）

### Internal / Notes
- OpenAI 呼び出しは各モジュールで独自の _call_openai_api 実装を持つ（モジュール間のプライベート関数共有を避ける設計）
- テスト容易性のため各所で差し替えポイント（モック対象）を用意
- DuckDB の日付型取り扱いや互換性に注意（_date/to_date ユーティリティを提供）
- 一部の公開 API（strategy, execution, monitoring 等）は __all__ に含まれるが、この差分では具体実装ファイルは提示されていないため、将来的な拡張箇所として想定

---

今後のリリースでは以下が想定されます（推測）
- strategy / execution / monitoring の具現化（発注ロジック・監視ループ）
- 単体テスト・統合テストの追加、CI 設定
- ドキュメント（API リファレンス、運用手順、DB スキーマ）
- 性能改善（大型 DB クエリ、並列化）、OpenAI コスト最適化

もし CHANGELOG に追記してほしい点（例えば実際のリリース日や既存の内部チケット番号、実際の修正履歴の詳細など）があれば教えてください。推定ではなく実際の履歴ベースで整形します。